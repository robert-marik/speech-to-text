"""Vkládání textu do schránky a aktivního okna."""

import subprocess
import time

from .logger import Logger


class ClipboardPaster:
    def __init__(self, logger: Logger):
        self.logger = logger

    def paste(self, text: str) -> None:
        """Vloží text do schránky (xclip) a pak simuluje Ctrl+V (xdotool)."""
        self.logger.log(f"Vkládám: {text}")
        try:
            process = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            process.communicate(input=text.encode("utf-8"))
            time.sleep(0.25)
            self.logger.log("Vkládám text do aktivního okna...")
            subprocess.run(["xdotool", "key", "ctrl+v"])
        except Exception as e:
            self.logger.log(f"CHYBA při vkládání: {e}")
