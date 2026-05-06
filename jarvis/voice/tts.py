"""
jarvis/voice/tts.py
Text-to-Speech using pyttsx3 (Windows SAPI — fully local, zero download).
Runs in a background thread so it never blocks the GUI.
"""
from __future__ import annotations
import threading
import re

_engine      = None
_lock        = threading.Lock()
_speaking    = False
_tts_enabled = True   # user can toggle off


def _get_engine():
    global _engine
    with _lock:
        if _engine is None:
            import pyttsx3
            _engine = pyttsx3.init()
            _engine.setProperty("rate",   165)   # words per minute
            _engine.setProperty("volume", 0.92)

            # Pick a clear voice — prefer David (en-US) or Zira
            voices = _engine.getProperty("voices")
            preferred = ["david", "zira", "mark"]
            for pref in preferred:
                for v in voices:
                    if pref in v.id.lower():
                        _engine.setProperty("voice", v.id)
                        break
                else:
                    continue
                break
        return _engine


def _clean(text: str) -> str:
    """Strip markdown and special chars before speaking."""
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)   # bold/italic
    text = re.sub(r"`+(.+?)`+",            r"\1", text)   # code
    text = re.sub(r"#{1,6}\s*",            "",    text)   # headers
    text = re.sub(r"\[(.+?)\]\(.+?\)",    r"\1", text)   # links
    text = re.sub(r"\n{2,}",              ". ",  text)   # blank lines → pause
    text = re.sub(r"\n",                  " ",   text)
    return text.strip()


def speak(text: str) -> None:
    """Speak text in a background thread. Skips if TTS is disabled."""
    if not _tts_enabled or not text.strip():
        return

    def _run():
        global _speaking
        _speaking = True
        try:
            engine = _get_engine()
            clean  = _clean(text)
            # Keep it brief — read max 250 chars to avoid long waits
            if len(clean) > 250:
                clean = clean[:250].rsplit(" ", 1)[0] + "."
            engine.say(clean)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS] Error: {e}")
        finally:
            _speaking = False

    threading.Thread(target=_run, daemon=True).start()


def stop() -> None:
    """Interrupt current speech."""
    global _speaking
    try:
        eng = _get_engine()
        eng.stop()
    except Exception:
        pass
    _speaking = False


def set_enabled(val: bool) -> None:
    global _tts_enabled
    _tts_enabled = val


def is_speaking() -> bool:
    return _speaking


def is_enabled() -> bool:
    return _tts_enabled
