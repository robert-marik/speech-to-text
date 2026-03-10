"""Ovládání přehrávače hudby přes playerctl."""

import subprocess

from .logger import Logger


class MusicController:
    def __init__(self, logger: Logger):
        self.logger = logger

    def pause_if_playing(self) -> bool:
        """Pozastaví přehrávač, pokud zrovna hraje. Vrací True, pokud bylo pozastaveno."""
        try:
            self.logger.log("Testuji, jestli hraje hudba...")
            result = subprocess.run(
                ["playerctl", "status"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            if result.stdout.strip() == "Playing":
                self.logger.log("Pozastavuji hudbu...")
                subprocess.run(["playerctl", "pause"], stderr=subprocess.DEVNULL)
                return True
            self.logger.log("Hudba nehrála, není třeba pozastavovat.")
            return False
        except Exception as e:
            self.logger.log(f"Chyba při ovládání hudby: {e}")
            return False

    def resume(self) -> None:
        """Spustí přehrávač."""
        try:
            self.logger.log("Spouštím hudbu...")
            subprocess.run(["playerctl", "play"], stderr=subprocess.DEVNULL)
        except Exception as e:
            self.logger.log(f"Chyba při spouštění hudby: {e}")
