"""OpenGL preview canvas."""

from __future__ import annotations

import ctypes
from pathlib import Path

import numpy as np
from PySide6.QtCore import QElapsedTimer, QTimer, Signal, Slot
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from astromotion.engine.camera import identity_matrix
from astromotion.engine.camera_motion import rotation_at_time, zoom_at_time
from astromotion.engine.color_sampling import build_star_color_palette, sample_theme_colors
from astromotion.engine.particle_engine import ParticleEngine, _gl_handle
from astromotion.engine.shader_program import compile_program, read_shader
from astromotion.media.image_loader import load_image_rgb
from astromotion.media.texture_loader import create_texture_from_rgb, delete_texture
from astromotion.presets import default_preset_name, get_preset


class GLPreviewWidget(QOpenGLWidget):
    """Realtime WYSIWYG preview using OpenGL point sprites."""

    preview_time_changed = Signal(float)
    playback_state_changed = Signal(bool)

    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumSize(860, 520)
        self.engine = ParticleEngine(max_particles=200_000, preset=default_preset_name(), seed=7)
        self.current_preset_name = default_preset_name()
        self.preview_time_seconds = 0.0
        self.duration_seconds = 10.0
        self.is_playing = True
        self.current_image_path: Path | None = None
        self.current_image_size: tuple[int, int] | None = None
        self.current_theme_colors: list[tuple[float, float, float, float]] | None = None
        self._image_rgb: np.ndarray | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self.update)
        self._timer.start()

        self._elapsed = QElapsedTimer()
        self._background_program = 0
        self._quad_vao = 0
        self._quad_vbo = 0
        self._background_texture = 0
        self._zoom = 1.0
        self._rotation_degrees = 0.0

    def load_image(self, path: str | Path) -> None:
        image = load_image_rgb(path)
        self.current_image_path = Path(path)
        self._image_rgb = image
        self.current_image_size = (int(image.shape[1]), int(image.shape[0]))
        self.current_theme_colors = sample_theme_colors(image, count=5)
        self.engine.update_params(
            {"theme_colors": self._theme_colors_for_preset(self.engine.preset, self.current_theme_colors)}
        )
        if self.context() is not None and self.isValid():
            self.makeCurrent()
            self._upload_background_texture()
            self.doneCurrent()
        self.update()

    @Slot(str)
    def set_preset(self, name: str) -> None:
        preset = get_preset(name)
        if self.current_theme_colors:
            preset["theme_colors"] = self._theme_colors_for_preset(preset, self.current_theme_colors)
        self.current_preset_name = name
        self.engine.set_preset(preset)
        self.seek_preview(0.0, pause=False)
        self.update()

    @Slot(dict)
    def update_particle_params(self, params: dict) -> None:
        self.engine.update_params(params)
        self.update()

    @Slot(float)
    def set_duration_seconds(self, duration_seconds: float) -> None:
        self.duration_seconds = max(0.1, float(duration_seconds))
        if self.preview_time_seconds > self.duration_seconds:
            self.seek_preview(self.duration_seconds, pause=True)
        self.update()

    @Slot(bool)
    def set_playing(self, is_playing: bool) -> None:
        self.is_playing = bool(is_playing)
        self._elapsed.restart()
        self.playback_state_changed.emit(self.is_playing)
        self.update()

    @Slot(float)
    def seek_preview(self, time_seconds: float, pause: bool = True) -> None:
        self.preview_time_seconds = max(0.0, min(float(time_seconds), self.duration_seconds))
        if pause:
            self.is_playing = False
            self.playback_state_changed.emit(False)
        self.engine.seek(self.preview_time_seconds)
        self.preview_time_changed.emit(self.preview_time_seconds)
        self._elapsed.restart()
        self.update()

    def current_preset_state(self) -> dict:
        return dict(self.engine.preset)

    def _theme_colors_for_preset(
        self,
        preset: dict,
        sampled_colors: list[tuple[float, float, float, float]],
    ) -> list[tuple[float, float, float, float]]:
        if preset.get("emitter") == "depth_starfield":
            return build_star_color_palette(sampled_colors)
        return list(sampled_colors)

    def initializeGL(self) -> None:
        from OpenGL import GL

        GL.glClearColor(0.015, 0.02, 0.035, 1.0)
        GL.glEnable(GL.GL_PROGRAM_POINT_SIZE)
        self._background_program = compile_program(
            read_shader("fullscreen_image.vert"),
            read_shader("fullscreen_image.frag"),
        )
        self._create_background_quad()
        self.engine.initialize_gl()
        self._upload_background_texture()
        self._elapsed.start()

    def resizeGL(self, width: int, height: int) -> None:
        self.engine.resize(width, height)

    def paintGL(self) -> None:
        from OpenGL import GL

        dt = 1.0 / 60.0
        if self._elapsed.isValid():
            elapsed_ms = self._elapsed.restart()
            if elapsed_ms > 0:
                dt = min(elapsed_ms / 1000.0, 1.0 / 12.0)

        if self.is_playing:
            self.preview_time_seconds = min(self.duration_seconds, self.preview_time_seconds + dt)
            self.engine.update(dt)
            self.preview_time_changed.emit(self.preview_time_seconds)
            if self.preview_time_seconds >= self.duration_seconds:
                self.is_playing = False
                self.playback_state_changed.emit(False)

        width = max(1, self.width())
        height = max(1, self.height())
        GL.glViewport(0, 0, width, height)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        self._zoom = zoom_at_time(self.engine.preset, self.preview_time_seconds, self.duration_seconds)
        self._rotation_degrees = rotation_at_time(
            self.engine.preset,
            self.preview_time_seconds,
            self.duration_seconds,
        )
        if self._background_texture:
            self._draw_background()

        self.engine.render(identity_matrix())

    def cleanup(self) -> None:
        if self.context() is None or not self.isValid():
            return
        self.makeCurrent()
        delete_texture(self._background_texture)
        self._background_texture = 0
        self.doneCurrent()

    def _upload_background_texture(self) -> None:
        if self._image_rgb is None:
            return
        delete_texture(self._background_texture)
        self._background_texture = create_texture_from_rgb(np.flipud(self._image_rgb))

    def _create_background_quad(self) -> None:
        from OpenGL import GL

        quad = np.array(
            [
                [-1.0, -1.0, 0.0, 0.0],
                [1.0, -1.0, 1.0, 0.0],
                [-1.0, 1.0, 0.0, 1.0],
                [1.0, 1.0, 1.0, 1.0],
            ],
            dtype=np.float32,
        )
        self._quad_vao = _gl_handle(GL.glGenVertexArrays(1))
        self._quad_vbo = _gl_handle(GL.glGenBuffers(1))
        GL.glBindVertexArray(self._quad_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._quad_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, quad.nbytes, quad, GL.GL_STATIC_DRAW)
        stride = 4 * 4
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, False, stride, ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, False, stride, ctypes.c_void_p(2 * 4))
        GL.glBindVertexArray(0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def _draw_background(self) -> None:
        from OpenGL import GL

        GL.glUseProgram(self._background_program)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._background_texture)
        GL.glUniform1i(GL.glGetUniformLocation(self._background_program, "u_image"), 0)
        GL.glUniform1f(GL.glGetUniformLocation(self._background_program, "u_zoom"), self._zoom)
        GL.glUniform1f(
            GL.glGetUniformLocation(self._background_program, "u_rotation_degrees"),
            self._rotation_degrees,
        )
        image_width, image_height = self.current_image_size or (1, 1)
        GL.glUniform2f(
            GL.glGetUniformLocation(self._background_program, "u_image_size"),
            float(image_width),
            float(image_height),
        )
        GL.glUniform2f(
            GL.glGetUniformLocation(self._background_program, "u_canvas_size"),
            float(max(1, self.width())),
            float(max(1, self.height())),
        )
        GL.glBindVertexArray(self._quad_vao)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        GL.glBindVertexArray(0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glUseProgram(0)
