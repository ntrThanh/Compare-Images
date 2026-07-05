"""Image Compare — a desktop tool for visually comparing multiple images
(model outputs, ablations, before/after, etc.) side by side in a
customizable grid.

Run with:
    python main.py
"""
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from widgets.main_window import MainWindow

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(APP_DIR, "assets", "icon_256.png")

DARK_STYLESHEET = """
QMainWindow, QDialog { background-color: #232323; }
QWidget { color: #e0e0e0; font-size: 13px; }
QGroupBox {
    border: 1px solid #444; border-radius: 6px; margin-top: 10px; padding-top: 8px;
    font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton {
    background-color: #3a3a3a; border: 1px solid #555; border-radius: 4px; padding: 6px 10px;
}
QPushButton:hover { background-color: #454545; }
QPushButton:pressed { background-color: #2a2a2a; }
QComboBox, QSpinBox, QLineEdit {
    background-color: #2f2f2f; border: 1px solid #555; border-radius: 4px; padding: 3px;
}
QDockWidget { titlebar-close-icon: none; }
QScrollArea { border: none; }
QStatusBar { background-color: #1e1e1e; }
QMenuBar { background-color: #2b2b2b; }
QMenuBar::item:selected { background-color: #3a3a3a; }
QMenu { background-color: #2b2b2b; border: 1px solid #444; }
QMenu::item:selected { background-color: #3a3a3a; }
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Image Compare")
    app.setStyleSheet(DARK_STYLESHEET)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
