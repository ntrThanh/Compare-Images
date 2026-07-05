"""The scrollable grid of ImageCell widgets.

Owns the QUndoStack and is the only place that turns user gestures (drop,
replace, remove, reorder, label edit, resize) into QUndoCommands, so every
mutation is undoable.
"""
from __future__ import annotations

import os
from typing import List, Optional

from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QFileDialog, QGridLayout, QSizePolicy, QWidget

from core.commands import ResizeGridCommand, SetImageCommand, SetLabelCommand, SwapImagesCommand
from core.grid_model import GridModel
from core.image_data import ImageItem
from core.image_processing import qpixmap_to_pil
from widgets.image_cell import ImageCell, IMAGE_EXTENSIONS
from widgets.zoom_dialog import ZoomDialog


class GridWidget(QWidget):
    selection_changed = Signal(object)  # Optional[int]
    status_message = Signal(str)

    def __init__(self, model: GridModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.undo_stack = QUndoStack(self)
        self.cells: List[ImageCell] = []
        self.selected_index: Optional[int] = None

        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(self.model.settings.spacing)
        m = self.model.settings.margin
        self.grid_layout.setContentsMargins(m, m, m, m)

        self.model.grid_resized.connect(self._rebuild_cells)
        self.model.changed.connect(self._refresh_all_cells)

        self._rebuild_cells()

    # -- building the widget grid -------------------------------------------
    def _rebuild_cells(self):
        # clear old widgets
        for cell in self.cells:
            self.grid_layout.removeWidget(cell)
            cell.deleteLater()
        self.cells = []

        rows, cols = self.model.settings.rows, self.model.settings.cols
        for i in range(rows * cols):
            cell = ImageCell(i, self.model, self)
            cell.set_item(self.model.items[i])
            cell.request_remove.connect(self.remove_image)
            cell.request_replace.connect(self.replace_image_dialog)
            cell.request_zoom.connect(self.open_zoom)
            cell.request_view_original.connect(self.open_zoom)
            cell.file_dropped.connect(self._on_cell_file_dropped)
            cell.image_data_dropped.connect(self._on_cell_image_data_dropped)
            cell.reorder_requested.connect(self.reorder_images)
            cell.label_edited.connect(self._on_label_edited)
            cell.selected.connect(self._on_cell_selected)
            r, c = divmod(i, cols)
            self.grid_layout.addWidget(cell, r, c)
            self.cells.append(cell)

        self.apply_layout_settings()

    def apply_layout_settings(self):
        s = self.model.settings
        self.grid_layout.setSpacing(s.spacing)
        self.grid_layout.setContentsMargins(s.margin, s.margin, s.margin, s.margin)
        self.setStyleSheet(f"background-color: {s.background_color};")
        for cell in self.cells:
            cell.setMinimumSize(60, 60)
            cell.apply_settings()

    def _refresh_all_cells(self):
        for i, cell in enumerate(self.cells):
            cell.set_item(self.model.items[i] if i < len(self.model.items) else None)

    # -- grid resize ---------------------------------------------------------
    def set_grid_size(self, rows: int, cols: int):
        if rows == self.model.settings.rows and cols == self.model.settings.cols:
            return
        cmd = ResizeGridCommand(self.model, rows, cols)
        self.undo_stack.push(cmd)

    # -- adding images ---------------------------------------------------------
    def add_image_paths(self, paths: List[str], target_index: Optional[int] = None):
        """Add one or more image files. If target_index is given and empty/replace,
        the first image goes there; remaining images fill subsequent empty cells."""
        remaining = list(paths)
        if target_index is not None and remaining:
            path = remaining.pop(0)
            item = ImageItem(path=path)
            self.undo_stack.push(SetImageCommand(self.model, target_index, item,
                                                  text=f"Add {os.path.basename(path)}"))
        for path in remaining:
            idx = self.model.first_empty_index()
            if idx is None:
                self._grow_grid_for_more_images(len(remaining) + 1)
                idx = self.model.first_empty_index()
            if idx is None:
                self.status_message.emit("Grid is full — increase rows/cols to add more images.")
                break
            item = ImageItem(path=path)
            self.undo_stack.push(SetImageCommand(self.model, idx, item,
                                                  text=f"Add {os.path.basename(path)}"))

    def add_pixmap(self, pixmap, target_index: Optional[int] = None):
        pil_img = qpixmap_to_pil(pixmap)
        item = ImageItem(pil_image=pil_img, label="Pasted Image")
        idx = target_index
        if idx is None:
            idx = self.selected_index if self.selected_index is not None else self.model.first_empty_index()
        if idx is None:
            self._grow_grid_for_more_images(1)
            idx = self.model.first_empty_index()
        if idx is None:
            self.status_message.emit("Grid is full — increase rows/cols to paste more images.")
            return
        self.undo_stack.push(SetImageCommand(self.model, idx, item, text="Paste Image"))

    def _grow_grid_for_more_images(self, extra_needed: int):
        s = self.model.settings
        while s.rows * s.cols < self.model.filled_count() + extra_needed:
            if s.cols <= s.rows:
                s.cols += 1
            else:
                s.rows += 1
        self.model.apply_grid_size_silent(s.rows, s.cols)

    # -- cell-driven actions -------------------------------------------------
    def _on_cell_file_dropped(self, index: int, paths: List[str]):
        self.add_image_paths(paths, target_index=index)

    def _on_cell_image_data_dropped(self, index: int, pixmap):
        self.add_pixmap(pixmap, target_index=index)

    def _on_label_edited(self, index: int, text: str):
        self.undo_stack.push(SetLabelCommand(self.model, index, text))

    def _on_cell_selected(self, index: int):
        self.selected_index = index
        for i, cell in enumerate(self.cells):
            cell.set_selected(i == index)
        self.selection_changed.emit(index)

    def remove_image(self, index: int):
        if self.model.items[index] is not None:
            self.undo_stack.push(SetImageCommand(self.model, index, None, text="Remove Image"))

    def remove_selected(self):
        if self.selected_index is not None:
            self.remove_image(self.selected_index)

    def replace_image_dialog(self, index: int):
        path, _ = QFileDialog.getOpenFileName(
            self, "Replace Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
        )
        if path:
            item = ImageItem(path=path)
            self.undo_stack.push(SetImageCommand(self.model, index, item, text="Replace Image"))

    def reorder_images(self, src_index: int, dst_index: int):
        self.undo_stack.push(SwapImagesCommand(self.model, src_index, dst_index))

    def open_zoom(self, index: int):
        item = self.model.items[index]
        if item is not None:
            dlg = ZoomDialog(item, self)
            dlg.exec()

    # -- global drag & drop (drop anywhere on the grid background) ------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            paths = [u.toLocalFile() for u in mime.urls()
                     if os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_EXTENSIONS]
            if paths:
                self.add_image_paths(paths)
                event.acceptProposedAction()
                return
        if mime.hasImage():
            from PySide6.QtGui import QPixmap
            pixmap = QPixmap.fromImage(mime.imageData())
            if not pixmap.isNull():
                self.add_pixmap(pixmap)
                event.acceptProposedAction()
