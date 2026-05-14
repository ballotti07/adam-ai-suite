from __future__ import annotations
from typing import Iterable, List

COLOR_MAP: dict[str, str] = {
    "default": "#95a5a6", "skin_1": "#F5D9CE", "skin_2": "#d4af91", 
    "skin_3": "#2F1203", "black": "#2c3e50", "blonde": "#f1c40f",
    "brown": "#795548", "green": "#2ecc71", "cyan": "#00bcd4",
    "beige": "#f5f5dc", "blue": "#252850", "orange": "#FF8000",
    "pink": "#ff9ff3", "red": "#e74c3c",
}

DEFAULT_HEX_FALLBACK = "#95a5a6"

DEFAULT_COLOR_PREFERENCES: dict[str, List[str]] = {
    "eyes": ["brown"], "occhiali": ["black"], "accessories": ["black"],
}

def color_to_hex(color_name: str | None, fallback: str = DEFAULT_HEX_FALLBACK) -> str:
    if not color_name: return fallback
    return COLOR_MAP.get(color_name.lower(), fallback)

def pick_default_color(cat_key: str, available_colors: Iterable[str]) -> str:
    available = list(available_colors)
    if not available: return "default"
    
    for pref in DEFAULT_COLOR_PREFERENCES.get(cat_key, []):
        if pref in available:
            return pref
    return available[0]