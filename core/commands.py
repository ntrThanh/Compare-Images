"""QUndoCommand implementations for all grid-mutating actions.

Every action that changes which image sits in which cell (or a label's text)
goes through one of these commands so Ctrl+Z / Ctrl+Y behave consistently.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QUndoCommand

from core.image_data import ImageItem


class SetImageCommand(QUndoCommand):
    """Set/replace/clear the image at a single cell index."""

    def __init__(self, model, index: int, new_item: Optional[ImageItem], text: str = "Set Image"):
        super().__init__(text)
        self.model = model
        self.index = index
        self.new_item = new_item
        self.old_item = model.items[index]

    def redo(self):
        self.model.set_item_silent(self.index, self.new_item)

    def undo(self):
        self.model.set_item_silent(self.index, self.old_item)


class SwapImagesCommand(QUndoCommand):
    """Swap the images at two cell indices (used for drag-and-drop reorder)."""

    def __init__(self, model, index_a: int, index_b: int, text: str = "Reorder Images"):
        super().__init__(text)
        self.model = model
        self.index_a = index_a
        self.index_b = index_b

    def redo(self):
        self.model.swap_silent(self.index_a, self.index_b)

    def undo(self):
        self.model.swap_silent(self.index_a, self.index_b)


class SetLabelCommand(QUndoCommand):
    """Change the label text of the image at a cell index."""

    def __init__(self, model, index: int, new_label: str, text: str = "Edit Label"):
        super().__init__(text)
        self.model = model
        self.index = index
        self.new_label = new_label
        item = model.items[index]
        self.old_label = item.label if item else ""

    def redo(self):
        item = self.model.items[self.index]
        if item:
            item.label = self.new_label
            self.model.notify_changed()

    def undo(self):
        item = self.model.items[self.index]
        if item:
            item.label = self.old_label
            self.model.notify_changed()


class ResizeGridCommand(QUndoCommand):
    """Change the number of rows/cols, preserving existing images by index."""

    def __init__(self, model, new_rows: int, new_cols: int, text: str = "Resize Grid"):
        super().__init__(text)
        self.model = model
        self.new_rows = new_rows
        self.new_cols = new_cols
        self.old_rows = model.settings.rows
        self.old_cols = model.settings.cols
        self.old_items = list(model.items)

    def redo(self):
        self.model.apply_grid_size_silent(self.new_rows, self.new_cols)

    def undo(self):
        self.model.apply_grid_size_silent(self.old_rows, self.old_cols, restore_items=self.old_items)
