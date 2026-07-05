"""Renders the full comparison grid to a single PIL image at any scale.

This is used both for "Export PNG" and "Copy composed image to clipboard".
It re-reads full-resolution source images from disk (or the in-memory
PIL image for pasted content) so exports are never limited by the
on-screen thumbnail quality.
"""
from __future__ import annotations

from typing import Optional

from PIL import Image, ImageColor, ImageDraw, ImageFont

from core.image_processing import fit_image_to_box


def _hex_to_rgba(color: str, alpha: int = 255):
    try:
        r, g, b = ImageColor.getrgb(color)
        return (r, g, b, alpha)
    except ValueError:
        return (43, 43, 43, alpha)


def _load_font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_grid_to_image(model, scale: int = 1) -> Image.Image:
    """Compose the entire grid (all filled cells, empty ones left blank) into
    one PIL RGBA image, at the requested export scale (1x / 2x / 4x)."""
    s = model.settings
    cols, rows = s.cols, s.rows

    cell_w = int(s.cell_width * scale)
    cell_h = int(s.cell_height * scale)
    spacing = int(s.spacing * scale)
    margin = int(s.margin * scale)
    label_h = int((s.label_font_size + 14) * scale) if s.show_labels else 0
    border_w = max(1, int(2 * scale)) if s.show_border else 0
    shadow_offset = int(6 * scale)

    row_h = cell_h + label_h

    total_w = margin * 2 + cols * cell_w + (cols - 1) * spacing
    total_h = margin * 2 + rows * row_h + (rows - 1) * spacing

    bg_rgba = _hex_to_rgba(s.background_color)
    canvas = Image.new("RGBA", (max(1, total_w), max(1, total_h)), bg_rgba)
    draw = ImageDraw.Draw(canvas, "RGBA")

    font = _load_font(max(8, int(s.label_font_size * scale))) if s.show_labels else None

    for idx, item in enumerate(model.items):
        r, c = divmod(idx, cols)
        x = margin + c * (cell_w + spacing)
        y = margin + r * (row_h + spacing)

        if s.show_shadow and item is not None:
            shadow_box = [
                x + shadow_offset,
                y + shadow_offset,
                x + cell_w + shadow_offset,
                y + cell_h + shadow_offset,
            ]
            draw.rectangle(shadow_box, fill=(0, 0, 0, 90))

        if item is not None:
            try:
                src = item.load_full_image()
                fitted = fit_image_to_box(src, cell_w, cell_h, s.padding_color, s.alignment)
                canvas.paste(fitted, (x, y), fitted)
            except Exception:
                draw.rectangle([x, y, x + cell_w, y + cell_h], fill=(120, 40, 40, 255))

        if s.show_border:
            draw.rectangle(
                [x, y, x + cell_w - 1, y + cell_h - 1],
                outline=_hex_to_rgba(s.border_color),
                width=border_w,
            )

        if s.show_labels and item is not None and item.label:
            text = item.label
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
            except Exception:
                text_w = len(text) * int(s.label_font_size * scale * 0.6)
            tx = x + (cell_w - text_w) // 2
            ty = y + cell_h + int(4 * scale)
            draw.text((tx, ty), text, fill=_hex_to_rgba(s.label_color), font=font)

    return canvas


def save_png(model, path: str, scale: int = 1) -> None:
    img = render_grid_to_image(model, scale=scale)
    img.save(path, format="PNG")
