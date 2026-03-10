"""Ikona v systray a kontextové menu."""

import os
import subprocess
import threading

from PIL import Image, ImageDraw
from pynput import keyboard
import pystray
from pystray import MenuItem as item

from .audio import AudioRecorder
from .clipboard import ClipboardPaster
from .config import (
    APP_DATA_DIR,
    DEFAULT_LANGUAGE,
    DEFAULT_SAMPLE_RATE,
    ICON_COLORS,
    ICON_SIZE,
    MAX_RECORDING_SECONDS,
    REPORT_PATH,
)
from .logger import Logger
from .music import MusicController
from .transcriber import Transcriber


class VoiceAppTray:
    def __init__(self):
        os.environ.setdefault("PYSTRAY_BACKEND", "gtk")
        os.makedirs(APP_DATA_DIR, exist_ok=True)

        self.logger = Logger()
        self.music = MusicController(self.logger)
        self.paster = ClipboardPaster(self.logger)
        self.transcriber = Transcriber(self.logger)

        self.language = DEFAULT_LANGUAGE
        self.fs = DEFAULT_SAMPLE_RATE
        self.use_correction = True
        self.translate_to_english = False

        self.recording = False
        self.was_playing = False
        self.last_ctrl_time = 0
        self.last_raw_text = ""
        self.last_corrected_text = ""

        self.icon: pystray.Icon | None = None
        self.running = True
        self._recorder: AudioRecorder | None = None

    # ------------------------------------------------------------------ #
    # Ikona                                                                #
    # ------------------------------------------------------------------ #

    def _create_image(self, color: str) -> Image.Image:
        image = Image.new("RGB", ICON_SIZE)
        d = ImageDraw.Draw(image)
        d.ellipse((5, 5, 59, 59), fill=color)
        return image

    def _set_icon_color(self, state: str) -> None:
        if self.icon:
            self.icon.icon = self._create_image(ICON_COLORS[state])

    # ------------------------------------------------------------------ #
    # Menu callbacky                                                       #
    # ------------------------------------------------------------------ #

    def set_language(self, lang: str):
        def inner():
            self.language = lang
            self.logger.log(f"Jazyk změněn na: {lang.upper()}")
        return inner

    def set_sample_rate(self, rate: int):
        def inner():
            self.fs = rate
            self.logger.log(f"Vzorkovací frekvence změněna na {rate} Hz")
        return inner

    def toggle_correction(self) -> None:
        self.use_correction = not self.use_correction
        self.logger.log(f"AI oprava pravopisu: {'ZAPNUTA' if self.use_correction else 'VYPNUTA'}")

    def toggle_translation(self) -> None:
        self.translate_to_english = not self.translate_to_english
        self.logger.log(f"Překlad do angličtiny: {'ZAPNUT' if self.translate_to_english else 'VYPNUT'}")

    def show_last_texts(self) -> None:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(f"PŮVODNÍ:\n{self.last_raw_text}\n\nOPRAVENÝ:\n{self.last_corrected_text}")
        subprocess.run(["xdg-open", REPORT_PATH])

    def quit_app(self) -> None:
        self.logger.log("Ukončování aplikace...")
        self.running = False
        if self.icon:
            self.icon.stop()
        os._exit(0)

    # ------------------------------------------------------------------ #
    # Nahrávání a zpracování                                               #
    # ------------------------------------------------------------------ #

    def _record_and_process(self) -> None:
        text_to_paste = ""
        recorder = AudioRecorder(self.logger, self.fs)
        self._recorder = recorder

        try:
            recorder.start()
            recorder.wait_for_stop(
                stop_flag_fn=lambda: self.recording,
                on_timeout_fn=lambda: self.music.resume() if self.was_playing else None,
            )
            recorder.stop()

            self._set_icon_color("processing")

            if not recorder.normalize():
                self.logger.log("Normalizace selhala, přeskakuji přepis.")
                return

            raw = self.transcriber.transcribe(recorder.normalized_path, self.language)
            self.last_raw_text = raw
            self.logger.log(f"Původní přepis: {raw}")

            if raw:
                text_to_paste = raw
                if self.use_correction:
                    text_to_paste = self.transcriber.correct(raw, self.language)
                    self.logger.log(f"Text po korekci: {text_to_paste}")
                if self.translate_to_english:
                    text_to_paste = self.transcriber.translate(text_to_paste)
                    self.logger.log(f"Text po překladu: {text_to_paste}")
                self.paster.paste(text_to_paste)

        except Exception as e:
            self.logger.log(f"CHYBA v procesu nahrávání: {e}")
        finally:
            self.last_corrected_text = text_to_paste
            self._set_icon_color("idle")
            self._recorder = None

    # ------------------------------------------------------------------ #
    # Klávesnice                                                           #
    # ------------------------------------------------------------------ #

    def on_press(self, key) -> None:
        import time
        if key == keyboard.Key.ctrl:
            now = time.time()
            if now - self.last_ctrl_time < 0.4:
                if not self.recording:
                    self.recording = True
                    self._set_icon_color("recording")
                    self.was_playing = self.music.pause_if_playing()
                    threading.Thread(target=self._record_and_process, daemon=True).start()
                else:
                    self.recording = False
                    if self.was_playing:
                        self.music.resume()
            self.last_ctrl_time = now

    # ------------------------------------------------------------------ #
    # Spuštění                                                             #
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        menu = pystray.Menu(
            item("Hlasový přepis (2x CTRL)", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("Čeština", self.set_language("cs"), checked=lambda i: self.language == "cs"),
            item("English", self.set_language("en"), checked=lambda i: self.language == "en"),
            pystray.Menu.SEPARATOR,
            item("Opravovat pravopis (AI)", self.toggle_correction, checked=lambda i: self.use_correction),
            item("Překlad do angličtiny (AI)", self.toggle_translation, checked=lambda i: self.translate_to_english),
            pystray.Menu.SEPARATOR,
            item("Kvalita: 16kHz (Rychlejší)", self.set_sample_rate(16000), checked=lambda i: self.fs == 16000),
            item("Kvalita: 44.1kHz (Věrnější)", self.set_sample_rate(44100), checked=lambda i: self.fs == 44100),
            pystray.Menu.SEPARATOR,
            item("Zobrazit poslední texty", self.show_last_texts),
            item("Otevřít logy", self.logger.open_log_file),
            pystray.Menu.SEPARATOR,
            item("Ukončit", self.quit_app),
        )

        self.icon = pystray.Icon(
            "VoiceToText",
            self._create_image(ICON_COLORS["idle"]),
            "Voice to Text (Ctrl+Ctrl)",
            menu,
        )

        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()

        self.logger.log("Aplikace spuštěna. Ikonka je v systray.")
        self.logger.log("Stiskni 2x klávesu CTRL pro start/stop nahrávání.")
        self.logger.log(f"Maximální délka nahrávání: {MAX_RECORDING_SECONDS}s.")

        self.icon.run()
