"""
ZERO CORE — Entry Point

Boot sequence:
  1. Dispatcher  (tools)
  2. Brain       (Ollama LLM)
  3. Listener    (wake word + STT)
  4. TUI         (Textual 3-panel UI)
"""

import sys

from engine.brain      import ZeroBrain
from engine.voice      import ZeroVoice
from engine.dispatcher import ZeroDispatcher
from tools.job_tracker import JobTracker


def boot_terminal_fallback(brain: ZeroBrain, voice: ZeroVoice):
    """Minimal terminal loop — used if Textual is not installed."""
    print("\n══════════════════════════════════════════════════")
    print("      ZERO CORE RUNTIME ENGINE INITIALIZED        ")
    print("══════════════════════════════════════════════════")
    print("Mode: Terminal Fallback  |  Stream: GPU → stdout\n")

    while True:
        try:
            user_input = input("Rahul ──▶ ")
            if user_input.lower() in ("exit", "quit", "shutdown"):
                break
            if not user_input.strip():
                continue

            print("ZERO  ──▶ ", end="")
            sys.stdout.flush()

            for token in brain.generate_streaming_response(user_input):
                sys.stdout.write(token)
                sys.stdout.flush()
                voice.stream_token(token)

            voice.end_of_turn()
            print()

        except (KeyboardInterrupt, EOFError):
            print("\nZERO: Thread safety disengagement initiated.")
            sys.exit(0)


def main():
    # ── 1. Dispatcher ──────────────────────────────────────────────────────────
    dispatcher = ZeroDispatcher()

    # ── 2. Brain ───────────────────────────────────────────────────────────────
    brain = ZeroBrain(dispatcher=dispatcher)

    # ── 3. Voice output (Piper TTS) ────────────────────────────────────────────
    voice = ZeroVoice()

    # ── 4. Listener (wake word + Whisper STT) ──────────────────────────────────
    try:
        from engine.listener import ZeroListener
        listener = ZeroListener()
    except ImportError:
        print("[ZERO] Listener deps not installed — voice input disabled.")
        listener = None

    # ── 5. TUI ─────────────────────────────────────────────────────────────────
    try:
        from ui.app import ZeroApp
        jobs_db = JobTracker()
        app = ZeroApp(
            brain=brain,
            dispatcher=dispatcher,
            listener=listener,
            jobs=jobs_db,
        )

        # Pipe TTS into every brain response via TUI token callback
        original_gen = brain.generate_streaming_response

        def gen_with_voice(prompt: str):
            for token in original_gen(prompt):
                voice.stream_token(token)
                yield token
            voice.end_of_turn()

        brain.generate_streaming_response = gen_with_voice

        app.run()

    except ImportError:
        print("[ZERO] Textual not installed — falling back to terminal mode.")
        boot_terminal_fallback(brain, voice)


if __name__ == "__main__":
    main()