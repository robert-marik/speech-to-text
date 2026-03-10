# Voice to Text

Systray applet pro Linux, který nahrává hlas, přepisuje ho přes Whisper (Groq API)
a volitelně opravuje pravopis nebo překládá do angličtiny pomocí LLM.

## Požadavky

### Systémové nástroje
```bash
sudo apt install alsa-utils ffmpeg xclip xdotool playerctl
```

### Python závislosti
```bash
pip install -e .
```

### API klíč
```bash
export GROQ_API_KEY="váš_klíč"
```

### Fix pro systra

```bash
export PYSTRAY_BACKEND='gtk'
```

## Spuštění
```bash
python main.py
```
nebo
```bash 
python -m voice_to_text
```

## Ovládání
- **2× Ctrl** – zahájí / ukončí nahrávání
- Pravým kliknutím na ikonu v systray se otevře menu

## Struktura projektu
```
voice_to_text/
├── main.py                  # Vstupní bod
├── pyproject.toml
├── README.md
└── voice_to_text/
    ├── __init__.py
    ├── __main__.py          # python -m voice_to_text
    ├── config.py            # Konstanty a konfigurace
    ├── logger.py            # Logování
    ├── audio.py             # Nahrávání a normalizace
    ├── transcriber.py       # Přepis, korekce, překlad (Groq)
    ├── clipboard.py         # Vkládání textu (xclip + xdotool)
    ├── music.py             # Ovládání přehrávače (playerctl)
    └── tray.py              # Systray ikona, menu, hlavní logika
```
