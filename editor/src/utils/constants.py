from enum import Enum

class Cat(str, Enum):
    BASE = "base"
    HAIR = "hair"
    EYES = "eyes"
    EYEBROWS = "eyebrows"
    NOSE = "nose"
    LIPS = "lips"
    OCCHIALI = "occhiali"

LAYER_ORDER = [
    Cat.BASE, Cat.EYES, Cat.EYEBROWS, 
    Cat.NOSE, Cat.LIPS, Cat.OCCHIALI, Cat.HAIR
]

OPTIONAL_CATS = {Cat.OCCHIALI, Cat.NOSE, Cat.EYEBROWS, Cat.LIPS, Cat.HAIR}