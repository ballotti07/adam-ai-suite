from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import tkinter as tk
from PIL import Image, ImageTk

from src.utils.config import TARGET_COORDS, PREVIEW_DIM
from src.core.assets_manager import get_disk_category

@lru_cache(maxsize=128)
def generate_thumb_pil(base_dir: Path, cat: str, item_name: Optional[str]) -> Image.Image:
    thumb_size = (100, 100)
    target_obj_size = 85
    bg = Image.new("RGBA", thumb_size, (255, 255, 255, 0))

    if not item_name:
        return bg

    try:
        shape_path = base_dir / get_disk_category(cat) / item_name
        target_dir = shape_path

        preferred_colors = {"occhiali": "black", "eyes": "brown"}
        if cat in preferred_colors:
            pref = shape_path / preferred_colors[cat]
            if pref.exists():
                target_dir = pref
            else:
                subs = sorted([d for d in shape_path.iterdir() if d.is_dir()])
                if subs: target_dir = subs[0]
        else:
            if not list(shape_path.glob("*.png")):
                subs = sorted([d for d in shape_path.iterdir() if d.is_dir()])
                if subs: target_dir = subs[0]

        candidates = list(target_dir.glob("*.png"))
        best_img = None
        if candidates:
            for f in candidates:
                name = f.name.lower()
                if "mid" in name or "a_e_i" in name:
                    best_img = f
                    break
            if not best_img:
                best_img = candidates[0]

        if best_img:
            with Image.open(best_img) as im:
                img = im.convert("RGBA")

                if cat == "nose":
                    w_orig, h_orig = img.size
                    safe = 300
                    left = max(0, (w_orig - safe) // 2)
                    top = max(0, (h_orig - safe) // 2)
                    right = min(w_orig, (w_orig + safe) // 2)
                    bottom = min(h_orig, (h_orig + safe) // 2)

                    if right > left and bottom > top:
                        img = img.crop((left, top, right, bottom))

                alpha = img.getchannel("A")
                bbox = alpha.point(lambda p: 255 if p > 50 else 0).getbbox()
                if bbox:
                    margin = 5
                    img = img.crop((
                        max(0, bbox[0] - margin),
                        max(0, bbox[1] - margin),
                        min(img.width, bbox[2] + margin),
                        min(img.height, bbox[3] + margin)
                    ))

                img.thumbnail((target_obj_size, target_obj_size), Image.Resampling.LANCZOS)
                x = (thumb_size[0] - img.width) // 2
                y = (thumb_size[1] - img.height) // 2
                bg.paste(img, (x, y), img)

    except Exception as e:
        logging.error(f"[Thumb Error] {item_name}: {e}")

    return bg

def pil_to_photo(pil_img: Image.Image) -> ImageTk.PhotoImage:
    return ImageTk.PhotoImage(pil_img)

class PreviewRenderer:
    def __init__(self, canvas: tk.Canvas, base_dir: Path) -> None:
        self.canvas = canvas
        self.base_dir = base_dir
        self._tk_image_ref: Optional[ImageTk.PhotoImage] = None
        self._canvas_item_id: Optional[int] = None

        self._last_draw_order: Optional[List[str]] = None
        self._last_layer_keys: Optional[List[Tuple[str, Optional[str]]]] = None
        self._prefix_cache: List[Image.Image] = []
        self._last_composed_raw: Optional[Image.Image] = None

        self._canvas_w = PREVIEW_DIM[0]
        self._canvas_h = PREVIEW_DIM[1]

    @staticmethod
    @lru_cache(maxsize=512)
    def _load_rgba(path_str: str) -> Optional[Image.Image]:
        p = Path(path_str)
        if not p.exists():
            return None
        try:
            with Image.open(p) as im:
                return im.convert("RGBA")
        except Exception:
            return None

    @staticmethod
    @lru_cache(maxsize=256)
    def _load_prepared(path_str: str, size: Tuple[int, int]) -> Optional[Image.Image]:
        img = PreviewRenderer._load_rgba(path_str)
        if img is None:
            return None
        if img.size != size:
            return img.resize(size, Image.Resampling.LANCZOS)
        return img

    @staticmethod
    def clear_caches() -> None:
        PreviewRenderer._load_rgba.cache_clear()
        PreviewRenderer._load_prepared.cache_clear()

    def _resolve_final_path(self, cat: str, item: str, color: Optional[str], target_filename: str) -> Optional[Path]:
        shape_path = self.base_dir / get_disk_category(cat) / item
        final_path = None

        if color and color != "default":
            color_dir = shape_path / color
            if color_dir.exists():
                if (color_dir / target_filename).exists():
                    final_path = color_dir / target_filename
                elif (color_dir / "mid.png").exists():
                    final_path = color_dir / "mid.png"
                else:
                    pngs = list(color_dir.glob("*.png"))
                    if pngs: final_path = pngs[0]

        if not final_path:
            if (shape_path / target_filename).exists():
                final_path = shape_path / target_filename
            elif (shape_path / "mid.png").exists():
                final_path = shape_path / "mid.png"
            else:
                pngs = list(shape_path.glob("*.png"))
                if pngs: final_path = pngs[0]

        return final_path

    def _compute_draw_order(self, current_avatar: Dict) -> List[str]:
        order = ["base", "eyes", "eyebrows", "nose", "lips", "occhiali", "hair"]
        hair_item = current_avatar.get("hair", {}).get("item")
        if hair_item and str(hair_item).startswith("corti"):
            order = ["base", "eyes", "eyebrows", "nose", "lips", "hair", "occhiali"]
        return order

    def _compose_image(self, current_avatar: Dict, file_overrides: Dict = None) -> Image.Image:
        overrides = file_overrides or {}
        draw_order = self._compute_draw_order(current_avatar)
        blank = Image.new("RGBA", PREVIEW_DIM, (0, 0, 0, 0))

        layer_keys: List[Tuple[str, Optional[str]]] = []
        layer_imgs: List[Optional[Image.Image]] = []

        for cat in draw_order:
            data = current_avatar.get(cat, {})
            item = data.get("item")
            color = data.get("color")

            if not item:
                layer_keys.append((cat, None))
                layer_imgs.append(None)
                continue

            target_filename = overrides.get(cat, "mid.png")
            if cat == "lips" and cat not in overrides:
                target_filename = "A_E_I.png"

            final_path = self._resolve_final_path(cat, item, color, target_filename)

            if not final_path:
                layer_keys.append((cat, None))
                layer_imgs.append(None)
                continue

            conf = TARGET_COORDS.get(cat)
            size = conf.resize_to if conf else PREVIEW_DIM
            img = self._load_prepared(str(final_path), size)

            layer_keys.append((cat, str(final_path)))
            layer_imgs.append(img)

        can_reuse = (
            self._last_draw_order == draw_order and
            self._last_layer_keys is not None and
            bool(self._prefix_cache)
        )

        start_idx = 0
        if can_reuse:
            for i, key in enumerate(layer_keys):
                if i >= len(self._last_layer_keys) or key != self._last_layer_keys[i]:
                    start_idx = i
                    break
            else:
                if self._last_composed_raw:
                    return self._last_composed_raw
                start_idx = 0

        if can_reuse and start_idx < len(self._prefix_cache):
            new_prefix_cache = self._prefix_cache[:start_idx + 1]
            base_img = new_prefix_cache[start_idx].copy()
        else:
            new_prefix_cache = [blank]
            base_img = blank.copy()
            start_idx = 0

        for i in range(start_idx, len(layer_imgs)):
            li = layer_imgs[i]
            if li:
                if li.size == base_img.size:
                    base_img.alpha_composite(li)
                else:
                    base_img.paste(li, (0, 0), li)
            new_prefix_cache.append(base_img.copy())

        self._last_draw_order = draw_order
        self._last_layer_keys = layer_keys
        self._prefix_cache = new_prefix_cache
        self._last_composed_raw = new_prefix_cache[-1]

        return self._last_composed_raw

    def set_canvas_size(self, w: int, h: int) -> None:
        if w > 1 and h > 1:
            self._canvas_w = w
            self._canvas_h = h
            if self._last_composed_raw:
                self._draw_to_canvas()

    def _draw_to_canvas(self) -> None:
        if not self._last_composed_raw:
            return

        img_w, img_h = self._last_composed_raw.size
        ratio = min(self._canvas_w / img_w, self._canvas_h / img_h)

        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)

        resized = self._last_composed_raw.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self._tk_image_ref = ImageTk.PhotoImage(resized)

        x_center = self._canvas_w // 2
        y_center = self._canvas_h // 2

        if self._canvas_item_id is None:
            self.canvas.delete("all")
            self._canvas_item_id = self.canvas.create_image(
                x_center, y_center,
                image=self._tk_image_ref,
                anchor="center"
            )
        else:
            self.canvas.coords(self._canvas_item_id, x_center, y_center)
            self.canvas.itemconfig(self._canvas_item_id, image=self._tk_image_ref)

    def render(self, current_avatar: Dict, file_overrides: Dict = None) -> None:
        self._compose_image(current_avatar, file_overrides)
        self._draw_to_canvas()

    def export_image(self, current_avatar: Dict, filepath: str) -> bool:
        try:
            pil_img = self._compose_image(current_avatar, file_overrides=None)
            pil_img.save(filepath, "PNG")
            return True
        except Exception as e:
            logging.error(f"[Export Error]: {e}")
            return False