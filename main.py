"""Vstupní bod aplikace – kontrola závislostí a spuštění."""

import os
os.environ['PYSTRAY_BACKEND'] = 'gtk'
import shutil
import sys

from voice_to_text.config import REQUIRED_SYSTEM_TOOLS
from voice_to_text.tray import VoiceAppTray


def check_dependencies() -> bool:
    ok = True
    for cmd in REQUIRED_SYSTEM_TOOLS:
        if not shutil.which(cmd):
            print(f"❌ CHYBA: Nástroj '{cmd}' není v systému dostupný! Ujistěte se, že je nainstalován a v PATH.")
            ok = False
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ CHYBA: Chybí GROQ_API_KEY v prostředí!")
        ok = False
    return ok


def main() -> None:
    if not check_dependencies():
        sys.exit(1)
    app = VoiceAppTray()
    app.run()


if __name__ == "__main__":
    main()
