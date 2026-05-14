import os
import time
import asyncio
import numpy as np
import edge_tts
import soundfile as sf
import tempfile

class Tts:
    def __init__(self, params=None, ap=None, ui=None):
        self.params = params or {}
        self.voice = self.params.get("voice", "it-IT-DiegoNeural")
        self.language = self.params.get("language", "it")
        self.ap = ap  
        self.ui = ui 

    def set_voice_params(self, voice, language):
        self.language = language
        
        voice_map = {
            "im_nicola": "it-IT-DiegoNeural",
            "if_sara": "it-IT-ElsaNeural",
            "am_eric": "en-US-GuyNeural",
            "af_sarah": "en-US-AriaNeural",
            "onyx": "it-IT-DiegoNeural",
            "nova": "it-IT-ElsaNeural",
            "echo": "en-US-GuyNeural",
            "shimmer": "en-US-AriaNeural",
            "alloy": "it-IT-DiegoNeural"
        }
        
        self.voice = voice_map.get(voice, voice)
        if "Neural" not in self.voice:
            self.voice = "it-IT-DiegoNeural" if language == "it" else "en-US-GuyNeural"

    def setup_voice_cloning(self, enabled, ref_path, ref_text):
        pass

    async def _async_generate_audio(self, text, output_file):
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_file)

    def run_tts_sync(self, data, on_answer_callback=None):
        clean_data = data.strip().replace("\n", " ")
        if not clean_data:
            return "tts_done"

        if self.ui:
            self.ui.update_status("⚙️ Sto generando l'audio...", "#e67e22")

        mp3_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f_mp3:
                mp3_path = f_mp3.name

            asyncio.run(self._async_generate_audio(clean_data, mp3_path))

            audio_data, sr = sf.read(mp3_path, dtype='int16')
            
            if len(audio_data.shape) > 1:
                audio_data = audio_data[:, 0]
                
            threshold = 200
            active_indices = np.where(np.abs(audio_data) > threshold)[0]
            if len(active_indices) > 0:
                audio_data = audio_data[active_indices[0]:active_indices[-1]]
                
            duration = len(audio_data) / sr

            if os.path.exists(mp3_path):
                try: os.remove(mp3_path)
                except: pass

            if on_answer_callback:
                on_answer_callback(clean_data, duration)

            if self.ap:
                self.ap.play_sound(audio_data)
                self.ap.check_audio_finished()

        except Exception as e:
            print(f"[TTS ERROR] {e}")
            if os.path.exists(mp3_path):
                try: os.remove(mp3_path)
                except: pass

        return "tts_done"

    def run_tts(self, data, on_chunk_callback=None):
        return self.run_tts_sync(data, None)