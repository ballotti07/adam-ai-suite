class Stt:
    def __init__(self, params=None):
        self.params = params or {}
        self.language = self.params.get("language", "en")
        print("[STT] Stub inizializzato.")

    def transcribe_translate(self, data):
        return ""

    def transcribe_translate_file(self, filename):
        return ""