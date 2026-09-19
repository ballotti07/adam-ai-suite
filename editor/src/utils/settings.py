import os
import json

def get_root_dir() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(current_dir, "..", "..", ".."))

def get_settings_path() -> str:
    return os.path.join(get_root_dir(), "settings.json")

def load_settings() -> dict:
    p = get_settings_path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_settings(data: dict) -> bool:
    p = get_settings_path()
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception:
        return False

def get_groq_api_key() -> str:
    settings = load_settings()
    key = settings.get("groq_api_key", "").strip()
    if not key:
        key = os.environ.get("GROQ_API_KEY", "").strip()
    return key

def is_key_verified() -> bool:
    settings = load_settings()
    return bool(settings.get("groq_api_key_verified", False))

def set_key_verified(verified: bool = True) -> bool:
    settings = load_settings()
    settings["groq_api_key_verified"] = bool(verified)
    return save_settings(settings)

def set_groq_api_key(key: str, verified: bool = False) -> bool:
    settings = load_settings()
    key_clean = key.strip()
    prev_key = settings.get("groq_api_key", "").strip()
    settings["groq_api_key"] = key_clean
    if key_clean != prev_key:
        settings["groq_api_key_verified"] = verified
    elif verified:
        settings["groq_api_key_verified"] = True
    if key_clean:
        settings["onboarding_completed"] = True
    os.environ["GROQ_API_KEY"] = key_clean
    return save_settings(settings)

def is_onboarding_completed() -> bool:
    settings = load_settings()
    return bool(settings.get("onboarding_completed", False) and get_groq_api_key() and is_key_verified())

def verify_groq_api_key(api_key: str) -> tuple[bool, str]:
    k = (api_key or "").strip()
    if not k:
        return False, "Nessuna chiave inserita."
    if not k.startswith("gsk_"):
        return False, "Formato errato: la chiave Groq deve iniziare con 'gsk_'."
    if len(k) < 25:
        return False, "Chiave incompleta: assicurati di aver copiato l'intero codice."

    try:
        import httpx
        from groq import Groq, AuthenticationError, APIConnectionError
        http_client = httpx.Client(verify=False, timeout=6.0)
        client = Groq(api_key=k, timeout=6.0, http_client=http_client)
        client.models.list()
        return True, "Chiave valida e funzionante!"
    except AuthenticationError:
        return False, "Chiave non valida o revocata (Errore 401 Groq)."
    except APIConnectionError:
        return False, "Errore di connessione a Groq. Verifica la connessione Internet."
    except Exception as e:
        return False, f"Errore verifica: {str(e)[:80]}"

def get_language() -> str:
    settings = load_settings()
    return settings.get("language", "it")

def set_language_setting(lang_code: str) -> bool:
    settings = load_settings()
    settings["language"] = str(lang_code).lower()
    return save_settings(settings)
