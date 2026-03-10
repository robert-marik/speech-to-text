"""Přepis audia, oprava pravopisu a překlad přes Groq API."""

import time

from groq import Groq

from .config import WHISPER_MODEL, LLM_MODEL
from .logger import Logger


class Transcriber:
    def __init__(self, logger: Logger):
        self.logger = logger
        self._client = Groq()

    def transcribe(self, audio_path: str, language: str) -> str:
        """Přepíše audio soubor na text pomocí Whisper přes Groq."""
        start = time.time()
        with open(audio_path, "rb") as f:
            transcription = self._client.audio.transcriptions.create(
                file=(audio_path, f.read()),
                model=WHISPER_MODEL,
                language=language,
                response_format="text",
            )
        self.logger.log(f"Transkripce dokončena za {time.time() - start:.2f} sekund.")
        return transcription.strip()

    def correct(self, text: str, language: str) -> str:
        """Opraví pravopis a čárky pomocí LLM."""
        try:
            self.logger.log("Provádím AI korekci textu...")
            if language == "cs":
                system_prompt = (
                    "Jsi expert na český pravopis. Oprav text: doplň čárky, oprav překlepy "
                    "a skloňování. Neměň význam, jen oprav chyby. Vrať POUZE opravený text "
                    "bez úvodních řečí."
                )
            else:
                system_prompt = (
                    "You are an expert in English grammar and spelling. Correct the text: "
                    "add commas, fix typos and grammar. Do not change the meaning, just correct "
                    "the errors. Return ONLY the corrected text without any introductory speech."
                )
            start = time.time()
            completion = self._client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            )
            result = completion.choices[0].message.content.strip()
            self.logger.log(f"Korekce dokončena za {time.time() - start:.2f} sekund.")
            return result
        except Exception as e:
            self.logger.log(f"Chyba při korekci: {e}")
            return text

    def translate(self, text: str) -> str:
        """Přeloží text do angličtiny pomocí LLM."""
        try:
            self.logger.log("Provádím překlad do angličtiny...")
            system_prompt = (
                "You are a professional translator. Translate the following text to English "
                "while preserving the meaning. Return ONLY the translated text without any "
                "introductory speech."
            )
            start = time.time()
            completion = self._client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            )
            result = completion.choices[0].message.content.strip()
            self.logger.log(f"Překlad dokončen za {time.time() - start:.2f} sekund.")
            return result
        except Exception as e:
            self.logger.log(f"Chyba při překladu: {e}")
            return text
