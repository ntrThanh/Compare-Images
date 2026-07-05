"""Dockable control panel: grid size, spacing/margin, colors, labels, export."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from core.settings import GridSettings


class ColorButton(QPushButton):
    color_changed = Signal(str)

    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedWidth(70)
        self._update_style()
        self.clicked.connect(self._pick_color)

    def _update_style(self):
        self.setText(self.color_hex)
        self.setStyleSheet(f"background-color: {self.color_hex}; color: white;")

    def _pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_hex = color.name()
            self._update_style()
            self.color_changed.emit(self.color_hex)

    def set_color(self, color_hex: str):
        self.color_hex = color_hex
        self._update_style()


class SettingsPanel(QWidget):
    grid_size_changed = Signal(int, int)   # rows, cols
    spacing_changed = Signal(int)
    margin_changed = Signal(int)
    background_changed = Signal(str)
    padding_color_changed = Signal(str)
    alignment_changed = Signal(str)
    border_toggled = Signal(bool)
    border_color_changed = Signal(str)
    shadow_toggled = Signal(bool)
    labels_toggled = Signal(bool)
    label_font_size_changed = Signal(int)
    label_color_changed = Signal(str)
    export_scale_changed = Signal(int)
    export_png_requested = Signal()
    copy_to_clipboard_requested = Signal()

    def __init__(self, settings: GridSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setMinimumWidth(280)
        self.setMaximumWidth(340)

        root = QVBoxLayout(self)
        root.addWidget(self._build_grid_group())
        root.addWidget(self._build_layout_group())
        root.addWidget(self._build_style_group())
        root.addWidget(self._build_label_group())
        root.addWidget(self._build_export_group())
        root.addStretch(1)

    # -- Grid size ---------------------------------------------------------
    def _build_grid_group(self) -> QGroupBox:
        box = QGroupBox("Grid Layout")
        form = QFormLayout(box)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 20)
        self.rows_spin.setValue(self.settings.rows)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 20)
        self.cols_spin.setValue(self.settings.cols)

        self.rows_spin.valueChanged.connect(self._emit_grid_size)
        self.cols_spin.valueChanged.connect(self._emit_grid_size)

        form.addRow("Rows", self.rows_spin)
        form.addRow("Columns", self.cols_spin)
        return box

    def _emit_grid_size(self):
        self.grid_size_changed.emit(self.rows_spin.value(), self.cols_spin.value())

    def sync_grid_size(self, rows: int, cols: int):
        self.rows_spin.blockSignals(True)
        self.cols_spin.blockSignals(True)
        self.rows_spin.setValue(rows)
        self.cols_spin.setValue(cols)
        self.rows_spin.blockSignals(False)
        self.cols_spin.blockSignals(False)

    # -- Spacing / margin / background ---------------------------------------
    def _build_layout_group(self) -> QGroupBox:
        box = QGroupBox("Spacing")
        form = QFormLayout(box)

        self.spacing_slider = QSlider(Qt.Horizontal)
        self.spacing_slider.setRange(0, 80)
        self.spacing_slider.setValue(self.settings.spacing)
        self.spacing_slider.valueChanged.connect(self.spacing_changed.emit)
        form.addRow("Between images", self.spacing_slider)

        self.margin_slider = QSlider(Qt.Horizontal)
        self.margin_slider.setRange(0, 150)
        self.margin_slider.setValue(self.settings.margin)
        self.margin_slider.valueChanged.connect(self.margin_changed.emit)
        form.addRow("Outer margin", self.margin_slider)

        self.bg_color_btn = ColorButton(self.settings.background_color)
        self.bg_color_btn.color_changed.connect(self.background_changed.emit)
        form.addRow("Background", self.bg_color_btn)

        return box

    # -- Image fit style -----------------------------------------------------
    def _build_style_group(self) -> QGroupBox:
        box = QGroupBox("Image Fit && Style")
        form = QFormLayout(box)

        self.padding_combo = QComboBox()
        self.padding_combo.addItems(["white", "black", "transparent"])
        self.padding_combo.setCurrentText(self.settings.padding_color)
        self.padding_combo.currentTextChanged.connect(self.padding_color_changed.emit)
        form.addRow("Padding color", self.padding_combo)

        self.align_combo = QComboBox()
        self.align_combo.addItems(["center", "top"])
        self.align_combo.setCurrentText(self.settings.alignment)
        self.align_combo.currentTextChanged.connect(self.alignment_changed.emit)
        form.addRow("Alignment", self.align_combo)

        self.border_check = QCheckBox("Show border")
        self.border_check.setChecked(self.settings.show_border)
        self.border_check.toggled.connect(self.border_toggled.emit)
        form.addRow(self.border_check)

        self.border_color_btn = ColorButton(self.settings.border_color)
        self.border_color_btn.color_changed.connect(self.border_color_changed.emit)
        form.addRow("Border color", self.border_color_btn)

        self.shadow_check = QCheckBox("Show shadow")
        self.shadow_check.setChecked(self.settings.show_shadow)
        self.shadow_check.toggled.connect(self.shadow_toggled.emit)
        form.addRow(self.shadow_check)

        return box

    # -- Labels --------------------------------------------------------------
    def _build_label_group(self) -> QGroupBox:
        box = QGroupBox("Labels")
        form = QFormLayout(box)

        self.labels_check = QCheckBox("Show labels")
        self.labels_check.setChecked(self.settings.show_labels)
        self.labels_check.toggled.connect(self.labels_toggled.emit)
        form.addRow(self.labels_check)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 48)
        self.font_size_spin.setValue(self.settings.label_font_size)
        self.font_size_spin.valueChanged.connect(self.label_font_size_changed.emit)
        form.addRow("Font size", self.font_size_spin)

        self.label_color_btn = ColorButton(self.settings.label_color)
        self.label_color_btn.color_changed.connect(self.label_color_changed.emit)
        form.addRow("Font color", self.label_color_btn)

        return box

    # -- Export ---------------------------------------------------------------
    def _build_export_group(self) -> QGroupBox:
        box = QGroupBox("Export")
        layout = QVBoxLayout(box)

        form = QFormLayout()
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["1x", "2x", "4x"])
        self.scale_combo.currentIndexChanged.connect(
            lambda i: self.export_scale_changed.emit([1, 2, 4][i])
        )
        form.addRow("Resolution", self.scale_combo)
        layout.addLayout(form)

        export_btn = QPushButton("Export as PNG… (Ctrl+S)")
        export_btn.clicked.connect(self.export_png_requested.emit)
        layout.addWidget(export_btn)

        copy_btn = QPushButton("Copy to Clipboard (Ctrl+C)")
        copy_btn.clicked.connect(self.copy_to_clipboard_requested.emit)
        layout.addWidget(copy_btn)

        return box
