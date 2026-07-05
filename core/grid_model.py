"""The single source of truth for grid contents and layout settings.

GridWidget (UI) observes `changed` to repaint; all mutations that should be
undoable go through core.commands and call the `_silent` methods here so
undo/redo doesn't recursively push new commands.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from core.image_data import ImageItem
from core.settings import GridSettings


class GridModel(QObject):
    changed = Signal()          # any redraw-worthy change
    grid_resized = Signal()     # rows/cols changed (layout must rebuild widgets)

    def __init__(self):
        super().__init__()
        self.settings = GridSettings()
        self.items: List[Optional[ImageItem]] = [None] * (self.settings.rows * self.settings.cols)

    # -- basic queries -----------------------------------------------------
    def cell_count(self) -> int:
        return self.settings.rows * self.settings.cols

    def first_empty_index(self) -> Optional[int]:
        for i, item in enumerate(self.items):
            if item is None:
                return i
        return None

    def filled_count(self) -> int:
        return sum(1 for i in self.items if i is not None)

    # -- silent mutators (called by QUndoCommand redo/undo) -----------------
    def set_item_silent(self, index: int, item: Optional[ImageItem]):
        if 0 <= index < len(self.items):
            self.items[index] = item
            self.changed.emit()

    def swap_silent(self, a: int, b: int):
        if 0 <= a < len(self.items) and 0 <= b < len(self.items):
            self.items[a], self.items[b] = self.items[b], self.items[a]
            self.changed.emit()

    def apply_grid_size_silent(self, rows: int, cols: int, restore_items: Optional[List] = None):
        new_count = rows * cols
        if restore_items is not None:
            new_items = list(restore_items)[:new_count]
            new_items += [None] * (new_count - len(new_items))
        else:
            new_items = list(self.items)[:new_count]
            new_items += [None] * (new_count - len(new_items))
        self.settings.rows = rows
        self.settings.cols = cols
        self.items = new_items
        self.grid_resized.emit()
        self.changed.emit()

    def notify_changed(self):
        self.changed.emit()
