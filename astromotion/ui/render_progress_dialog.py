"""Minimal modal progress dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from astromotion.i18n import tr


class RenderProgressDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("progress.title"))
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        self.label = QLabel(tr("progress.label"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)

    def set_progress(self, value: int) -> None:
        self.progress.setValue(int(value))
