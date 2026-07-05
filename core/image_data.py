"""Data model representing a single image placed in a grid cell."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image


@dataclass
class ImageItem:
    """Holds everything needed to display and export one image in the grid.

    The full-resolution image is kept lazily: if `path` is set, the original
    file is only re-opened from disk when we need full quality (zoom /
    export). For in-memory images (e.g. pasted from clipboard) we keep a
    PIL.Image directly in `pil_image`.
    """

    path: Optional[str] = None
    pil_image: Optional[Image.Image] = None
    label: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    # Per-cell view controls (zoom/pan within the cell preview only; does not
    # affect exported composition, which always fits the image to the cell).
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def display_name(self) -> str:
        if self.label:
            return self.label
        if self.path:
            import os

            return os.path.basename(self.path)
        return "Untitled"

    def load_full_image(self) -> Image.Image:
        """Return a full-resolution PIL image (RGBA), loading from disk if needed."""
        if self.path:
            img = Image.open(self.path)
            img.load()
            return img.convert("RGBA")
        if self.pil_image is not None:
            return self.pil_image.convert("RGBA")
        raise ValueError("ImageItem has neither path nor pil_image set")

    def clone(self) -> "ImageItem":
        return ImageItem(
            path=self.path,
            pil_image=self.pil_image,
            label=self.label,
            zoom=self.zoom,
            pan_x=self.pan_x,
            pan_y=self.pan_y,
        )
