"""AstroMotion main window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDockWidget,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from astromotion.config import APP_NAME, EXPORT_RESOLUTION_PRESETS, SUPPORTED_IMAGE_FILTER
from astromotion.export.render_worker import RenderSettings, RenderWorker
from astromotion.i18n import SUPPORTED_LANGUAGES, language_manager, tr
from astromotion.presets import get_preset
from astromotion.ui.advanced_settings_panel import AdvancedSettingsPanel
from astromotion.ui.gl_preview_widget import GLPreviewWidget
from astromotion.ui.preset_bar import PresetBar
from astromotion.ui.render_progress_dialog import RenderProgressDialog


ADVANCED_DOCK_DEFAULT_WIDTH = 440
ADVANCED_DOCK_MINIMUM_WIDTH = 430


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1440, 880)

        self.render_worker: RenderWorker | None = None
        self.progress_dialog: RenderProgressDialog | None = None

        self.preview = GLPreviewWidget(self)
        self.preset_bar = PresetBar(self)
        self.settings_panel = AdvancedSettingsPanel(self)
        self.import_button = QPushButton()
        self.import_button.setObjectName("ImportButton")
        self.file_label = QLabel()
        self.file_label.setObjectName("MutedLabel")
        self.title_label = QLabel()
        self.title_label.setObjectName("AppTitle")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("MutedLabel")
        self.status_label = QLabel()
        self.status_label.setObjectName("StatusPill")
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("TopLanguageCombo")
        self.play_button = QPushButton()
        self.play_button.setObjectName("PlayButton")
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setObjectName("TimelineSlider")
        self.time_label = QLabel("00:00 / 00:10")
        self.time_label.setObjectName("MutedLabel")
        self._duration_seconds = 10.0
        self._slider_dragging = False
        self._source_star_count = 0
        self._using_source_stars = False

        self._build_layout()
        self._connect_signals()
        self.retranslate_ui()

    def _build_layout(self) -> None:
        central = QWidget()
        central.setObjectName("AppRoot")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        toolbar = QHBoxLayout(top_bar)
        toolbar.setContentsMargins(14, 10, 14, 10)
        toolbar.setSpacing(10)
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        toolbar.addLayout(title_box, 1)
        toolbar.addWidget(self.status_label)
        toolbar.addWidget(self.language_combo)
        self.import_button.clicked.connect(self._choose_image)
        toolbar.addWidget(self.import_button)
        outer.addWidget(top_bar)

        preview_frame = QFrame()
        preview_frame.setObjectName("PreviewFrame")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(0)
        preview_layout.addWidget(self.preview, 1)
        outer.addWidget(preview_frame, 1)

        info_row = QHBoxLayout()
        info_row.addWidget(self.file_label, 1)
        info_row.addWidget(self.time_label)
        outer.addLayout(info_row)
        outer.addWidget(self._build_playback_controls())
        outer.addWidget(self.preset_bar)
        self.setCentralWidget(central)

        self.advanced_dock = QDockWidget(self)
        self.advanced_dock.setMinimumWidth(ADVANCED_DOCK_MINIMUM_WIDTH)
        self.advanced_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.advanced_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.advanced_dock.setWidget(self.settings_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.advanced_dock)
        self.resizeDocks([self.advanced_dock], [ADVANCED_DOCK_DEFAULT_WIDTH], Qt.Orientation.Horizontal)

    def _connect_signals(self) -> None:
        self.preset_bar.preset_selected.connect(self._select_preset)
        self.settings_panel.settings_changed.connect(self.preview.update_particle_params)
        self.settings_panel.render_requested.connect(self._start_render)
        self.settings_panel.duration_changed.connect(self._set_preview_duration)
        self.preview.preview_time_changed.connect(self._preview_time_changed)
        self.preview.playback_state_changed.connect(self._playback_state_changed)
        self.preview.source_stars_changed.connect(self._source_stars_changed)
        self.play_button.clicked.connect(self._toggle_playback)
        self.time_slider.sliderPressed.connect(self._preview_slider_pressed)
        self.time_slider.sliderReleased.connect(self._preview_slider_released)
        self.time_slider.valueChanged.connect(self._preview_slider_changed)
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        language_manager.language_changed.connect(lambda _language: self.retranslate_ui())

    def _build_playback_controls(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("PlaybackBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        self.play_button.setMinimumWidth(80)
        self.time_slider.setRange(0, int(self._duration_seconds * 1000))
        self.time_slider.setSingleStep(100)
        self.time_slider.setPageStep(1000)
        layout.addWidget(self.play_button)
        layout.addWidget(self.time_slider, 1)
        return frame

    def retranslate_ui(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.title_label.setText(tr("app.title"))
        self.subtitle_label.setText(tr("app.subtitle"))
        self.import_button.setText(tr("toolbar.import"))
        self.file_label.setText(
            self.preview.current_image_path.name if self.preview.current_image_path else tr("toolbar.no_image")
        )
        self._refresh_status_label()
        self._refresh_language_combo()
        self.advanced_dock.setWindowTitle(tr("dock.advanced"))
        self._playback_state_changed(self.preview.is_playing)
        self._update_time_label(self.preview.preview_time_seconds)
        self.preset_bar.retranslate_ui()
        self.settings_panel.retranslate_ui()

    def _refresh_language_combo(self) -> None:
        current_language = language_manager.current_language
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        for language in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(tr(f"language.{language}"), language)
        index = max(0, self.language_combo.findData(current_language))
        self.language_combo.setCurrentIndex(index)
        self.language_combo.blockSignals(False)

    def _language_changed(self) -> None:
        language_manager.set_language(str(self.language_combo.currentData()))

    def _choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("dialog.import_title"), "", SUPPORTED_IMAGE_FILTER)
        if not path:
            return
        try:
            self.preview.load_image(path)
            self.file_label.setText(Path(path).name)
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"{tr('dialog.import_failed')}\n{exc}")

    def _source_stars_changed(self, count: int, using_source_stars: bool) -> None:
        self._source_star_count = int(count)
        self._using_source_stars = bool(using_source_stars)
        self._refresh_status_label()

    def _refresh_status_label(self) -> None:
        if self.preview.current_image_path and self._using_source_stars:
            self.status_label.setText(tr("toolbar.source_stars").format(count=self._source_star_count))
        elif self.preview.current_image_path:
            self.status_label.setText(tr("toolbar.generated_stars"))
        else:
            self.status_label.setText(tr("toolbar.ready"))

    def _select_preset(self, name: str) -> None:
        self.preview.set_preset(name)
        self.settings_panel.apply_preset(get_preset(name), emit=False)
        self._set_slider_value(0.0)

    def _toggle_playback(self) -> None:
        if self.preview.preview_time_seconds >= self._duration_seconds:
            self.preview.seek_preview(0.0, pause=False)
        self.preview.set_playing(not self.preview.is_playing)

    def _preview_slider_pressed(self) -> None:
        self._slider_dragging = True
        self.preview.set_playing(False)

    def _preview_slider_released(self) -> None:
        self._slider_dragging = False
        self.preview.seek_preview(self.time_slider.value() / 1000.0, pause=True)

    def _preview_slider_changed(self, value: int) -> None:
        if self._slider_dragging:
            seconds = value / 1000.0
            self._update_time_label(seconds)
            self.preview.seek_preview(seconds, pause=True)

    def _preview_time_changed(self, seconds: float) -> None:
        if not self._slider_dragging:
            self._set_slider_value(seconds)
        self._update_time_label(seconds)

    def _playback_state_changed(self, is_playing: bool) -> None:
        self.play_button.setText(tr("play.pause") if is_playing else tr("play.play"))

    def _set_preview_duration(self, duration_seconds: float) -> None:
        self._duration_seconds = max(0.1, float(duration_seconds))
        self.time_slider.setRange(0, int(self._duration_seconds * 1000))
        self.preview.set_duration_seconds(self._duration_seconds)
        self._preview_time_changed(self.preview.preview_time_seconds)

    def _set_slider_value(self, seconds: float) -> None:
        self.time_slider.blockSignals(True)
        self.time_slider.setValue(int(max(0.0, min(seconds, self._duration_seconds)) * 1000))
        self.time_slider.blockSignals(False)

    def _update_time_label(self, seconds: float) -> None:
        self.time_label.setText(f"{_format_time(seconds)} / {_format_time(self._duration_seconds)}")

    def _start_render(self) -> None:
        if self.render_worker is not None:
            return
        default_output = Path.home() / "Videos" / "AstroMotion" / "astromotion_output.mp4"
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("dialog.render_title"),
            str(default_output),
            "MP4 Video (*.mp4)",
        )
        if not path:
            return

        render_options = self.settings_panel.render_options()
        export_width, export_height = self._resolve_export_size(render_options["resolution_mode"])
        settings = RenderSettings(
            output_path=Path(path),
            image_path=self.preview.current_image_path,
            source_star_field=self.preview.current_source_star_field(),
            preset=self.preview.current_preset_state(),
            width=export_width,
            height=export_height,
            duration_seconds=render_options["duration_seconds"],
            fps=render_options["fps"],
        )
        self.progress_dialog = RenderProgressDialog(self)
        self.progress_dialog.set_progress(0)
        self.settings_panel.set_render_enabled(False)
        self.render_worker = RenderWorker(settings)
        self.render_worker.progress_changed.connect(self._render_progress)
        self.render_worker.render_finished.connect(self._render_finished)
        self.render_worker.render_failed.connect(self._render_failed)
        self.render_worker.finished.connect(self._render_thread_finished)
        self.render_worker.start()
        self.progress_dialog.show()

    def _render_progress(self, value: int) -> None:
        if self.progress_dialog:
            self.progress_dialog.set_progress(value)

    def _render_finished(self, output_path: str) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()
        self.settings_panel.set_render_enabled(True)
        output = Path(output_path)
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setText(tr("dialog.render_success"))
        open_button = box.addButton(tr("dialog.open_folder"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

    def _render_failed(self, message: str) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()
        self.settings_panel.set_render_enabled(True)
        QMessageBox.critical(self, APP_NAME, f"{tr('dialog.render_failed')}\n{message}")

    def _render_thread_finished(self) -> None:
        self.render_worker = None
        self.progress_dialog = None

    def _resolve_export_size(self, resolution_mode: str) -> tuple[int, int]:
        if resolution_mode == "source" and self.preview.current_image_size is not None:
            width, height = self.preview.current_image_size
        else:
            width, height = EXPORT_RESOLUTION_PRESETS.get(resolution_mode, EXPORT_RESOLUTION_PRESETS["2k"])
        return _even_dimension(width), _even_dimension(height)

    def closeEvent(self, event) -> None:
        if self.render_worker is not None:
            self.render_worker.cancel()
            self.render_worker.wait(1500)
        self.preview.cleanup()
        super().closeEvent(event)


def _format_time(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def _even_dimension(value: int) -> int:
    return max(2, int(value) - (int(value) % 2))
