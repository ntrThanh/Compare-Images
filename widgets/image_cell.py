"""A single cell in the comparison grid.

Handles:
 - accepting dropped files / internal reorder drags
 - starting a reorder drag when the user drags a filled cell
 - showing a cached, padded preview pixmap (fast repaint even with 100 cells)
 - remove / replace / zoom / view-original via context menu or double-click
 - an inline-editable label below the image
"""
from __future__ import annotations

import os
from typing import Optional

from PIL import Image
from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QDrag,
    QDragEnterEvent,
    QDropEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import QFrame, QLineEdit, QMenu, QVBoxLayout, QWidget

from core.image_data import ImageItem
from core.image_processing import fit_image_to_box, pil_to_qpixmap

CELL_MIME = "application/x-image-cell-index"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}


class ImageCell(QFrame):
    request_remove = Signal(int)
    request_replace = Signal(int)          # opens file picker for this index
    request_zoom = Signal(int)             # open zoom dialog
    request_view_original = Signal(int)    # double-click -> original size dialog
    file_dropped = Signal(int, list)       # index, list of file paths
    image_data_dropped = Signal(int, QPixmap)  # index, raw pixmap (e.g. dragged from a browser)
    reorder_requested = Signal(int, int)   # from_index, to_index
    label_edited = Signal(int, str)
    selected = Signal(int)

    def __init__(self, index: int, model, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.index = index
        self.model = model
        self.item: Optional[ImageItem] = None
        self._cached_pixmap: Optional[QPixmap] = None
        self.is_selected = False
        self._drag_start_pos: Optional[QPoint] = None

        self.setAcceptDrops(True)
        self.setMinimumSize(80, 60)
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addStretch(1)

        self.label_edit = QLineEdit(self)
        self.label_edit.setPlaceholderText("Add label…")
        self.label_edit.setAlignment(Qt.AlignCenter)
        self.label_edit.setFrame(False)
        self.label_edit.editingFinished.connect(self._on_label_committed)
        self.label_edit.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.label_edit)

        self._apply_label_style()

    # -- public API ----------------------------------------------------
    def set_item(self, item: Optional[ImageItem]):
        self.item = item
        self.label_edit.blockSignals(True)
        self.label_edit.setText(item.label if item else "")
        self.label_edit.blockSignals(False)
        self.label_edit.setVisible(bool(self.model.settings.show_labels))
        self._rebuild_cache()
        self.update()

    def apply_settings(self):
        self._apply_label_style()
        self.label_edit.setVisible(bool(self.model.settings.show_labels))
        self._rebuild_cache()
        self.update()

    def set_selected(self, value: bool):
        self.is_selected = value
        self.update()

    # -- internals -------------------------------------------------------
    def _apply_label_style(self):
        s = self.model.settings
        self.label_edit.setStyleSheet(
            f"background: transparent; border: none; color: {s.label_color}; "
            f"font-size: {s.label_font_size}px;"
        )

    def _on_label_committed(self):
        self.label_edited.emit(self.index, self.label_edit.text())

    def _rebuild_cache(self):
        if self.item is None:
            self._cached_pixmap = None
            return
        try:
            if self.item.path:
                # Use a downscaled thumbnail for on-screen preview; full-res is
                # only touched at export/zoom time (lazy loading for perf).
                with Image.open(self.item.path) as im:
                    im.load()
                    preview_src = im.copy()
            else:
                preview_src = self.item.pil_image
            box_w = max(20, self.width())
            box_h = max(20, self.height() - (24 if self.model.settings.show_labels else 0))
            fitted = fit_image_to_box(
                preview_src, box_w, box_h,
                self.model.settings.padding_color, self.model.settings.alignment,
            )
            self._cached_pixmap = pil_to_qpixmap(fitted)
        except Exception:
            self._cached_pixmap = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rebuild_cache()

    # -- painting ----------------------------------------------------------
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        s = self.model.settings
        img_h = self.height() - (24 if s.show_labels else 0)

        # checkerboard-ish neutral cell background so transparent padding is visible
        painter.fillRect(0, 0, self.width(), img_h, QColor("#3a3a3a"))

        if s.show_shadow and self._cached_pixmap is not None:
            painter.fillRect(4, 4, self.width() - 1, img_h - 1, QColor(0, 0, 0, 90))

        if self._cached_pixmap is not None:
            painter.drawPixmap(0, 0, self._cached_pixmap)
        else:
            painter.setPen(QColor("#777777"))
            painter.drawText(self.rect().adjusted(0, 0, 0, -24 if s.show_labels else 0),
                              Qt.AlignCenter, "Drop image here")

        if s.show_border:
            painter.setPen(QColor(s.border_color))
            painter.drawRect(0, 0, self.width() - 1, img_h - 1)

        if self.is_selected:
            pen = painter.pen()
            painter.setPen(QColor("#4a90e2"))
            painter.drawRect(1, 1, self.width() - 3, img_h - 3)
            painter.setPen(pen)

        painter.end()

    # -- mouse / drag interactions ------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.index)
            if self.item is not None:
                self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (
            self._drag_start_pos is not None
            and self.item is not None
            and (event.position().toPoint() - self._drag_start_pos).manhattanLength() > 12
        ):
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData(CELL_MIME, str(self.index).encode("utf-8"))
            drag.setMimeData(mime)
            if self._cached_pixmap is not None:
                drag.setPixmap(self._cached_pixmap.scaled(
                    100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            drag.exec(Qt.MoveAction)
            self._drag_start_pos = None
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.item is not None:
            self.request_view_original.emit(self.index)
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier and self.item is not None:
            delta = 1.1 if event.angleDelta().y() > 0 else (1 / 1.1)
            self.item.zoom = max(0.2, min(5.0, self.item.zoom * delta))
            self._rebuild_cache()
            self.update()
            event.accept()
        else:
            event.ignore()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        zoom_action = QAction("Zoom", self)
        original_action = QAction("View Original Size", self)
        replace_action = QAction("Replace Image…", self)
        remove_action = QAction("Remove", self)
        menu.addAction(zoom_action)
        menu.addAction(original_action)
        menu.addSeparator()
        menu.addAction(replace_action)
        menu.addAction(remove_action)

        has_item = self.item is not None
        zoom_action.setEnabled(has_item)
        original_action.setEnabled(has_item)
        remove_action.setEnabled(has_item)

        action = menu.exec(event.globalPos())
        if action == zoom_action:
            self.request_zoom.emit(self.index)
        elif action == original_action:
            self.request_view_original.emit(self.index)
        elif action == replace_action:
            self.request_replace.emit(self.index)
        elif action == remove_action:
            self.request_remove.emit(self.index)

    # -- drag & drop targets -------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasImage() or event.mimeData().hasFormat(CELL_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage() or event.mimeData().hasFormat(CELL_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        if mime.hasFormat(CELL_MIME):
            src_index = int(bytes(mime.data(CELL_MIME)).decode("utf-8"))
            if src_index != self.index:
                self.reorder_requested.emit(src_index, self.index)
            event.acceptProposedAction()
            return

        if mime.hasUrls():
            paths = []
            for url in mime.urls():
                local = url.toLocalFile()
                if local and os.path.splitext(local)[1].lower() in IMAGE_EXTENSIONS:
                    paths.append(local)
            if paths:
                self.file_dropped.emit(self.index, paths)
                event.acceptProposedAction()
                return

        if mime.hasImage():
            pixmap = QPixmap.fromImage(mime.imageData())
            if not pixmap.isNull():
                self.image_data_dropped.emit(self.index, pixmap)
                event.acceptProposedAction()
