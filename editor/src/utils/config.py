from dataclasses import dataclass
from typing import Tuple, Dict

APP_NAME = "ADAM CREATOR PRO - Unified Canvas"
WINDOW_SIZE = "1400x900"
PREVIEW_DIM = (512, 512)

@dataclass(frozen=True)
class TargetConfig:
    resize_to: Tuple[int, int]

_DEFAULT = TargetConfig(resize_to=PREVIEW_DIM)

TARGET_COORDS: Dict[str, TargetConfig] = {
    "base": _DEFAULT, "hair": _DEFAULT, "eyebrows": _DEFAULT,
    "eyes": _DEFAULT, "nose": _DEFAULT, "lips": _DEFAULT,
    "occhiali": _DEFAULT, "accessories": _DEFAULT, 
}