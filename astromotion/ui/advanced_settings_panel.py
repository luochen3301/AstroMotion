"""Collapsible advanced particle, camera, and export settings panel."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from astromotion.i18n import tr
from astromotion.presets import get_preset


@dataclass(slots=True)
class SliderSpec:
    key: str
    minimum: float
    maximum: float
    step: float
    group: str
    integer: bool = False


class AdvancedSettingsPanel(QWidget):
    settings_changed = Signal(dict)
    render_requested = Signal()
    duration_changed = Signal(float)

    SPECS = [
        SliderSpec("particle_count", 1_000, 200_000, 1_000, "particles", True),
        SliderSpec("speed", 0.0, 5.0, 0.01, "particles"),
        SliderSpec("size", 0.5, 32.0, 0.1, "particles"),
        SliderSpec("glow", 0.0, 4.0, 0.05, "particles"),
        SliderSpec("brightness", 0.0, 5.0, 0.05, "particles"),
        SliderSpec("color_intensity", 0.0, 5.0, 0.05, "particles"),
        SliderSpec("opacity", 0.0, 1.0, 0.01, "particles"),
        SliderSpec("turbulence", 0.0, 2.0, 0.01, "particles"),
        SliderSpec("zoom_start", 0.7, 1.5, 0.01, "motion"),
        SliderSpec("zoom_end", 0.8, 1.8, 0.01, "motion"),
        SliderSpec("zoom_speed", 0.1, 3.0, 0.01, "motion"),
        SliderSpec("rotation_degrees", -20.0, 20.0, 0.1, "motion"),
        SliderSpec("trail_length", 0.0, 2.0, 0.01, "motion"),
        SliderSpec("depth_strength", 0.0, 2.0, 0.01, "motion"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("AdvancedSettingsPanel")
        self._rows: dict[str, _SliderRow] = {}
        self._labels: dict[str, QLabel] = {}
        self._group_titles: dict[str, QLabel] = {}
        self._collapsed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("PanelTitle")
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.toggle_button = QPushButton()
        self.toggle_button.setFixedWidth(72)
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.toggle_button)
        root.addLayout(header)

        self.body = QScrollArea()
        self.body.setObjectName("SettingsScroll")
        self.body.setWidgetResizable(True)
        self.body.setFrameShape(QFrame.Shape.NoFrame)
        self.body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body.viewport().setAutoFillBackground(False)

        content = QWidget()
        content.setObjectName("SettingsContent")
        body_layout = QVBoxLayout(content)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        group_forms: dict[str, QFormLayout] = {}
        for group in ("particles", "motion"):
            card, form = self._create_group_card(group)
            group_forms[group] = form
            body_layout.addWidget(card)

        for spec in self.SPECS:
            row = _SliderRow(spec)
            row.value_changed.connect(self._emit_settings)
            label = QLabel()
            label.setObjectName("FormLabel")
            label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self._rows[spec.key] = row
            self._labels[spec.key] = label
            group_forms[spec.group].addRow(label, row)

        export_card, export_form = self._create_group_card("export")
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(1.0, 120.0)
        self.duration_spin.setSingleStep(1.0)
        self.duration_spin.setDecimals(1)
        self.duration_spin.setValue(10.0)
        self.duration_spin.valueChanged.connect(lambda value: self.duration_changed.emit(float(value)))

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(24, 120)
        self.fps_spin.setSingleStep(6)
        self.fps_spin.setValue(60)

        self.resolution_combo = QComboBox()
        self._export_labels = {
            "duration": QLabel(),
            "fps": QLabel(),
            "resolution": QLabel(),
        }
        for label in self._export_labels.values():
            label.setObjectName("FormLabel")
            label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        export_form.addRow(self._export_labels["duration"], self.duration_spin)
        export_form.addRow(self._export_labels["fps"], self.fps_spin)
        export_form.addRow(self._export_labels["resolution"], self.resolution_combo)
        body_layout.addWidget(export_card)

        self.render_hint = QLabel()
        self.render_hint.setObjectName("MutedLabel")
        self.render_hint.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.render_button = QPushButton()
        self.render_button.setObjectName("RenderButton")
        self.render_button.clicked.connect(self.render_requested.emit)
        body_layout.addWidget(self.render_hint)
        body_layout.addWidget(self.render_button)
        body_layout.addStretch(1)
        self.body.setWidget(content)
        root.addWidget(self.body, 1)

        self.apply_preset(get_preset(), emit=False)
        self.retranslate_ui()

    def _create_group_card(self, group: str) -> tuple[QFrame, QFormLayout]:
        card = QFrame()
        card.setObjectName("SettingsGroup")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        title = QLabel()
        title.setObjectName("GroupTitle")
        title.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(title)
        layout.addLayout(form)
        self._group_titles[group] = title
        return card, form

    def set_render_enabled(self, enabled: bool) -> None:
        self.render_button.setEnabled(enabled)

    def toggle_collapsed(self) -> None:
        self._collapsed = not self._collapsed
        self.body.setVisible(not self._collapsed)
        self.toggle_button.setText(tr("panel.expand") if self._collapsed else tr("panel.collapse"))

    def apply_preset(self, preset: dict, emit: bool = True) -> None:
        for key, row in self._rows.items():
            if key in preset:
                row.set_value(preset[key], emit=False)
        if emit:
            self._emit_settings()

    def current_settings(self) -> dict:
        return {key: row.value() for key, row in self._rows.items()}

    def render_options(self) -> dict:
        return {
            "duration_seconds": float(self.duration_spin.value()),
            "fps": int(self.fps_spin.value()),
            "resolution_mode": str(self.resolution_combo.currentData()),
        }

    def retranslate_ui(self) -> None:
        self.title_label.setText(tr("panel.title"))
        self.toggle_button.setText(tr("panel.expand") if self._collapsed else tr("panel.collapse"))
        for group, title in self._group_titles.items():
            title.setText(tr(f"panel.group.{group}"))
        for key, label in self._labels.items():
            label.setText(tr(f"setting.{key}"))

        current_resolution = self.resolution_combo.currentData() or "source"
        self.resolution_combo.blockSignals(True)
        self.resolution_combo.clear()
        self.resolution_combo.addItem(tr("resolution.source"), "source")
        self.resolution_combo.addItem(tr("resolution.2k"), "2k")
        self.resolution_combo.addItem(tr("resolution.4k"), "4k")
        index = max(0, self.resolution_combo.findData(current_resolution))
        self.resolution_combo.setCurrentIndex(index)
        self.resolution_combo.blockSignals(False)

        self._export_labels["duration"].setText(tr("setting.duration"))
        self._export_labels["fps"].setText(tr("setting.fps"))
        self._export_labels["resolution"].setText(tr("setting.resolution"))
        self.render_hint.setText(tr("export.hint"))
        self.render_button.setText(tr("export.render"))

    def _emit_settings(self) -> None:
        self.settings_changed.emit(self.current_settings())


class _SliderRow(QWidget):
    value_changed = Signal()

    def __init__(self, spec: SliderSpec, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SliderRow")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.spec = spec
        self._scale = 1 if spec.integer else int(round(1.0 / spec.step))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("ParamSlider")
        self.slider.setRange(int(spec.minimum * self._scale), int(spec.maximum * self._scale))
        layout.addWidget(self.slider, 1)

        if spec.integer:
            self.spin = QSpinBox()
            self.spin.setRange(int(spec.minimum), int(spec.maximum))
            self.spin.setSingleStep(int(spec.step))
        else:
            self.spin = QDoubleSpinBox()
            self.spin.setRange(float(spec.minimum), float(spec.maximum))
            self.spin.setSingleStep(float(spec.step))
            self.spin.setDecimals(2)
        self.spin.setObjectName("ParamSpin")
        layout.addWidget(self.spin)

        self.slider.valueChanged.connect(self._slider_changed)
        self.spin.valueChanged.connect(self._spin_changed)

    def value(self):
        return int(self.spin.value()) if self.spec.integer else float(self.spin.value())

    def set_value(self, value, emit: bool = True) -> None:
        self.blockSignals(True)
        self.slider.blockSignals(True)
        self.spin.blockSignals(True)
        if self.spec.integer:
            val = int(value)
            self.spin.setValue(val)
            self.slider.setValue(val)
        else:
            val = float(value)
            self.spin.setValue(val)
            self.slider.setValue(int(round(val * self._scale)))
        self.spin.blockSignals(False)
        self.slider.blockSignals(False)
        self.blockSignals(False)
        if emit:
            self.value_changed.emit()

    def _slider_changed(self, raw: int) -> None:
        value = raw if self.spec.integer else raw / self._scale
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)
        self.value_changed.emit()

    def _spin_changed(self, value) -> None:
        raw = int(value if self.spec.integer else round(float(value) * self._scale))
        self.slider.blockSignals(True)
        self.slider.setValue(raw)
        self.slider.blockSignals(False)
        self.value_changed.emit()
