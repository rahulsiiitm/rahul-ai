import re
import queue
import threading
import os
import sys
from config import PIPER_MODEL_PATH
import subprocess

class ZeroVoice:
    def __init__(self):
        self.model = PIPER_MODEL_PATH
        self.token_queue = queue.Queue()
        self._buffer = ""  # sentence accumulation buffer
        
        venv_bin_dir = os.path.dirname(sys.executable)
        self.piper_binary = os.path.join(venv_bin_dir, "piper")
        if not os.path.exists(self.piper_binary):
            self.piper_binary = "piper"

        self.start_audio_engine()
        self.worker = threading.Thread(target=self._stream_worker, daemon=True)
        self.worker.start()

    # Sentence boundary pattern — flush on . ! ? followed by space or end
    _SENTENCE_END = re.compile(r'[.!?]["\']?\s')

    def _flush_buffer(self, force=False):
        """Write buffered text to Piper if it contains a complete sentence (or force-flush)."""
        if not self._buffer.strip():
            return

        if force:
            text = self._buffer.strip()
            self._buffer = ""
        else:
            # Split at the last sentence boundary, keep the remainder buffered
            match = None
            for m in self._SENTENCE_END.finditer(self._buffer):
                match = m
            if not match:
                return  # no complete sentence yet
            split_at = match.end()
            text = self._buffer[:split_at].strip()
            self._buffer = self._buffer[split_at:]

        if not text:
            return

        if not hasattr(self, 'process') or self.process.poll() is not None:
            self.start_audio_engine()

        clean = text.replace("'", "").replace('"', '')
        try:
            self.process.stdin.write(clean + "\n")
            self.process.stdin.flush()
        except Exception as e:
            print(f"\n[ZERO Voice Flush Error]: {e}")

    def _stream_worker(self):
        while True:
            try:
                token = self.token_queue.get()
                if token is None:
                    break

                if token == "\n":          # end_of_turn signal
                    self._flush_buffer(force=True)
                else:
                    self._buffer += token
                    self._flush_buffer()   # flush if sentence complete

                self.token_queue.task_done()
            except Exception as e:
                print(f"\n[ZERO Voice Stream Error]: {e}")

    def stream_token(self, token: str):
        if token:
            self.token_queue.put(token)

    def end_of_turn(self):
        self.token_queue.put("\n")  # triggers force-flush of any remaining buffer

    def start_audio_engine(self):
        """Launches Piper and aplay as a single long-lived background pipeline."""
        if not os.path.exists(self.model):
            print(f"\n[ZERO Voice Error]: Audio weights file missing at {self.model}")
            return

        command = f"{self.piper_binary} --model {self.model} --output-raw | aplay -r 22050 -f S16_LE -t raw -"
        
        self.process = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )