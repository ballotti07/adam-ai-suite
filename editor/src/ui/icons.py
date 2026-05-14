from PIL import Image, ImageTk, ImageDraw
from src.ui.theme import C_SIDEBAR

def _scale(val: float, size: int) -> int:
    return int(val * size / 100)

def generate_solid_icon(category: str, size: int = 128) -> ImageTk.PhotoImage:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    col = "#ffffff"
    s = lambda v: _scale(v, size)

    if category == "base":
        draw.ellipse([s(25), s(5), s(75), s(55)], fill=col)
        draw.chord([s(10), s(60), s(90), s(140)], 0, 180, fill=col)
    elif category == "eyes":
        draw.pieslice([s(5), s(30), s(95), s(70)], 0, 360, fill=col)
        draw.ellipse([s(35), s(35), s(65), s(65)], fill=C_SIDEBAR)
    elif category == "eyebrows":
        coords = [
            (s(10), s(60)), (s(30), s(45)), (s(70), s(45)), (s(90), s(60)),
            (s(90), s(75)), (s(70), s(60)), (s(30), s(60)), (s(10), s(75)),
        ]
        draw.polygon(coords, fill=col)
    elif category == "nose":
        draw.polygon([
            (s(40), s(20)), (s(60), s(20)),
            (s(60), s(70)), (s(80), s(70)),
            (s(80), s(85)), (s(40), s(85)),
        ], fill=col)
    elif category == "lips":
        draw.ellipse([s(10), s(35), s(90), s(65)], fill=col)
        draw.line([s(15), s(50), s(85), s(50)], fill=C_SIDEBAR, width=s(5))
    elif category == "hair":
        draw.chord([s(15), s(15), s(85), s(85)], 180, 0, fill=col)
        draw.rectangle([s(15), s(50), s(85), s(80)], fill=col)
        draw.ellipse([s(30), s(40), s(70), s(80)], fill=C_SIDEBAR)
    elif category == "occhiali":
        draw.rounded_rectangle([s(5), s(35), s(95), s(65)], radius=s(5), fill=col)
        draw.rectangle([s(10), s(40), s(45), s(60)], fill=C_SIDEBAR)
        draw.rectangle([s(55), s(40), s(90), s(60)], fill=C_SIDEBAR)
    else:
        draw.ellipse([s(20), s(20), s(80), s(80)], fill=col)

    return ImageTk.PhotoImage(img.resize((30, 30), Image.Resampling.LANCZOS))