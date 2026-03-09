import os
os.environ['PYSTRAY_BACKEND'] = 'gtk'
import os
import time
import threading
import subprocess
import numpy as np
import scipy.io.wavfile as wav
from pynput import keyboard
from groq import Groq
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
import subprocess

# Groq klient - bere API klíč z proměnné prostředí GROQ_API_KEY
client = Groq()

class VoiceAppTray:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.last_ctrl_time = 0
        self.language = "cs"
        self.fs = 44100  # Výchozí frekvence 44.1kHz pro kvalitu
        self.use_correction = True  # Oprava pravopisu zapnuta v základu
        self.icon = None
        self.running = True
        # Definice systémové cesty pro logy (Linux standard)
        home = os.path.expanduser("~")
        self.app_data_dir = os.path.join(home, ".local", "state", "voice_to_text")
        # Vytvoření složky, pokud neexistuje
        os.makedirs(self.app_data_dir, exist_ok=True)
        # Cesty pro log a poslední přepis
        self.log_path = os.path.join(self.app_data_dir, "app.log")
        self.report_path = os.path.join(self.app_data_dir, "last_transcription.txt")
        # Audio soubor můžeme nechat v /tmp, aby se po restartu smazal (volitelné)
        random_number = np.random.randint(1000, 9999)
        self.audio_path = f"/tmp/voice_input_{random_number}.wav"
        # Pro ukládání posledních přepisů pro zobrazení v reportu
        self.last_raw_text = ""
        self.last_corrected_text = ""
        # Pro sledování stavu hudby
        self.was_playing = False
        self.translate_to_english = False

    def log(self, message):
        """Vypíše zprávu do terminálu a uloží ji do logu s časovou značkou."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

    def set_sample_rate(self, rate):
        def inner():
            self.fs = rate
            self.log(f"Vzorkovací frekvence změněna na {rate} Hz")
        return inner        

    def toggle_correction(self):
        self.use_correction = not self.use_correction
        self.log(f"AI oprava pravopisu: {'ZAPNUTA' if self.use_correction else 'VYPNUTA'}")

    def toggle_translation(self):
        self.translate_to_english = not self.translate_to_english
        self.log(f"Překlad do angličtiny: {'ZAPNUT' if self.translate_to_english else 'VYPNUT'}")

    def create_image(self, color):
        """Vytvoří ikonku pro stavovou lištu (kruh)."""
        image = Image.new('RGB', (64, 64))
        d = ImageDraw.Draw(image)
        d.ellipse((5, 5, 59, 59), fill=color)
        return image

    def set_language(self, lang):
        def inner():
            self.language = lang
            self.log(f"Jazyk změněn na: {lang.upper()}")
        return inner

    def quit_app(self):
        self.log("Ukončování aplikace...")
        self.running = False
        if self.icon:
            self.icon.stop()
        os._exit(0)

    def correct_text(self, raw_text):
        """Druhý průchod přes LLM pro opravu pravopisu a čárek."""
        try:
            self.log("Provádím AI korekci textu...")
            if self.language == "cs":
                system_prompt = "Jsi expert na český pravopis. Oprav text: doplň čárky, oprav překlepy a skloňování. Neměň význam, jen oprav chyby. Vrať POUZE opravený text bez úvodních řečí."
            else:
                system_prompt = "You are an expert in English grammar and spelling. Correct the text: add commas, fix typos and grammar. Do not change the meaning, just correct the errors. Return ONLY the corrected text without any introductory speech."
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text}
                ]
            )
            final_text = completion.choices[0].message.content.strip()
            return final_text
        except Exception as e:
            self.log(f"Chyba při korekci: {e}")
            return raw_text

    def translate_text(self, text):
        """Přeloží text do angličtiny pomocí LLM."""
        try:
            self.log("Provádím překlad do angličtiny...")
            system_prompt = "You are a professional translator. Translate the following text to English while preserving the meaning. Return ONLY the translated text without any introductory speech."
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
            )
            final_text = completion.choices[0].message.content.strip()
            return final_text
        except Exception as e:
            self.log(f"Chyba při překladu: {e}")
            return text

    def toggle_music(self, pause=True):
        """Ztlumí/pustí hudbu pomocí playerctl."""
        try:
            if pause:
                self.log("Testuji, jestli hraje hudba...")
                result = subprocess.run(
                    ["playerctl", "status"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.DEVNULL, 
                    text=True
                )                
                status = result.stdout.strip()                
                if status == "Playing":          
                    self.log("Pozastavuji hudbu...")
                    subprocess.run(["playerctl", "pause"], stderr=subprocess.DEVNULL)
                    return True
                else:
                    self.log("Hudba nehrála, není třeba pozastavovat.")
                    return False
            else:
                self.log("Spouštím hudbu...")
                subprocess.run(["playerctl", "play"], stderr=subprocess.DEVNULL)
        except Exception as e:
            self.log(f"Chyba při ovládání hudby: {e}")
            return False

    def robust_paste(self, text):
        """Spolehlivě vloží text do schránky a pak na pozici kurzoru."""
        self.log(f"Vkládám: {text}")
        
        try:
            # 1. Vložení do schránky přes xclip
            process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            process.communicate(input=text.encode('utf-8'))
            
            # 2. Krátká pauza pro systém (důležité pro uvolnění fyzických kláves)
            time.sleep(0.25) 

            # 3. Simulace CTRL+V přes xdotool
            self.log("Vkládám text do aktivního okna...")
            subprocess.run(["xdotool", "key", "ctrl+v"])
            
        except Exception as e:
            self.log(f"CHYBA při vkládání: {e}")

    def record_and_process(self):
        """Vlákno, které teď jen čeká na externí procesy."""
        try:
            # 1. Zvuková signalizace startu
            subprocess.run(["aplay", "-q", "start.wav"], stderr=subprocess.DEVNULL)
            
            # 2. Spuštění EXTERNÍHO nahrávání přes arecord
            # -D default (nebo 'pulse'), -f S16_LE (formát), -c 1 (mono)
            cmd = ["arecord", "-f", "S16_LE", "-r", str(self.fs), "-c", "1", self.audio_path]
            self.recording_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log(f"Externí nahrávání spuštěno (PID: {self.recording_process.pid})")

            # Čekáme, dokud uživatel nahrávání nevypne (recording = False)
            while self.recording:
                time.sleep(0.1)

            # 3. UKONČENÍ nahrávání
            if self.recording_process:
                self.recording_process.terminate() # Pošle SIGTERM, arecord korektně zavře soubor
                self.recording_process.wait()
                self.log("Nahrávání ukončeno externím procesem.")

            # Zvuková signalizace konce
            subprocess.run(["aplay", "-q", "stop.wav"], stderr=subprocess.DEVNULL)

            # 4. EXTERNÍ NORMALIZACE (Zesílení) přes ffmpeg
            postprocessing_start = time.time()
            self.icon.icon = self.create_image("yellow")
            normalized_path = self.audio_path.replace(".wav", "_norm.opus")
            self.log(f"Normalizuji hlasitost přes ffmpeg do {normalized_path} ...")
            
            # Tento příkaz vytáhne hlasitost tak, aby špička byla na 0dB
            # ffmpeg -y -i voice_input_4449.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a libopus -b:a 32k out.opus
            subprocess.run([
                "ffmpeg", "-y", "-i", self.audio_path, 
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", 
                "-ar", "16000", "-c:a", "libopus", "-b:a", "32k", 
                normalized_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log(f"Normalizace dokončena za {time.time() - postprocessing_start:.2f} sekund.")
            self.log(f"Velikost původního souboru: {os.path.getsize(self.audio_path) / 1024:.2f} KB, normalizovaného souboru: {os.path.getsize(normalized_path) / 1024:.2f} KB")

            # 5. Odeslání do Groq (použijeme ten normalizovaný soubor)
            if os.path.exists(normalized_path):
                groq_start = time.time()            
                with open(normalized_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(normalized_path, file.read()),
                        model="whisper-large-v3-turbo",
                        language=self.language,
                        response_format="text"
                    )
                self.log(f"Transkripce dokončena za {time.time() - groq_start:.2f} sekund.")

                self.last_raw_text = transcription.strip()
                self.log(f"Původní přepis: {self.last_raw_text}")
                if self.last_raw_text:
                    text_to_paste = self.last_raw_text
                    if self.use_correction:
                        correction_start = time.time()
                        text_to_paste = self.correct_text(self.last_raw_text)
                        self.log(f"Korekce dokončena za {time.time() - correction_start:.2f} sekund.")
                        self.log(f"Text po korekci: {text_to_paste}")
                    if self.translate_to_english:
                        translation_start = time.time()
                        text_to_paste = self.translate_text(text_to_paste)
                        self.log(f"Překlad dokončen za {time.time() - translation_start:.2f} sekund.")    
                        self.log(f"Text po překladu: {text_to_paste}")
                    self.robust_paste(text_to_paste)
                self.last_corrected_text = text_to_paste
                
                # Úklid
                # os.remove(normalized_path)
            
        except Exception as e:
            self.log(f"CHYBA v externím procesu: {e}")
        finally:
            self.icon.icon = self.create_image("blue")

    def open_logs(self):
        """Otevře systémový log v editoru."""
        if os.path.exists(self.log_path):
            subprocess.run(["xdg-open", self.log_path])

    def show_last_texts(self):
        """Uloží report do systémové složky a otevře ho."""
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(f"PŮVODNÍ:\n{self.last_raw_text}\n\nOPRAVENÝ:\n{self.last_corrected_text}")
        subprocess.run(["xdg-open", self.report_path])            

    def on_press(self, key):
        """Upravená detekce CTRL - jen přepíná vlajku self.recording."""
        if key == keyboard.Key.ctrl:
            now = time.time()
            if now - self.last_ctrl_time < 0.4:
                if not self.recording:
                    self.recording = True
                    self.icon.icon = self.create_image("red")
                    self.was_playing = self.toggle_music(pause=True)
                    threading.Thread(target=self.record_and_process).start()
                else:
                    self.recording = False # To zastaví arecord ve vlákně výše
                    if self.was_playing:
                        self.toggle_music(pause=False)
            self.last_ctrl_time = now

    def run(self):
        # Menu pro ikonku
        menu = pystray.Menu(
            item('Hlasový přepis (2x CTRL)', lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,            
	        item('Čeština', self.set_language('cs'), checked=lambda item: self.language == 'cs'),
            item('English', self.set_language('en'), checked=lambda item: self.language == 'en'),
            pystray.Menu.SEPARATOR,            
            item('Opravovat pravopis (AI)', self.toggle_correction, checked=lambda item: self.use_correction),
            item('Překlad do angličtiny (AI)', self.toggle_translation, checked=lambda item: self.translate_to_english),
            pystray.Menu.SEPARATOR,
            item('Kvalita: 16kHz (Rychlejší)', self.set_sample_rate(16000), checked=lambda item: self.fs == 16000),
            item('Kvalita: 44.1kHz (Věrnější)', self.set_sample_rate(44100), checked=lambda item: self.fs == 44100),
            pystray.Menu.SEPARATOR,
            item('Zobrazit poslední texty', self.show_last_texts),
            item('Otevřít logy', self.open_logs),            
            pystray.Menu.SEPARATOR,            
            item('Ukončit', self.quit_app)
        )

        self.icon = pystray.Icon("VoiceToText", self.create_image("blue"), "Voice to Text (Ctrl+Ctrl)", menu)
        
        # Spuštění keyboard listeneru
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        
        self.log("Aplikace spuštěna. Ikonka je v systray.")
        self.log("Stiskni 2x klávesu CTRL pro start/stop nahrávání.")
        
        # Spuštění ikonky (zablokuje hlavní vlákno)
        self.icon.run()

if __name__ == "__main__":
    import shutil
    # test that aplay and arecord are available
    for cmd in ["aplay", "arecord", "ffmpeg", "xclip", "xdotool", "playerctl"]:
        if not shutil.which(cmd):
            print(f"❌ CHYBA: Nástroj '{cmd}' není v systému dostupný! Ujistěte se, že je nainstalován a v PATH.")
            exit(1)
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ CHYBA: Chybí GROQ_API_KEY v prostředí!")
    else:
        app = VoiceAppTray()
        app.run()

