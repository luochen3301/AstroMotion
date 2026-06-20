"""Large preset buttons under the preview canvas."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget

from astromotion.i18n import preset_display_name
from astromotion.presets import default_preset_name, preset_names


class PresetBar(QWidget):
    preset_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PresetBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(10)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for name in preset_names():
            button = QPushButton()
            button.setObjectName("PresetButton")
            button.setCheckable(True)
            button.setMinimumHeight(46)
            button.setToolTip(name)
            layout.addWidget(button)
            self.group.addButton(button)
            self._buttons[name] = button
            button.clicked.connect(lambda checked=False, preset_name=name: self._select(preset_name))

        default_name = default_preset_name()
        if default_name in self._buttons:
            self._buttons[default_name].setChecked(True)
        elif self.group.buttons():
            self.group.buttons()[0].setChecked(True)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        for name, button in self._buttons.items():
            button.setText(preset_display_name(name))

    def _select(self, name: str) -> None:
        self.preset_selected.emit(name)
