import threading
import time

try:
    import pyttsx3
except Exception:
    pyttsx3 = None


class VoiceAlert:
    def __init__(self, cooldown=5):
        self.cooldown = cooldown
        self.last_spoken = {}
        self.lock = threading.Lock()

    def speak(self, class_name):
        if pyttsx3 is None:
            return
        now = time.time()
        with self.lock:
            if now - self.last_spoken.get(class_name, 0) < self.cooldown:
                return
            self.last_spoken[class_name] = now
        threading.Thread(target=self._speak, args=(class_name,), daemon=True).start()

    def _speak(self, class_name):
        try:
            engine = pyttsx3.init()
            engine.say(f"Warning! {class_name} detected.")
            engine.runAndWait()
        except Exception:
            pass
