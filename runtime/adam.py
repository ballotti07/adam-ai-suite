import time
import numpy as np
from enum import Enum

from core.vad import Vad
from core.stt import Stt
from core.llm import Llm
from core.tts import Tts
from core.ap import Ap
from core.mic import Mic
from core.utils import remove_emojis, remove_code_blocks, remove_multiple_dots

class State(Enum):
    IDLE = 0
    LISTEN = 1
    TALK = 2

PROMPTS = {
    "it": "Sei un assistente virtuale intelligente e simpatico. Rispondi in modo conciso (max 20 parole). Parla SEMPRE in ITALIANO.",
    "en": "You are a smart and funny virtual assistant. Answer concisely (max 20 words). Always speak in ENGLISH."
}
VOICE_MAP_LOCAL = { "it": {"male": "im_nicola", "female": "if_sara"}, "en": {"male": "am_eric", "female": "af_sarah"} }
VOICE_MAP_OPENAI = { "it": {"male": "onyx", "female": "nova"}, "en": {"male": "echo", "female": "shimmer"} }

class Adam:
    def __init__(self, ui, config):
        self.ui = ui
        self.config = config
        self.vad_params = config.get("Vad", {}).get("params", {})
        self.stt_params = config.get("Stt_Local", {}).get("params", {})
        self.llm_params = config.get("Llm_Local", {}).get("params", {})
        self.tts_params = config.get("Tts_Local", {}).get("params", {})
        self.ap_params = config.get("Ap", {}).get("params", {})
        self.mic_params = config.get("Mic", {}).get("params", {})
        self.ui.log_message("system", "loading...")
        self.vad = Vad(params=self.vad_params)
        self.stt = Stt(params=self.stt_params)
        self.llm = Llm(params=self.llm_params)
        self.ap = Ap(params=self.ap_params)
        self.ap.on_playback_chunk = self.on_volume_update
        self.tts = Tts(params=self.tts_params, ap=self.ap, ui=self.ui)
        self.mic = Mic(params=self.mic_params, vad_params=self.vad_params)
        self.state = State.IDLE
        self.mic_muted = True 
        self.mic_last_chunk = None
        self.do_quit = False
        self.is_profile_loaded = False 
        self.ui.set_callbacks(
            on_toggle_mute=self.on_toggle_mute,
            on_reset_chat=self.on_reset_chat,
            on_exit=self.on_exit,
            on_profile_loaded=self.on_profile_loaded,
            on_language_change=self.on_language_change
        )

    def on_profile_loaded(self, profile_data):
        lang = profile_data.get("language", "en").lower()
        gender = profile_data.get("gender", "male").lower()
        self.current_gender = gender
        self.stt.language = lang
        voice_cloning = profile_data.get("voice_cloning", False)
        voice_ref_path = profile_data.get("voice_ref_path", "")
        voice_ref_text = profile_data.get("voice_ref_text", "")
        self.tts.setup_voice_cloning(voice_cloning, voice_ref_path, voice_ref_text)
        
        if "custom_prompt" in profile_data and profile_data["custom_prompt"].strip():
            base_prompt = profile_data["custom_prompt"]
            is_closed_domain = True
        else:
            base_prompt = ""
            is_closed_domain = False
            
        if is_closed_domain:
            SYSTEM_RULES = {
                "it": ("\n[REGOLE]\n1. Sei il personaggio descritto sopra. Rispondi in prima persona in modo naturale.\n2. Lunghezza massima: 20 parole.\n3. Se ti fanno domande su argomenti che escono dal tuo personaggio (es. storia, calcoli), usa la frase di sicurezza.\n\nESEMPIO DI COMPORTAMENTO:\nUtente: Qual è la capitale della Francia?\nTu: Mi dispiace, non ho questa informazione."),
                "en": ("\n[RULES]\n1. You are the character described above. Answer in the first person naturally.\n2. Maximum length: 20 words.\n3. If asked about topics outside your persona (e.g. history, math), use the safety phrase.\n\nEXAMPLE OF BEHAVIOR:\nUser: What is the capital of France?\nYou: I apologize, I do not have this information.")
            }
            enforced_rules = SYSTEM_RULES.get(lang, SYSTEM_RULES["en"])
            self.llm.system_message = f"--- LA TUA IDENTITÀ ---\n{base_prompt}\n----------------------\n{enforced_rules}"
        else:
            SYSTEM_RULES_OPEN = {
                "it": "Sei un assistente virtuale intelligente e simpatico. Rispondi a qualsiasi domanda in modo naturale e conciso (max 20 parole). Parla SEMPRE in ITALIANO.",
                "en": "You are a smart and funny virtual assistant. Answer any question naturally and concisely (max 20 words). Always speak in ENGLISH."
            }
            self.llm.system_message = SYSTEM_RULES_OPEN.get(lang, SYSTEM_RULES_OPEN["en"])
            
        self.llm.reset_chat()
        is_local_tts = "localhost" in self.tts_params.get("base_url", "")
        target_voice = "alloy"
        if is_local_tts:
            if lang in VOICE_MAP_LOCAL and gender in VOICE_MAP_LOCAL[lang]:
                target_voice = VOICE_MAP_LOCAL[lang][gender]
        else:
            if lang in VOICE_MAP_OPENAI and gender in VOICE_MAP_OPENAI[lang]:
                target_voice = VOICE_MAP_OPENAI[lang][gender]
                
        self.tts.set_voice_params(target_voice, lang)
        self.mic.mute()        
        self.mic_muted = True   
        self.vad.reset_vad()
        self.ui.update_status("🟢 PRONTO (Premi SPAZIO per parlare)", "#2ecc71")
        self.is_profile_loaded = True
        self.mic.start_mic()

    def on_toggle_mute(self):
        if not self.is_profile_loaded: return 
        if self.mic_muted:
            self.mic.unmute()
            self.mic_muted = False
            self.vad.reset_vad()
            self.ui.update_status("🟢 PRONTO (Parla pure...)", "#2ecc71")
        else:
            self.mic.mute()
            self.mic_muted = True
            self.ui.update_status("🔴 MUTO (Premi SPAZIO per parlare)", "#ff6b6b")

    def on_reset_chat(self):
        if self.state != State.TALK:
            self.llm.reset_chat()
            self.ui.clear_chat()
            self.ui.update_status("⚠️ MEMORIA PULITA", "#e67e22")

    def on_exit(self):
        self.do_quit = True
        try:
            self.mic.close()
            self.ap.close()
        except Exception:
            pass

    def on_volume_update(self, volume):
        self.ui.ui_queue.put(("volume", volume))

    def on_language_change(self, lang_code):
        self.stt.language = lang_code
        self.llm.language = lang_code
        if self.is_profile_loaded:
            gender = getattr(self, 'current_gender', 'male')
            is_local_tts = "localhost" in self.tts_params.get("base_url", "")
            target_voice = "alloy"
            if is_local_tts:
                if lang_code in VOICE_MAP_LOCAL and gender in VOICE_MAP_LOCAL[lang_code]:
                    target_voice = VOICE_MAP_LOCAL[lang_code][gender]
            else:
                if lang_code in VOICE_MAP_OPENAI and gender in VOICE_MAP_OPENAI[lang_code]:
                    target_voice = VOICE_MAP_OPENAI[lang_code][gender]
            self.tts.set_voice_params(target_voice, lang_code)

    def on_transcript(self, text):
        self.ui.log_message("user says", text)

    def on_answer(self, text, audio_duration=0, log_to_chat=True):
        self.ui.update_status("🔵 PARLO...", "#3498db")
        
        if audio_duration == -1:
            self.ui.log_message("adam says", text)
            return

        if log_to_chat:
            self.ui.log_message("adam says", text)
        
        self.ui.say(text, audio_duration)

    def on_tts_chunk(self, volume):
        target_lip = "end"
        if volume > 2500: target_lip = "A"
        elif volume > 1500: target_lip = "O"
        elif volume > 800: target_lip = "U"
        elif volume > 400: target_lip = "C"
        elif volume > 150: target_lip = "M"
        elif volume > 50: target_lip = "E"
        self.ui.set_lips_realtime(target_lip)

    def set_state(self, state):
        if self.state != state:
            self.state = state

    def play(self):
        while not getattr(self.ui, 'is_ui_ready', False):
            time.sleep(0.1)
        self.ui.idle()
        if not self.is_profile_loaded:
            self.ui.update_status("CARICA UN PROFILO...", "#95a5a6")
            self.ui.log_message("system", "waiting for profile...")
            
        while not self.do_quit:
            loop_start_time = time.time()
            if not self.is_profile_loaded:
                time.sleep(0.1)
                continue
                
            skip_sleep = False
            mic_chunk = self.mic.get_chunk()
            
            if len(mic_chunk) > 0 and not self.mic.is_muted():
                try:
                    audio_data = np.frombuffer(mic_chunk, dtype=np.int16)
                    volume = np.abs(audio_data).mean()
                    self.ui.update_audio_level(min(volume / 2000.0, 1.0))
                except Exception: pass
            else:
                self.ui.update_audio_level(0)
                
            if (len(mic_chunk) >= self.mic.buffer_size * 2) and not self.mic.is_muted():  
                if max(mic_chunk) == 0:
                    pass
                elif not (mic_chunk == self.mic_last_chunk):
                    if self.state == State.IDLE:
                        self.set_state(State.LISTEN)
                        self.ui.listen()
                    self.mic_last_chunk = mic_chunk 
                    self.mic.vad_time = self.vad.no_voice_wait_sec - self.vad.no_voice_sec
                    chunk_time = self.mic_params.get("buffer_size") / self.mic_params.get("samplerate")
                    
                    vad_status = self.vad.check(
                        np.frombuffer(mic_chunk, np.int16).flatten().astype(np.float32, order="C") / 32768.0,
                        chunk_time,
                    )
                    
                    if vad_status is None:
                        self.mic.reset_recording()
                        skip_sleep = True
                    elif vad_status == "vad_end":
                        self.set_state(State.TALK)
                        self.ui.update_audio_level(0)
                        self.ui.update_status("🟡 ELABORAZIONE...", "#f1c40f")
                        self.mic.stop_mic()
                        
                        mic_recording = self.mic.get_recording()
                        trim_bytes = int(self.vad.no_voice_wait_sec * self.mic.samplerate * 2)
                        if len(mic_recording) > trim_bytes:
                            mic_recording = mic_recording[:-trim_bytes]
                        
                        audio_data = np.frombuffer(mic_recording, dtype=np.int16)
                        
                        if len(audio_data) > self.mic.samplerate * 0.5:
                            import io
                            import scipy.io.wavfile as wavfile
                            audio_buffer = io.BytesIO()
                            wavfile.write(audio_buffer, self.mic.samplerate, audio_data)
                            audio_bytes = audio_buffer.getvalue()
                            
                            turn_reminder = " [SYSTEM DIRECTIVE: Answer strictly in English!]" if getattr(self.stt, 'language', 'it') == "en" else " [SYSTEM DIRECTIVE: Rispondi in Italiano!]"
                            self.llm.get_answer(self.ap, self.tts, audio_bytes, turn_reminder, self.on_answer, self.on_transcript, gender=self.current_gender)
                        else:
                            print(f"[ADAM] Audio scartato: durata {len(audio_data)/self.mic.samplerate:.2f}s, volume {volume_norm:.1f}")
                                    
                        self.set_state(State.LISTEN)
                        self.ui.listen()
                        self.ui.update_status("⚪ PRONTO (Parla pure...)", "#2ecc71")
                        self.mic.unmute()
                        skip_sleep = True
                        
            elif self.mic.is_muted() and self.state != State.IDLE:
                self.set_state(State.IDLE)
                self.ui.idle()
                
            if not skip_sleep:
                elapsed = time.time() - loop_start_time
                target_sleep = self.mic.buffer_size / self.mic.samplerate
                sleep_time = max(0, target_sleep - elapsed)
                time.sleep(sleep_time)