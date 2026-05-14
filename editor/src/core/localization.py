import json
from pathlib import Path
from typing import Dict

class LocalizationManager:
    def __init__(self, locale_file: str = "locales.json", default_lang: str = "it"):
        base_path = Path(__file__).parent.parent if "src" in Path(__file__).parts else Path.cwd()
        resolved_path = base_path / locale_file
        
        self.locale_file = str(resolved_path) if resolved_path.exists() else locale_file
        self.current_lang = default_lang
        self.data: Dict[str, Dict[str, str]] = {}
        self._load_data()

    def _load_data(self) -> None:
        try:
            with open(self.locale_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = {}

    def set_language(self, lang_code: str) -> None:
        if lang_code in self.data:
            self.current_lang = lang_code

    def get(self, key: str) -> str:
        return self.data.get(self.current_lang, {}).get(key, f"MISSING: {key}")

    def get_for_lang(self, lang_code: str, key: str) -> str:
        return self.data.get(lang_code, {}).get(key, f"MISSING: {key}")

LOCALE = LocalizationManager()