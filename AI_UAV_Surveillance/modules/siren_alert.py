import threading

try:
    import pygame
except Exception:
    pygame = None


class SirenAlert:
    def __init__(self, sound_path):
        self.sound_path = str(sound_path)
        self.ready = False
        self.lock = threading.Lock()
        if pygame:
            try:
                pygame.mixer.init()
                self.ready = True
            except Exception:
                self.ready = False

    def play(self):
        if not self.ready:
            return
        threading.Thread(target=self._play, daemon=True).start()

    def _play(self):
        with self.lock:
            try:
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(self.sound_path)
                    pygame.mixer.music.play()
            except Exception:
                pass
