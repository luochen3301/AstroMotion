"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from astromotion.config import APP_NAME
from astromotion.ui.main_window import MainWindow
from astromotion.ui.theme import app_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(app_stylesheet())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

