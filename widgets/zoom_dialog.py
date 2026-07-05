"""Modal-less dialog that shows one image at full resolution.

Opened via double-click on a cell, or the "Zoom" / "View Original Size"
context menu actions.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.image_data import ImageItem
from core.image_processing import pil_to_qpixmap


class ZoomDialog(QDialog):
    def __init__(self, item: ImageItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle(item.display_name() or "Image Viewer")
        self.resize(900, 700)

        self._base_pixmap: QPixmap = pil_to_qpixmap(item.load_full_image())
        self._scale = 1.0

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.zoom_out_btn = QPushButton("−")
        self.zoom_in_btn = QPushButton("+")
        self.reset_btn = QPushButton("Fit to Window")
        self.actual_size_btn = QPushButton("100%")
        for b in (self.zoom_out_btn, self.zoom_in_btn, self.actual_size_btn, self.reset_btn):
            b.setFixedWidth(110)
        self.info_label = QLabel(
            f"{self._base_pixmap.width()} × {self._base_pixmap.height()} px"
        )
        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.zoom_in_btn)
        toolbar.addWidget(self.actual_size_btn)
        toolbar.addWidget(self.reset_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.info_label)
        layout.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.image_label = QLabel()
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.scroll.setWidget(self.image_label)
        layout.addWidget(self.scroll, 1)

        self.zoom_in_btn.clicked.connect(lambda: self._set_scale(self._scale * 1.25))
        self.zoom_out_btn.clicked.connect(lambda: self._set_scale(self._scale / 1.25))
        self.actual_size_btn.clicked.connect(lambda: self._set_scale(1.0))
        self.reset_btn.clicked.connect(self._fit_to_window)

        QShortcut(QKeySequence.ZoomIn, self, activated=lambda: self._set_scale(self._scale * 1.25))
        QShortcut(QKeySequence.ZoomOut, self, activated=lambda: self._set_scale(self._scale / 1.25))
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.close)

        self._fit_to_window()

    def _set_scale(self, scale: float):
        self._scale = max(0.05, min(8.0, scale))
        w = max(1, int(self._base_pixmap.width() * self._scale))
        h = max(1, int(self._base_pixmap.height() * self._scale))
        scaled = self._base_pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.resize(scaled.size())

    def _fit_to_window(self):
        avail = self.scroll.viewport().size()
        if self._base_pixmap.width() == 0 or self._base_pixmap.height() == 0:
            return
        scale = min(
            avail.width() / self._base_pixmap.width(),
            avail.height() / self._base_pixmap.height(),
            1.0,
        )
        self._set_scale(scale if scale > 0 else 1.0)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = 1.15 if event.angleDelta().y() > 0 else (1 / 1.15)
            self._set_scale(self._scale * delta)
            event.accept()
        else:
            super().wheelEvent(event)
