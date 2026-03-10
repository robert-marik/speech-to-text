"""Konfigurace a konstanty aplikace."""

import os

MAX_RECORDING_SECONDS = 120
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_LANGUAGE = "cs"

APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "state", "voice_to_text")
LOG_PATH = os.path.join(APP_DATA_DIR, "app.log")
REPORT_PATH = os.path.join(APP_DATA_DIR, "last_transcription.txt")

WHISPER_MODEL = "whisper-large-v3-turbo"
LLM_MODEL = "llama-3.3-70b-versatile"

REQUIRED_SYSTEM_TOOLS = ["aplay", "arecord", "ffmpeg", "xclip", "xdotool", "playerctl"]

ICON_SIZE = (64, 64)
ICON_COLORS = {
    "idle": "blue",
    "recording": "red",
    "processing": "yellow",
}
