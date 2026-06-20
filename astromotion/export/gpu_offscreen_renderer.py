"""GPU-backed offscreen renderer for export."""

from __future__ import annotations

import ctypes
from pathlib import Path

import numpy as np
from PySide6.QtGui import QGuiApplication, QOffscreenSurface, QOpenGLContext, QSurfaceFormat
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat

from astromotion.engine.camera import identity_matrix
from astromotion.engine.camera_motion import rotation_at_time, zoom_at_time
from astromotion.engine.particle_engine import ParticleEngine, _gl_handle
from astromotion.engine.shader_program import compile_program, read_shader
from astromotion.media.image_loader import fit_image_to_canvas, load_image_rgb
from astromotion.media.texture_loader import create_texture_from_rgb, delete_texture


class GpuRendererUnavailable(RuntimeError):
    pass


class GpuOffscreenRenderer:
    """Render export frames with OpenGL into an offscreen framebuffer."""

    def __init__(
        self,
        width: int,
        height: int,
        preset: dict,
        image_path: str | Path | None = None,
        duration_seconds: float = 10.0,
        seed: int | None = 1234,
    ) -> None:
        if QGuiApplication.instance() is None:
            raise GpuRendererUnavailable("GPU renderer requires an active Qt application.")

        self.width = int(width) - (int(width) % 2)
        self.height = int(height) - (int(height) % 2)
        self.duration_seconds = max(0.001, float(duration_seconds))
        self.background = self._load_background(image_path)

        self.surface: QOffscreenSurface | None = None
        self.context: QOpenGLContext | None = None
        self.fbo: QOpenGLFramebufferObject | None = None
        self.background_program = 0
        self.quad_vao = 0
        self.quad_vbo = 0
        self.background_texture = 0

        max_particles = max(1, int(preset.get("particle_count", 20_000)))
        self.engine = ParticleEngine(
            max_particles=max_particles,
            preset=preset,
            viewport_size=(self.width, self.height),
            gpu_mode="cpu",
            seed=seed,
        )

        self._initialize_context()
        self._initialize_gl_resources()

    def render_frame(self, dt: float) -> np.ndarray:
        from OpenGL import GL

        if self.context is None or self.surface is None or self.fbo is None:
            raise GpuRendererUnavailable("GPU renderer is not initialized.")
        if not self.context.makeCurrent(self.surface):
            raise GpuRendererUnavailable("Could not activate GPU renderer context.")

        zoom = zoom_at_time(self.engine.preset, self.engine.time_seconds, self.duration_seconds)
        rotation_degrees = rotation_at_time(
            self.engine.preset,
            self.engine.time_seconds,
            self.duration_seconds,
        )
        self.engine.update(dt)

        if not self.fbo.bind():
            raise GpuRendererUnavailable("Could not bind GPU renderer framebuffer.")
        GL.glViewport(0, 0, self.width, self.height)
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        self._draw_background(zoom, rotation_degrees)
        self.engine.render(identity_matrix())

        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
        pixels = GL.glReadPixels(0, 0, self.width, self.height, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        self.fbo.release()
        frame = np.frombuffer(pixels, dtype=np.uint8).reshape((self.height, self.width, 3))
        return np.flipud(frame).copy()

    def close(self) -> None:
        if self.context is not None and self.surface is not None:
            self.context.makeCurrent(self.surface)
            delete_texture(self.background_texture)
            self.background_texture = 0
            self.context.doneCurrent()
        self.fbo = None
        self.context = None
        if self.surface is not None:
            self.surface.destroy()
            self.surface = None

    def _initialize_context(self) -> None:
        fmt = QSurfaceFormat()
        fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)

        self.context = QOpenGLContext()
        self.context.setFormat(fmt)
        if not self.context.create():
            raise GpuRendererUnavailable("Could not create offscreen OpenGL context.")

        self.surface = QOffscreenSurface()
        self.surface.setFormat(self.context.format())
        self.surface.create()
        if not self.surface.isValid():
            raise GpuRendererUnavailable("Could not create offscreen OpenGL surface.")
        if not self.context.makeCurrent(self.surface):
            raise GpuRendererUnavailable("Could not make offscreen OpenGL context current.")

    def _initialize_gl_resources(self) -> None:
        from OpenGL import GL

        self.background_program = compile_program(
            read_shader("fullscreen_image.vert"),
            read_shader("fullscreen_image.frag"),
        )
        self._create_background_quad()
        self.background_texture = create_texture_from_rgb(np.flipud(self.background))

        fbo_format = QOpenGLFramebufferObjectFormat()
        fbo_format.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
        self.fbo = QOpenGLFramebufferObject(self.width, self.height, fbo_format)
        if not self.fbo.isValid():
            raise GpuRendererUnavailable("Could not create offscreen framebuffer.")

        GL.glEnable(GL.GL_PROGRAM_POINT_SIZE)
        self.engine.initialize_gl()

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
        self.quad_vao = _gl_handle(GL.glGenVertexArrays(1))
        self.quad_vbo = _gl_handle(GL.glGenBuffers(1))
        GL.glBindVertexArray(self.quad_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, quad.nbytes, quad, GL.GL_STATIC_DRAW)
        stride = 4 * 4
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, False, stride, ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, False, stride, ctypes.c_void_p(2 * 4))
        GL.glBindVertexArray(0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def _draw_background(self, zoom: float, rotation_degrees: float) -> None:
        from OpenGL import GL

        GL.glUseProgram(self.background_program)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.background_texture)
        GL.glUniform1i(GL.glGetUniformLocation(self.background_program, "u_image"), 0)
        GL.glUniform1f(GL.glGetUniformLocation(self.background_program, "u_zoom"), float(zoom))
        GL.glUniform1f(
            GL.glGetUniformLocation(self.background_program, "u_rotation_degrees"),
            float(rotation_degrees),
        )
        GL.glUniform2f(
            GL.glGetUniformLocation(self.background_program, "u_image_size"),
            float(self.width),
            float(self.height),
        )
        GL.glUniform2f(
            GL.glGetUniformLocation(self.background_program, "u_canvas_size"),
            float(self.width),
            float(self.height),
        )
        GL.glBindVertexArray(self.quad_vao)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        GL.glBindVertexArray(0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glUseProgram(0)

    def _load_background(self, image_path: str | Path | None) -> np.ndarray:
        if image_path:
            image = load_image_rgb(image_path)
            return fit_image_to_canvas(image, self.width, self.height)
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)
