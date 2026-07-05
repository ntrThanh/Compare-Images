"""Global settings that control how the grid is laid out and rendered."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GridSettings:
    rows: int = 2
    cols: int = 3

    cell_width: int = 260
    cell_height: int = 200

    spacing: int = 12
    margin: int = 24

    background_color: str = "#2b2b2b"   # canvas / app background
    padding_color: str = "white"        # "white" | "black" | "transparent"
    alignment: str = "center"           # "center" | "top"

    show_border: bool = True
    border_color: str = "#555555"
    show_shadow: bool = True

    show_labels: bool = True
    label_font_size: int = 13
    label_color: str = "#e0e0e0"

    export_scale: int = 1  # 1, 2, or 4
