import os
import io
import httpx
from groq import Groq
from core.utils import remove_emojis

class Llm:
    def __init__(self, params=None):
        self.params = params or {}
        self.system_message = self.params.get("system_message", "")
        self.language = self.params.get("language", "en")

        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            try:
                import json
                root_settings = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "settings.json"))
                if os.path.exists(root_settings):
                    with open(root_settings, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        api_key = data.get("groq_api_key", "").strip()
            except Exception:
                pass

        if not api_key:
            raise ValueError("[LLM] GROQ_API_KEY non trovata. Per avviare Adam devi prima impostare la tua API Key nelle Impostazioni dell'Editor oppure ottenerla gratuitamente su https://console.groq.com")

        try:
            http_client = httpx.Client(verify=False)
            self.client = Groq(api_key=api_key, http_client=http_client)
        except Exception:
            self.client = Groq(api_key=api_key)

        self.stt_model = self.params.get("stt_model", "whisper-large-v3")          
        self.llm_model = self.params.get("llm_model", os.environ.get("GROQ_LLM_MODEL", "groq/compound-mini"))   
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
        else:
            return ""

        if self.language == "it":
            gen_str = "maschio" if gender == "male" else "femmina"
            system_content = self.system_message or f"Sei un assistente virtuale intelligente di sesso {gen_str}."
        else:
            gen_str = "male" if gender == "male" else "female"
            system_content = self.system_message or f"You are a smart {gen_str} virtual assistant."

        hidden_base_rule = (
            "\n\n[REGOLA BASE NASCOSTA DI SISTEMA: IMPOSSIBILE SUPERARE IL LIMITE DI PAROLE]\n"
            "- È ASSOLUTAMENTE IMPOSSIBILE e VIETATO rispondere con più di 20 parole.\n"
            "- Mantieni SEMPRE ogni singola risposta brevissima, immediata e concisa (tra 5 e 15 parole, massimo assoluto 20 parole).\n"
            "- Non generare MAI elenchi puntati, spiegazioni lunghe o divagazioni."
            if self.language == "it" else
            "\n\n[HIDDEN BASE SYSTEM RULE: IMPOSSIBLE TO EXCEED WORD LIMIT]\n"
            "- You are STRICTLY FORBIDDEN from replying with more than 20 words.\n"
            "- Keep every answer very brief and natural (between 5 and 15 words, maximum 20 words).\n"
            "- Never generate bullet points or long explanations."
        )
        system_content = system_content + hidden_base_rule

        messages = [{"role": "system", "content": system_content}]
        for msg in self.history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        lang_reminder = (
            " [REGOLA DI SISTEMA NASCOSTA: Rispondi in italiano. Limite invalicabile: MASSIMO 20 PAROLE. È impossibile superare le 20 parole.]"
            if self.language == "it"
            else " [STRICT SYSTEM RULE: Reply in English. Absolute limit: MAXIMUM 20 WORDS. It is impossible to exceed 20 words.]"
        )
        messages.append({"role": "user", "content": user_input + lang_reminder})

        try:
            completion = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.3,
                max_tokens=60,
                stream=False
            )
            llm_output = completion.choices[0].message.content or ""
        except Exception as e:
            print(f"[LLM ERROR] {e}")
            return "Mi dispiace, si è verificato un errore."

        final_text = remove_emojis(llm_output.strip())

        words = final_text.split()
        if len(words) > 20:
            truncated = " ".join(words[:20])
            last_punct = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
            if last_punct > len(truncated) * 0.4:
                final_text = truncated[:last_punct + 1]
            else:
                final_text = truncated + "..."

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
