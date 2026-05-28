"""
ZeroBrain — Ollama chat engine with tool-call interception.

Normal flow  : buffer → no tool tag → yield tokens.
Tool flow    : buffer → detect [TOOL:...] tag → dispatch → inject [RESULT:]
               → single second Ollama call for narration → yield narration tokens.

Note: Two-call tool flow is necessary because Ollama needs a fresh message
      with the result injected. We avoid OOM by keeping num_gpu conservative
      (set in config.py — tuned for RTX 3050 Laptop 4 GB VRAM).
"""

import re
import ollama
from config import OLLAMA_MODEL, OLLAMA_NUM_GPU

_TOOL_RE = re.compile(r'\[TOOL:[^\]]+\]')

_OLLAMA_OPTIONS = {
    "num_gpu": OLLAMA_NUM_GPU,
    "num_ctx": 2048,          # reduced from 4096 — saves ~400 MB VRAM
    "num_predict": 256,       # cap response length — ZERO should be brief
}


class ZeroBrain:

    def __init__(self, dispatcher=None):
        self.model      = OLLAMA_MODEL
        self.history    = []
        self.dispatcher = dispatcher

    def set_dispatcher(self, dispatcher):
        self.dispatcher = dispatcher

    # ── Main entry point ───────────────────────────────────────────────────────

    def generate_streaming_response(self, prompt: str):
        """
        Yield tokens for the given prompt.

        If ZERO's first response is a [TOOL:...] tag:
          1. Dispatch tool silently
          2. Inject [RESULT:] and call Ollama again for narration
          3. Stream narration tokens
        Otherwise: stream buffered tokens directly.
        """
        self.history.append({"role": "user", "content": prompt})

        # ── Step 1: get ZERO's first response ─────────────────────────────────
        full_reply, error = self._collect(self.history)

        if error:
            yield error
            return

        # ── Step 2: tool detection ─────────────────────────────────────────────
        tool_match = _TOOL_RE.search(full_reply)

        if tool_match and self.dispatcher:
            tag = tool_match.group(0)
            self.history.append({"role": "assistant", "content": tag})

            # Run the tool
            try:
                result = self.dispatcher.dispatch(tag)
            except Exception as e:
                result = f"[Tool Error] {e}"

            # Inject result and get narration
            narration_messages = self.history + [
                {"role": "user", "content": f"[RESULT:] {result}"}
            ]
            narration, error2 = self._collect(narration_messages)
            if error2:
                yield error2
                return

            # Save both sides to history cleanly
            self.history.append({"role": "user",      "content": f"[RESULT:] {result}"})
            self.history.append({"role": "assistant",  "content": narration})

            # Yield narration token-by-token (simulate streaming for TUI)
            for char in narration:
                yield char

        else:
            # No tool — yield buffered tokens and save
            for char in full_reply:
                yield char
            self.history.append({"role": "assistant", "content": full_reply})

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _collect(self, messages: list) -> tuple[str, str | None]:
        """
        Run a non-streaming Ollama call and return (full_text, error_or_None).
        Non-streaming avoids the two-connection VRAM contention issue on 4 GB GPUs.
        """
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                stream=False,
                options=_OLLAMA_OPTIONS,
            )
            return response.message.content, None
        except Exception as e:
            return "", f"\n[Brain] Error: {e}"