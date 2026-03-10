"""Nahrávání zvuku a jeho zpracování (normalizace přes ffmpeg)."""

import os
import subprocess
import time

import numpy as np

from .config import MAX_RECORDING_SECONDS
from .logger import Logger


class AudioRecorder:
    def __init__(self, logger: Logger, sample_rate: int):
        self.logger = logger
        self.sample_rate = sample_rate
        random_number = np.random.randint(1000, 9999)
        self.audio_path = f"/tmp/voice_input_{random_number}.wav"
        self.normalized_path = self.audio_path.replace(".wav", "_norm.opus")
        self._process: subprocess.Popen | None = None
        self.is_recording = False

    def start(self) -> None:
        """Spustí externí nahrávání přes arecord."""
        subprocess.run(["aplay", "-q", "start.wav"], stderr=subprocess.DEVNULL)
        cmd = ["arecord", "-f", "S16_LE", "-r", str(self.sample_rate), "-c", "1", self.audio_path]
        self._process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.is_recording = True
        self.logger.log(f"Externí nahrávání spuštěno (PID: {self._process.pid})")

    def wait_for_stop(self, stop_flag_fn, on_timeout_fn=None) -> None:
        """Blokuje, dokud stop_flag_fn() nevrátí False nebo nevyprší timeout."""
        start_time = time.time()
        while stop_flag_fn():
            time.sleep(0.1)
            if time.time() - start_time >= MAX_RECORDING_SECONDS:
                self.logger.log(f"⚠️ Timeout: nahrávání automaticky ukončeno po {MAX_RECORDING_SECONDS}s.")
                self.is_recording = False
                if on_timeout_fn:
                    on_timeout_fn()
                break

    def stop(self) -> None:
        """Ukončí nahrávací proces."""
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None
        self.is_recording = False
        subprocess.run(["aplay", "-q", "stop.wav"], stderr=subprocess.DEVNULL)
        self.logger.log("Nahrávání ukončeno.")

    def normalize(self) -> bool:
        """Normalizuje hlasitost a převede soubor do opus formátu přes ffmpeg.
        
        Vrací True při úspěchu, False při chybě.
        """
        self.logger.log(f"Normalizuji hlasitost přes ffmpeg do {self.normalized_path} ...")
        start = time.time()
        result = subprocess.run([
            "ffmpeg", "-y", "-i", self.audio_path,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "16000", "-c:a", "libopus", "-b:a", "32k",
            self.normalized_path,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.logger.log(f"Normalizace dokončena za {time.time() - start:.2f} sekund.")
        if os.path.exists(self.audio_path) and os.path.exists(self.normalized_path):
            orig_kb = os.path.getsize(self.audio_path) / 1024
            norm_kb = os.path.getsize(self.normalized_path) / 1024
            self.logger.log(f"Původní: {orig_kb:.2f} KB → Normalizovaný: {norm_kb:.2f} KB")
        return result.returncode == 0 and os.path.exists(self.normalized_path)
