"""
jarvis/voice/stt.py
Speech-to-Text using faster-whisper (local Whisper model).
Runs on GPU (CUDA) if available, falls back to CPU.

Model: "tiny" — ~75MB, downloads once, very fast on RTX 3050.
"""
from __future__ import annotations
import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000   # Whisper expects 16kHz
MAX_SECONDS = 30       # safety cap

_model   = None
_lock    = threading.Lock()

# ── Shared recording state ─────────────────────────────────────────────────
_recording   = False
_audio_chunks: list[np.ndarray] = []


def load_model():
    """Lazy-load Whisper model. Downloads ~75MB on first run."""
    global _model
    with _lock:
        if _model is not None:
            return _model
        from faster_whisper import WhisperModel
        try:
            _model = WhisperModel("tiny", device="cuda", compute_type="float16")
            print("[STT] Loaded Whisper tiny on CUDA")
        except Exception:
            _model = WhisperModel("tiny", device="cpu", compute_type="int8")
            print("[STT] Loaded Whisper tiny on CPU")
        return _model


def start_recording() -> None:
    """Start microphone capture. Call stop_and_transcribe() to finish."""
    global _recording, _audio_chunks
    _recording    = True
    _audio_chunks = []

    def _callback(indata, frames, time_info, status):
        if _recording:
            _audio_chunks.append(indata.copy())

    def _stream():
        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1,
            dtype="float32", callback=_callback,
            blocksize=int(SAMPLE_RATE * 0.1),   # 100ms blocks
        ):
            # Stay open until _recording is flipped off
            import time
            elapsed = 0.0
            while _recording and elapsed < MAX_SECONDS:
                time.sleep(0.05)
                elapsed += 0.05

    threading.Thread(target=_stream, daemon=True).start()


def stop_and_transcribe() -> str:
    """Stop the microphone and return transcribed text (blocking)."""
    global _recording
    _recording = False
    import time; time.sleep(0.15)  # let final chunks flush

    if not _audio_chunks:
        return ""

    audio = np.concatenate(_audio_chunks, axis=0).flatten()
    if len(audio) < SAMPLE_RATE * 0.5:   # less than 0.5s — ignore
        return ""

    model = load_model()
    segments, _ = model.transcribe(
        audio, language="en", beam_size=1,
        vad_filter=True,                  # skip silence
    )
    return " ".join(s.text for s in segments).strip()


def is_recording() -> bool:
    return _recording
