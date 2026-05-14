from __future__ import annotations
import json
import random
import re
import sys
import shutil
import os
from pathlib import Path
from typing import Dict, Optional, List, Set, Any

from src.utils.constants import LAYER_ORDER, Cat
from src.utils.colors import pick_default_color

_SPLIT_REGEX = re.compile(r"(\d+)")

def natural_keys(text: str) -> List[Any]:
    return [int(c) if c.isdigit() else c.lower() for c in _SPLIT_REGEX.split(text)]

def get_disk_category(cat: str) -> str:
    return "glasses" if cat == "occhiali" else cat

def resolve_assets_dir(base_path: str | Path) -> Path:
    p = Path(base_path)
    if p.is_absolute(): return p

    candidates = [
        (Path.cwd() / p).resolve(),
        (Path(__file__).parent / p).resolve(),
        (Path(sys.argv[0]).parent / p).resolve()
    ]

    def _score(path: Path) -> int:
        if not path.exists(): return 0
        return 2 if (path / "glasses").exists() else 1

    return max(candidates, key=_score)

class AssetManager:
    def __init__(self, base_dir: str = "assets") -> None:
        self.base_dir = resolve_assets_dir(base_dir)
        self.gender = "male"
        self.language = "it"
        self.keys = [c.value if isinstance(c, Cat) else c for c in LAYER_ORDER]
        
        self.assets: Dict[str, List[str]] = {k: [] for k in self.keys}
        self.colors_cache: Dict[str, List[str]] = {}
        self.current_avatar: Dict[str, Dict[str, Any]] = {
            k: {"item": None, "color": "default", "dx": 0, "dy": 0} for k in self.keys
        }

        self._init_folders()
        self.scan()

        if self.assets.get("base"):
            self.set_smart_item("base", self.assets["base"][0])

    def _init_folders(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for cat in self.keys:
            (self.base_dir / get_disk_category(cat)).mkdir(exist_ok=True)
        (self.base_dir / "hair" / "corti").mkdir(exist_ok=True)
        (self.base_dir / "hair" / "lunghi").mkdir(exist_ok=True)

    @property
    def current_assets_path(self) -> Path:
        return self.base_dir

    def scan(self) -> None:
        self.assets = {k: [] for k in self.keys}
        self.colors_cache.clear()

        for cat in self.keys:
            cat_path = self.base_dir / get_disk_category(cat)
            if not cat_path.exists(): continue

            if cat == "hair":
                for sub in ["corti", "lunghi"]:
                    sub_path = cat_path / sub
                    if not sub_path.exists(): continue
                    items = sorted([d.name for d in sub_path.iterdir() if d.is_dir()], key=natural_keys)
                    for item in items:
                        full_id = f"{sub}/{item}"
                        self.assets[cat].append(full_id)
                        self._cache_colors(sub_path / item, cat, full_id)
            else:
                items = sorted([d.name for d in cat_path.iterdir() if d.is_dir()], key=natural_keys)
                self.assets[cat] = items
                for item in items:
                    self._cache_colors(cat_path / item, cat, item)

    def _cache_colors(self, path: Path, cat: str, item_id: str) -> None:
        colors = sorted([d.name for d in path.iterdir() if d.is_dir()], key=natural_keys)
        if not colors and list(path.glob("*.png")):
            colors = ["default"]
        self.colors_cache[f"{cat}/{item_id}"] = colors

    def get_colors_for_shape(self, cat: str, shape: str | None) -> List[str]:
        if not shape: return []
        cat_key = cat.value if hasattr(cat, "value") else cat
        return self.colors_cache.get(f"{cat_key}/{shape}", [])

    def set_smart_item(self, cat: str, item_name: Optional[str]) -> None:
        cat_key = cat.value if hasattr(cat, "value") else cat
        self.current_avatar[cat_key]["item"] = item_name

        if item_name:
            avail = self.get_colors_for_shape(cat_key, item_name)
            if avail and self.current_avatar[cat_key].get("color") not in avail:
                self.current_avatar[cat_key]["color"] = pick_default_color(cat_key, avail)

    def set_color(self, cat: str, color_name: str) -> None:
        cat_key = cat.value if hasattr(cat, "value") else cat
        self.current_avatar[cat_key]["color"] = color_name

    def reset_all(self) -> None:
        for k in self.keys:
            self.current_avatar[k] = {"item": None, "color": "default", "dx": 0, "dy": 0}
        if self.assets.get("base"):
            self.set_smart_item("base", self.assets["base"][0])

    def randomize(self, optional_cats: Set[str] | None = None) -> None:
        target_color = None
        base_val = Cat.BASE.value

        for cat in sorted(self.keys, key=lambda k: 0 if k == base_val else 1):
            shapes = self.assets.get(cat, [])
            if not shapes: continue

            cat_val = cat.value if hasattr(cat, "value") else cat
            if cat_val == "occhiali" and random.random() > 0.5:
                self.set_smart_item(cat, None)
                continue
                
            chosen_shape = random.choice(shapes)
            self.set_smart_item(cat, chosen_shape)
            avail_colors = self.get_colors_for_shape(cat, chosen_shape)

            if avail_colors:
                if cat_val == base_val:
                    selected_color = random.choice(avail_colors)
                    target_color = selected_color
                else:
                    selected_color = target_color if target_color in avail_colors else random.choice(avail_colors)
                self.set_color(cat, selected_color)

    def save(self, json_filepath: Path | str, language: str = "it", gender: str = "male",
             voice_mode: str = "predefined", temp_recording_path: str = None, 
             dest_wav_path: str = None, voice_ref_text: str = None) -> bool:
        self.gender = gender
        self.language = language
        
        data = {
            "language": language,
            "gender": gender,
            "avatar": self.current_avatar,
            "voice_mode": voice_mode,
            "voice_cloning": (voice_mode == "cloned")
        }

        if voice_mode == "cloned":
            if temp_recording_path and dest_wav_path and os.path.exists(temp_recording_path):
                try:
                    shutil.copy(temp_recording_path, dest_wav_path)
                    json_dir = Path(json_filepath).parent
                    wav_path_obj = Path(dest_wav_path)
                    
                    try:
                        data["voice_ref_path"] = str(wav_path_obj.relative_to(json_dir))
                    except ValueError:
                        data["voice_ref_path"] = str(wav_path_obj)
                        
                    data["voice_ref_text"] = voice_ref_text or ""
                except Exception:
                    pass

        try:
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except IOError:
            return False

    def load_profile(self, filepath: Path | str) -> bool:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            loaded = data.get("avatar", data)
            self.gender = data.get("gender", self.gender)
            self.language = data.get("language", self.language)

            if not loaded: return False

            for k in self.keys:
                src_key = "accessories" if k == "occhiali" and "accessories" in loaded and "occhiali" not in loaded else k
                if src_key in loaded and isinstance(loaded[src_key], dict):
                    self.current_avatar[k]["item"] = loaded[src_key].get("item")
                    self.current_avatar[k]["color"] = loaded[src_key].get("color", "default")
                else:
                    self.current_avatar[k].update({"item": None, "color": "default"})
            return True
        except (IOError, json.JSONDecodeError):
            return False