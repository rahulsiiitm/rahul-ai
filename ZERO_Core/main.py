"""
ZERO CORE — Entry Point

Boot sequence:
  1. Dispatcher  (tool router)
  2. Brain       (Ollama LLM — streaming)
  3. TUI         (Textual 3-panel UI)

Voice / STT disabled — will be re-enabled after core is stable.
"""

import sys

from engine.brain      import ZeroBrain
from engine.dispatcher import ZeroDispatcher
from tools.job_tracker import JobTracker


def boot_terminal_fallback(brain: ZeroBrain):
    """Minimal terminal loop — used if Textual is not installed."""
    print("\n══════════════════════════════════════════════════")
    print("      ZERO CORE RUNTIME ENGINE INITIALIZED        ")
    print("══════════════════════════════════════════════════")
    print("Mode: Terminal  |  Stream: GPU → stdout\n")

    while True:
        try:
            user_input = input("Rahul ──▶ ")
            if user_input.lower() in ("exit", "quit", "shutdown"):
                print("ZERO: Shutting down.")
                break
            if not user_input.strip():
                continue

            print("ZERO  ──▶ ", end="")
            sys.stdout.flush()

            for token in brain.generate_streaming_response(user_input):
                sys.stdout.write(token)
                sys.stdout.flush()

            print()

        except (KeyboardInterrupt, EOFError):
            print("\nZERO: Thread safety disengagement initiated.")
            sys.exit(0)


def main():
    # ── 1. Dispatcher ──────────────────────────────────────────────────────────
    dispatcher = ZeroDispatcher()

    # ── 2. Brain ───────────────────────────────────────────────────────────────
    brain = ZeroBrain(dispatcher=dispatcher)

    # ── 3. TUI ─────────────────────────────────────────────────────────────────
    try:
        from ui.app import ZeroApp
        jobs_db = JobTracker()
        app = ZeroApp(
            brain=brain,
            dispatcher=dispatcher,
            jobs=jobs_db,
        )
        app.run()

    except ImportError as e:
        print(f"[ZERO] Textual not installed ({e}) — falling back to terminal mode.")
        boot_terminal_fallback(brain)


if __name__ == "__main__":
    main()