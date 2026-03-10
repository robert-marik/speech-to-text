"""Jednoduchý logger zapisující do terminálu i souboru."""

import os
import time

from .config import LOG_PATH, APP_DATA_DIR


class Logger:
    def __init__(self, log_path: str = LOG_PATH):
        self.log_path = log_path
        os.makedirs(APP_DATA_DIR, exist_ok=True)

    def log(self, message: str) -> None:
        """Vypíše zprávu do terminálu a uloží ji do logu s časovou značkou."""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        print(entry)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

    def open_log_file(self) -> None:
        """Otevře log soubor v systémovém editoru."""
        import subprocess
        if os.path.exists(self.log_path):
            subprocess.run(["xdg-open", self.log_path])
