"""Image processing helpers.

Keeps all Pillow logic (fitting images into fixed-size boxes without
stretching) and the PIL <-> Qt conversion helpers in one place.
"""
from __future__ import annotations

import io
from typing import Tuple

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QPixmap

_COLOR_MAP = {
    "white": (255, 255, 255, 255),
    "black": (0, 0, 0, 255),
    "transparent": (0, 0, 0, 0),
}


def resolve_padding_color(name: str) -> Tuple[int, int, int, int]:
    return _COLOR_MAP.get(name, (255, 255, 255, 255))


def fit_image_to_box(
    pil_img: Image.Image,
    box_w: int,
    box_h: int,
    padding_color: str = "white",
    align: str = "center",
) -> Image.Image:
    """Resize `pil_img` to fit within (box_w, box_h) preserving aspect ratio,
    then pad with `padding_color` to exactly fill the box (never stretches).

    align: "center" (both axes centered) or "top" (horizontally centered,
    vertically pinned to the top of the box).
    """
    box_w = max(1, int(box_w))
    box_h = max(1, int(box_h))

    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")

    img_w, img_h = pil_img.size
    if img_w == 0 or img_h == 0:
        img_w, img_h = 1, 1

    scale = min(box_w / img_w, box_h / img_h)
    new_w = max(1, round(img_w * scale))
    new_h = max(1, round(img_h * scale))

    resample = Image.LANCZOS if scale < 1 else Image.BICUBIC
    resized = pil_img.resize((new_w, new_h), resample)

    bg_rgba = resolve_padding_color(padding_color)
    canvas = Image.new("RGBA", (box_w, box_h), bg_rgba)

    x = (box_w - new_w) // 2
    y = (box_h - new_h) // 2 if align == "center" else 0

    canvas.paste(resized, (x, y), resized)
    return canvas


def make_thumbnail(pil_img: Image.Image, max_size: int = 512) -> Image.Image:
    """Downscale a large image for fast preview rendering (lazy-load helper)."""
    img = pil_img.copy()
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    return img.convert("RGBA")


def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
    # QImage does not own `data`'s lifetime by default in some bindings; copy() forces
    # PySide6 to take ownership of its own buffer so the Python bytes can be freed.
    return QPixmap.fromImage(qimg.copy())


def qimage_to_pil(qimage: QImage) -> Image.Image:
    buffer = QBuffer()
    buffer.open(QIODevice.ReadWrite)
    qimage.save(buffer, "PNG")
    pil_img = Image.open(io.BytesIO(bytes(buffer.data())))
    pil_img.load()
    return pil_img.convert("RGBA")


def qpixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    return qimage_to_pil(pixmap.toImage())
