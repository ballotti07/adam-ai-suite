import os
import io
from groq import Groq
from core.utils import remove_emojis


class Llm:
    def __init__(self, params=None):
        self.params = params or {}
        self.system_message = self.params.get("system_message", "")
        self.language = self.params.get("language", "en")

        api_key = os.environ.get("GROQ_API_KEY", "")  #API_KEY
        if not api_key:
            raise ValueError("[LLM] GROQ_API_KEY non trovata. Ottienila gratis su https://console.groq.com")

        self.client = Groq(api_key=api_key)
        self.stt_model = "whisper-large-v3"          
        self.llm_model = "llama-3.3-70b-versatile"   
        self.reset_chat()

    def reset_chat(self):
        self.history = []

    def get_answer(self, ap, tts, audio_bytes, reminder, on_answer_callback=None, on_transcript_callback=None, user_text=None, gender="male"):

        actual_transcript = ""
        if audio_bytes:
            try:
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = "audio.wav"
                transcription = self.client.audio.transcriptions.create(
                    model=self.stt_model,
                    file=audio_file,
                    language=self.language if self.language in ["it", "en"] else None,
                    response_format="text"
                )
                actual_transcript = transcription.strip() if transcription else ""
                print(f"[STT] Trascritto: {actual_transcript}")
                if on_transcript_callback and actual_transcript:
                    on_transcript_callback(actual_transcript)
            except Exception as e:
                print(f"[STT ERROR] {e}")
                actual_transcript = ""

            if not actual_transcript:
                return ""

            user_input = actual_transcript
        elif user_text:
            user_input = user_text
            self.history.append({"role": "user", "content": user_text})
        else:
            return ""

        if self.language == "it":
            gen_str = "maschio" if gender == "male" else "femmina"
            system_content = self.system_message or f"Sei un assistente virtuale intelligente di sesso {gen_str}. Rispondi in modo naturale e conciso (max 20 parole)."
        else:
            gen_str = "male" if gender == "male" else "female"
            system_content = self.system_message or f"You are a smart {gen_str} virtual assistant. Answer naturally and concisely (max 20 words)."

        messages = [{"role": "system", "content": system_content}]
        for msg in self.history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        lang_reminder = " [Rispondi SEMPRE in italiano, max 20 parole.]" if self.language == "it" else " [Always reply in English, max 20 words.]"
        messages.append({"role": "user", "content": user_input + lang_reminder})

        try:
            # Disabilitiamo lo streaming per attendere la risposta completa
            completion = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.3,
                max_tokens=150,
                stream=False
            )
            llm_output = completion.choices[0].message.content or ""
        except Exception as e:
            print(f"[LLM ERROR] {e}")
            return "Mi dispiace, si è verificato un errore."

        final_text = remove_emojis(llm_output.strip())
        
        if final_text:
            if tts is not None:
                def full_callback(text, duration):
                    if on_answer_callback:
                        on_answer_callback(text, duration, log_to_chat=True)
                
                tts.run_tts_sync(final_text, full_callback)

        if ap is not None:
            ap.check_audio_finished()

        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": llm_output.strip()})
        if len(self.history) > 10: self.history = self.history[-10:]

        return llm_output.strip()
