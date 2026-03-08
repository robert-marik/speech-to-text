import os
os.environ['PYSTRAY_BACKEND'] = 'gtk'
import os
import time
import threading
import subprocess
import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd
from pynput import keyboard
from groq import Groq
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
import subprocess

# --- KONFIGURACE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILENAME = os.path.join(BASE_DIR, "input_audio.wav")

# Groq klient - bere API klíč z proměnné prostředí GROQ_API_KEY
client = Groq()

class VoiceAppTray:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.last_ctrl_time = 0
        self.language = "cs"  # Výchozí jazyk
        self.fs = 16000
        self.icon = None
        self.running = True

    def log(self, message):
        """Vypíše zprávu do terminálu s časovou značkou."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def set_sample_rate(self, rate):
        def inner():
            self.fs = rate
            self.log(f"Vzorkovací frekvence změněna na: {rate} Hz")
        return inner        

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

    def toggle_music(self, pause=True):
        """Ztlumí/pustí hudbu pomocí playerctl."""
        try:
            if pause:
                self.log("Pozastavuji hudbu...")
                subprocess.run(["playerctl", "pause"], stderr=subprocess.DEVNULL)
            else:
                self.log("Spouštím hudbu...")
                subprocess.run(["playerctl", "play"], stderr=subprocess.DEVNULL)
        except:
            pass

    def robust_paste(self, text):
        """Spolehlivě vloží text do schránky a pak na pozici kurzoru."""
        self.log(f"Získán přepis: {text}")
        
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
        """Pracovní vlákno pro záznam a AI zpracování."""
        self.audio_data = []
        try:
            # Nahrávání
            subprocess.run(["aplay", "-q", "start.wav"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with sd.InputStream(samplerate=self.fs, channels=1, callback=lambda indata, f, t, s: self.audio_data.append(indata.copy()) if self.recording else None):
                while self.recording:
                    time.sleep(0.1)
            
            subprocess.run(["aplay", "-q", "stop.wav"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if self.audio_data:
                # Změna ikonky na "zpracovávám" (žlutá)
                self.icon.icon = self.create_image("yellow")
                self.log("Zpracovávám zvuk přes Groq AI...")
                
                # Uložení do WAV
                recorded_chunk = np.concatenate(self.audio_data, axis=0)
                wav.write(FILENAME, self.fs, recorded_chunk)
                
                # Groq Whisper API
                with open(FILENAME, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(FILENAME, file.read()),
                        model="whisper-large-v3-turbo",
                        language=self.language,
                        response_format="text"
                    )
                
                if transcription.strip():
                    self.robust_paste(transcription.strip())
                else:
                    self.log("AI nevrátila žádný text (ticho?).")
        except Exception as e:
            self.log(f"CHYBA v procesu: {e}")
        finally:
            self.icon.icon = self.create_image("blue") # Zpět do klidu

    def on_press(self, key):
        """Detekce dvojitého stisku CTRL."""
        if key == keyboard.Key.ctrl:
            now = time.time()
            if now - self.last_ctrl_time < 0.4:
                if not self.recording:
                    self.log("START nahrávání...")
                    self.recording = True
                    self.icon.icon = self.create_image("red")
                    self.toggle_music(True)
                    threading.Thread(target=self.record_and_process).start()
                else:
                    self.log("STOP nahrávání...")
                    self.recording = False
                    self.toggle_music(False)
            self.last_ctrl_time = now

    def run(self):
        # Menu pro ikonku
        menu = pystray.Menu(
            item('Hlasový přepis (2x CTRL)', lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item('Čeština', self.set_language('cs'), checked=lambda item: self.language == 'cs'),
            item('English', self.set_language('en'), checked=lambda item: self.language == 'en'),
            item('Deutsch', self.set_language('de'), checked=lambda item: self.language == 'de'),
            pystray.Menu.SEPARATOR,
            item('Kvalita: 16kHz (Rychlejší)', self.set_sample_rate(16000), checked=lambda item: self.fs == 16000),
            item('Kvalita: 44.1kHz (Věrnější)', self.set_sample_rate(44100), checked=lambda item: self.fs == 44100),
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
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ CHYBA: Musíš nastavit proměnnou prostředí GROQ_API_KEY!")
    else:
        app = VoiceAppTray()
        app.run()