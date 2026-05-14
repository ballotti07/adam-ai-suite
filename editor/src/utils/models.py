from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class TargetConfig:
    resize_to: Tuple[int, int]