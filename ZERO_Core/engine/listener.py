"""
ZeroListener — Wake word detection + Speech-to-Text
Wake word : "Hey ZERO"  (openWakeWord hey_jarvis model)
STT       : faster-whisper  (fully local, no cloud)
"""

import threading
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from openwakeword.model import Model as OWWModel

from config import (
    SAMPLE_RATE, CHUNK_SIZE, WHISPER_MODEL_SIZE,
    WAKE_WORD_MODEL, WAKE_WORD_THRESHOLD,
    SILENCE_THRESHOLD, MAX_SILENCE_SECS, MIN_SPEECH_SECS,
)


class ZeroListener:
    """
    Continuously monitors microphone for wake word.
    On detection → records until silence → transcribes → fires on_transcription().

    Callbacks
    ---------
    on_wake(str)           : fired when wake word is detected (status label)
    on_transcription(str)  : fired with final recognised text
    on_status(str)         : fired with human-readable status updates for UI
    """

    def __init__(self, on_wake=None, on_transcription=None, on_status=None):
        self.on_wake          = on_wake
        self.on_transcription = on_transcription
        self.on_status        = on_status
        self._stop            = threading.Event()
        self._recording       = False

        self._log("Loading Whisper STT model …")
        self.whisper = WhisperModel(
            WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type="int8",
        )

        self._log("Loading wake word detector …")
        self.oww = OWWModel(
            wakeword_models=[WAKE_WORD_MODEL],
            inference_framework="onnx",
        )

        self._log("Listener armed  ·  Say 'Hey ZERO' to activate.")

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        """Launch background listening thread (non-blocking)."""
        self._stop.clear()
        threading.Thread(target=self._run_loop, daemon=True).start()

    def stop(self):
        self._stop.set()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        if self.on_status:
            self.on_status(msg)
        else:
            print(f"[Listener] {msg}")

    def _run_loop(self):
        """Main mic loop — feeds chunks to OWW, captures speech on trigger."""
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        ) as stream:
            while not self._stop.is_set():
                if self._recording:
                    # Don't double-read while capture is happening
                    import time; time.sleep(0.01)
                    continue

                chunk, _ = stream.read(CHUNK_SIZE)
                audio_np  = chunk.flatten()

                preds = self.oww.predict(audio_np)
                score = max(preds.values(), default=0.0)

                if score >= WAKE_WORD_THRESHOLD:
                    self._log("Wake word detected!")
                    if self.on_wake:
                        self.on_wake("Wake word detected — listening…")
                    self._recording = True
                    self._capture_and_transcribe(stream)
                    self._recording = False
                    self._log("Monitoring for 'Hey ZERO' …")

    def _capture_and_transcribe(self, stream):
        """Record until silence detected, then run Whisper."""
        frames        = []
        silence_count = 0
        max_silence   = int(MAX_SILENCE_SECS * SAMPLE_RATE / CHUNK_SIZE)
        min_speech    = int(MIN_SPEECH_SECS  * SAMPLE_RATE / CHUNK_SIZE)

        while True:
            chunk, _ = stream.read(CHUNK_SIZE)
            flat      = chunk.flatten()
            frames.append(flat)

            rms = np.sqrt(np.mean(flat.astype(np.float32) ** 2))
            silence_count = silence_count + 1 if rms < SILENCE_THRESHOLD else 0

            if silence_count >= max_silence and len(frames) >= min_speech:
                break

        if len(frames) < min_speech:
            return  # too short — probably noise

        audio_f32 = np.concatenate(frames).astype(np.float32) / 32768.0

        self._log("Transcribing …")
        segments, _ = self.whisper.transcribe(audio_f32, language="en", beam_size=5)
        text = " ".join(s.text for s in segments).strip()

        if text:
            self._log(f"Heard: {text}")
            if self.on_transcription:
                self.on_transcription(text)
