"""
ZeroBrain — Ollama chat engine with tool-call interception.

Normal flow  : stream tokens directly to caller (low latency).
Tool flow    : buffer first response → detect [TOOL:...] tag → dispatch → stream narration.
"""

import re
import ollama
from config import OLLAMA_MODEL

_TOOL_RE = re.compile(r'\[TOOL:[^\]]+\]')


class ZeroBrain:

    def __init__(self, dispatcher=None):
        self.model      = OLLAMA_MODEL
        self.history    = []
        self.dispatcher = dispatcher          # injected after construction

    def set_dispatcher(self, dispatcher):
        self.dispatcher = dispatcher

    # ── Main entry point ───────────────────────────────────────────────────────

    def generate_streaming_response(self, prompt: str):
        """
        Yield tokens for the given prompt.
        If ZERO's response contains a [TOOL:...] tag:
          1. Run the tool (silent — no tokens yielded yet)
          2. Feed result back as a [RESULT:] user message
          3. Stream ZERO's narration of the result
        """
        self.history.append({"role": "user", "content": prompt})

        # ── Step 1: buffer full response to detect tool calls ──────────────────
        try:
            stream = ollama.chat(
                model=self.model,
                messages=self.history,
                stream=True,
                options={"num_gpu": 99, "num_ctx": 4096},
            )
        except Exception as e:
            yield f"\n[Brain] Connection error: {e}"
            return

        full_reply = ""
        buffered   = []

        for chunk in stream:
            token = chunk["message"]["content"]
            full_reply += token
            buffered.append(token)

        # ── Step 2: did ZERO call a tool? ──────────────────────────────────────
        tool_match = _TOOL_RE.search(full_reply)

        if tool_match and self.dispatcher:
            tag = tool_match.group(0)

            # Save ZERO's decision to history
            self.history.append({"role": "assistant", "content": tag})

            # Run tool — get plain-text result
            result = self.dispatcher.dispatch(tag)

            # Feed result back and stream narration
            self.history.append({"role": "user", "content": f"[RESULT:] {result}"})
            yield from self._stream_narration()

        else:
            # No tool — yield the buffered tokens and save history
            for token in buffered:
                yield token
            self.history.append({"role": "assistant", "content": full_reply})

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _stream_narration(self):
        """Stream ZERO's natural-language narration of a tool result."""
        try:
            stream = ollama.chat(
                model=self.model,
                messages=self.history,
                stream=True,
                options={"num_gpu": 99, "num_ctx": 4096},
            )
            narration = ""
            for chunk in stream:
                token = chunk["message"]["content"]
                narration += token
                yield token
            self.history.append({"role": "assistant", "content": narration})
        except Exception as e:
            yield f"\n[Brain] Narration error: {e}"