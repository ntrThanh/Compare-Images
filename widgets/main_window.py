"""Top-level QMainWindow that assembles the grid, settings panel, and menus."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QStatusBar,
    QWidget,
)

from core.exporter import render_grid_to_image, save_png
from core.grid_model import GridModel
from core.image_processing import pil_to_qpixmap
from widgets.grid_widget import GridWidget
from widgets.settings_panel import SettingsPanel

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Compare — Model Output Comparison Tool")
        self.resize(1400, 900)

        self.model = GridModel()

        self.grid_widget = GridWidget(self.model)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.grid_widget)
        self.scroll_area.setAcceptDrops(True)
        self.setCentralWidget(self.scroll_area)

        self.settings_panel = SettingsPanel(self.model.settings)
        dock = QDockWidget("Settings", self)
        dock.setWidget(self.settings_panel)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.grid_widget.status_message.connect(lambda msg: self.status.showMessage(msg, 5000))
        self.grid_widget.selection_changed.connect(self._on_selection_changed)

        self._build_menus()
        self._connect_settings_panel()

    # -- menus / shortcuts ----------------------------------------------------
    def _build_menus(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("Open Images…", self)
        open_action.setShortcut(QKeySequence.Open)  # Ctrl+O
        open_action.triggered.connect(self.open_images_dialog)
        file_menu.addAction(open_action)

        paste_action = QAction("Paste Image", self)
        paste_action.setShortcut(QKeySequence.Paste)  # Ctrl+V
        paste_action.triggered.connect(self.paste_from_clipboard)
        file_menu.addAction(paste_action)

        file_menu.addSeparator()

        export_action = QAction("Export as PNG…", self)
        export_action.setShortcut(QKeySequence.Save)  # Ctrl+S
        export_action.triggered.connect(self.export_png)
        file_menu.addAction(export_action)

        copy_action = QAction("Copy Composed Image", self)
        copy_action.setShortcut(QKeySequence.Copy)  # Ctrl+C
        copy_action.triggered.connect(self.copy_to_clipboard)
        file_menu.addAction(copy_action)

        edit_menu = menu_bar.addMenu("&Edit")

        self.undo_action = self.grid_widget.undo_stack.createUndoAction(self, "Undo")
        self.undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(self.undo_action)

        self.redo_action = self.grid_widget.undo_stack.createRedoAction(self, "Redo")
        self.redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(self.redo_action)

        edit_menu.addSeparator()

        delete_action = QAction("Remove Selected", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self.grid_widget.remove_selected)
        edit_menu.addAction(delete_action)
        # also make Delete work even without menu focus
        self.addAction(delete_action)
        self.addAction(open_action)
        self.addAction(paste_action)
        self.addAction(export_action)
        self.addAction(copy_action)

    # -- settings panel wiring -------------------------------------------------
    def _connect_settings_panel(self):
        sp = self.settings_panel
        gw = self.grid_widget
        s = self.model.settings

        sp.grid_size_changed.connect(gw.set_grid_size)
        self.model.grid_resized.connect(
            lambda: sp.sync_grid_size(s.rows, s.cols)
        )

        def _apply(attr, value):
            setattr(s, attr, value)
            gw.apply_layout_settings()
            self.model.notify_changed()

        sp.spacing_changed.connect(lambda v: _apply("spacing", v))
        sp.margin_changed.connect(lambda v: _apply("margin", v))
        sp.background_changed.connect(lambda v: _apply("background_color", v))
        sp.padding_color_changed.connect(lambda v: _apply("padding_color", v))
        sp.alignment_changed.connect(lambda v: _apply("alignment", v))
        sp.border_toggled.connect(lambda v: _apply("show_border", v))
        sp.border_color_changed.connect(lambda v: _apply("border_color", v))
        sp.shadow_toggled.connect(lambda v: _apply("show_shadow", v))
        sp.labels_toggled.connect(lambda v: _apply("show_labels", v))
        sp.label_font_size_changed.connect(lambda v: _apply("label_font_size", v))
        sp.label_color_changed.connect(lambda v: _apply("label_color", v))
        sp.export_scale_changed.connect(lambda v: setattr(s, "export_scale", v))

        sp.export_png_requested.connect(self.export_png)
        sp.copy_to_clipboard_requested.connect(self.copy_to_clipboard)

    def _on_selection_changed(self, index):
        if index is not None:
            self.status.showMessage(f"Selected cell {index + 1}", 2000)

    # -- file actions ------------------------------------------------------
    def open_images_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Open Images", "", IMAGE_FILTER)
        if paths:
            self.grid_widget.add_image_paths(paths)
            self.status.showMessage(f"Added {len(paths)} image(s)", 3000)

    def paste_from_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        if mime.hasImage():
            image = clipboard.image()
            pixmap = QPixmap.fromImage(image)
            if not pixmap.isNull():
                self.grid_widget.add_pixmap(pixmap)
                self.status.showMessage("Pasted image from clipboard", 3000)
                return
        if mime.hasUrls():
            paths = [u.toLocalFile() for u in mime.urls() if u.toLocalFile()]
            paths = [p for p in paths if os.path.splitext(p)[1].lower() in
                     {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}]
            if paths:
                self.grid_widget.add_image_paths(paths)
                return
        self.status.showMessage("Clipboard has no image to paste", 3000)

    def export_png(self):
        if self.model.filled_count() == 0:
            QMessageBox.information(self, "Nothing to Export", "Add at least one image first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Comparison Grid", "comparison.png", "PNG Image (*.png)")
        if not path:
            return
        try:
            save_png(self.model, path, scale=self.model.settings.export_scale)
            self.status.showMessage(f"Exported to {path}", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def copy_to_clipboard(self):
        if self.model.filled_count() == 0:
            QMessageBox.information(self, "Nothing to Copy", "Add at least one image first.")
            return
        try:
            pil_img = render_grid_to_image(self.model, scale=self.model.settings.export_scale)
            pixmap = pil_to_qpixmap(pil_img)
            QGuiApplication.clipboard().setPixmap(pixmap)
            self.status.showMessage("Composed image copied to clipboard", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Copy Failed", str(exc))

    # -- top-level drag & drop (so dropping anywhere on the window works) -----
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.grid_widget.dropEvent(event)
