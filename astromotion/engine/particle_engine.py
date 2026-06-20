"""Particle engine for AstroMotion."""

from __future__ import annotations

import ctypes
import math
from typing import Any

import numpy as np

from astromotion.engine.camera import identity_matrix
from astromotion.engine.particle_types import (
    ParticleBuffers,
    create_empty_buffers,
    interleave_for_gpu,
    interleave_trails_for_gpu,
)
from astromotion.engine.shader_program import compile_compute_program, compile_program, read_shader
from astromotion.presets import get_preset, normalize_preset


def _gl_handle(value: Any) -> int:
    """Normalize PyOpenGL object ids to plain Python ints."""

    array = np.asarray(value)
    if array.shape:
        return int(array.reshape(-1)[0])
    return int(value)


def project_positions(positions: np.ndarray, preset: dict[str, Any]) -> np.ndarray:
    """Project world-space particle positions into normalized screen space."""

    positions = np.asarray(positions, dtype=np.float32)
    if positions.size == 0:
        return positions.reshape((-1, 3)).copy()

    projected = positions.copy()
    if preset.get("emitter") == "depth_starfield" or float(preset.get("depth_strength", 0.0)) > 0.0:
        focal = float(preset.get("focal_length", 1.0))
        depth_strength = float(preset.get("depth_strength", 1.0))
        z = np.maximum(projected[:, 2], 0.08)
        perspective = focal / z
        projected[:, 0:2] *= perspective[:, None] * depth_strength
        projected[:, 2] = 0.0
    return projected


class ParticleEngine:
    """Particle simulation and OpenGL rendering state."""

    def __init__(
        self,
        max_particles: int = 100_000,
        preset: str | dict[str, Any] | None = None,
        viewport_size: tuple[int, int] = (1920, 1080),
        gpu_mode: str = "compute",
        seed: int | None = None,
    ) -> None:
        self.max_particles = int(max_particles)
        self.viewport_size = tuple(viewport_size)
        self.gpu_mode = gpu_mode
        self.seed = 0 if seed is None else int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.buffers: ParticleBuffers = create_empty_buffers(self.max_particles)
        self.active_count = 0
        self.time_seconds = 0.0
        self._suppress_upload = False
        self.gpu_dirty = True

        self.preset = normalize_preset(get_preset() if preset is None else self._coerce_preset(preset))
        self._base_alpha = np.ones((self.max_particles,), dtype=np.float32)

        self.gl = None
        self.gl_initialized = False
        self.compute_available = False
        self.compute_program = 0
        self.render_program = 0
        self.trail_program = 0
        self.vao = 0
        self.vbo = 0
        self.trail_vao = 0
        self.trail_vbo = 0

        self.set_preset(self.preset)

    def _coerce_preset(self, preset: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(preset, str):
            return get_preset(preset)
        return dict(preset)

    def set_preset(self, preset: str | dict[str, Any]) -> None:
        self.preset = normalize_preset(self._coerce_preset(preset))
        self.active_count = min(int(self.preset["particle_count"]), self.max_particles)
        self._reset_simulation()
        self._mark_gpu_dirty()

    def update_params(self, params: dict[str, Any]) -> None:
        old_count = self.active_count
        old_emitter = self.preset.get("emitter")
        merged = dict(self.preset)
        merged.update(params)
        self.preset = normalize_preset(merged)
        self.active_count = min(int(self.preset["particle_count"]), self.max_particles)

        should_respawn_all = old_emitter != self.preset.get("emitter")
        if should_respawn_all:
            self._spawn(np.arange(self.active_count), initial=True)
        elif self.active_count != old_count:
            start = min(old_count, self.active_count)
            if self.active_count > start:
                self._spawn(np.arange(start, self.active_count), initial=True)

        if "theme_colors" in params or "color_intensity" in params or "opacity" in params:
            self._assign_colors(np.arange(self.active_count), refresh_opacity="opacity" in params)
            self._update_alpha()

        self.buffers.sizes[: self.active_count] = self._random_sizes(self.active_count)
        self._mark_gpu_dirty()

    def resize(self, width: int, height: int) -> None:
        self.viewport_size = (max(1, int(width)), max(1, int(height)))

    def seek(self, time_seconds: float, step_seconds: float = 1.0 / 60.0) -> None:
        """Deterministically rebuild the particle state at a preview time.

        This is designed for UI scrubbing. It resets the RNG and simulates from
        zero to the requested timestamp, so dragging the slider to the same time
        shows the same particle field every time.
        """

        target = max(0.0, float(time_seconds))
        step = max(1.0 / 120.0, min(1.0 / 15.0, float(step_seconds)))
        self._suppress_upload = True
        try:
            self._reset_simulation()
            remaining = target
            while remaining > 1e-9:
                dt = min(step, remaining)
                self.update(dt)
                remaining -= dt
        finally:
            self._suppress_upload = False
        self.time_seconds = target
        self._mark_gpu_dirty()

    def initialize_gl(self) -> None:
        """Create OpenGL objects. Must be called from an active GL context."""

        from OpenGL import GL

        self.gl = GL
        self.render_program = compile_program(read_shader("particles.vert"), read_shader("particles.frag"))
        self.trail_program = compile_program(read_shader("trail.vert"), read_shader("trail.frag"))
        self.vao = _gl_handle(GL.glGenVertexArrays(1))
        self.vbo = _gl_handle(GL.glGenBuffers(1))

        GL.glBindVertexArray(self.vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        stride = 16 * 4
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.max_particles * stride, None, GL.GL_DYNAMIC_DRAW)

        # position(0), color(1), life(2), size(3), velocity(4), previous_position(5)
        offsets = [0, 3 * 4, 7 * 4, 9 * 4, 10 * 4, 13 * 4]
        sizes = [3, 4, 2, 1, 3, 3]
        for index, size, offset in zip(range(6), sizes, offsets):
            GL.glEnableVertexAttribArray(index)
            GL.glVertexAttribPointer(index, size, GL.GL_FLOAT, False, stride, ctypes.c_void_p(offset))
        GL.glBindVertexArray(0)

        self.trail_vao = _gl_handle(GL.glGenVertexArrays(1))
        self.trail_vbo = _gl_handle(GL.glGenBuffers(1))
        GL.glBindVertexArray(self.trail_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.trail_vbo)
        trail_stride = 7 * 4
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.max_particles * 2 * trail_stride, None, GL.GL_DYNAMIC_DRAW)
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, False, trail_stride, ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 4, GL.GL_FLOAT, False, trail_stride, ctypes.c_void_p(3 * 4))
        GL.glBindVertexArray(0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        self.gl_initialized = True
        if self.gpu_mode == "compute":
            try:
                version = GL.glGetString(GL.GL_VERSION).decode("ascii", errors="ignore")
                self.compute_available = _gl_version_at_least(version, 4, 3)
                if self.compute_available:
                    self.compute_program = compile_compute_program(read_shader("particles_compute.glsl"))
            except Exception:
                self.compute_available = False
                self.compute_program = 0

        self.gpu_dirty = True
        self.flush_gpu_buffers()

    def update(self, dt: float) -> None:
        count = self.active_count
        if count <= 0:
            return

        dt = float(max(0.0, min(dt, 1.0 / 12.0)))
        self.time_seconds += dt

        life = self.buffers.life[:count]
        positions = self.buffers.positions[:count]
        velocities = self.buffers.velocities[:count]
        self.buffers.previous_positions[:count] = positions

        life[:, 0] += dt
        expired = life[:, 0] >= life[:, 1]
        emitter = self.preset.get("emitter", "fullscreen")

        turbulence = float(self.preset.get("turbulence", 0.0))
        if turbulence > 0.0:
            self._apply_turbulence(positions, velocities, dt, turbulence)

        positions += velocities * dt
        expired |= self._out_of_bounds(positions, emitter)

        if np.any(expired):
            self._spawn(np.flatnonzero(expired), initial=False)

        self._update_alpha()
        self._mark_gpu_dirty()

    def render(self, view_projection: np.ndarray | None = None) -> None:
        if not self.gl_initialized or self.gl is None or self.active_count <= 0:
            return

        self.flush_gpu_buffers()

        GL = self.gl
        matrix = identity_matrix() if view_projection is None else np.asarray(view_projection, dtype=np.float32)
        depth_strength = float(self.preset.get("depth_strength", 0.0))
        focal_length = float(self.preset.get("focal_length", 1.0))
        brightness = float(self.preset.get("brightness", 1.0))
        glow = float(self.preset["glow"])
        trail_length = float(self.preset.get("trail_length", 0.0))

        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE)
        GL.glDepthMask(False)

        if trail_length > 0.001 and self.trail_vao:
            GL.glUseProgram(self.trail_program)
            GL.glUniformMatrix4fv(
                GL.glGetUniformLocation(self.trail_program, "u_view_projection"),
                1,
                GL.GL_FALSE,
                matrix.T,
            )
            GL.glUniform1f(GL.glGetUniformLocation(self.trail_program, "u_depth_strength"), depth_strength)
            GL.glUniform1f(GL.glGetUniformLocation(self.trail_program, "u_focal_length"), focal_length)
            GL.glUniform1f(GL.glGetUniformLocation(self.trail_program, "u_trail_strength"), trail_length)
            GL.glUniform1f(
                GL.glGetUniformLocation(self.trail_program, "u_brightness"),
                brightness,
            )
            GL.glUniform1f(
                GL.glGetUniformLocation(self.trail_program, "u_color_intensity"),
                float(self.preset.get("color_intensity", 1.0)),
            )
            GL.glLineWidth(max(1.0, min(3.0, trail_length * 2.5)))
            GL.glBindVertexArray(self.trail_vao)
            GL.glDrawArrays(GL.GL_LINES, 0, self.active_count * 2)
            GL.glBindVertexArray(0)

        GL.glUseProgram(self.render_program)
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(self.render_program, "u_view_projection"),
            1,
            GL.GL_FALSE,
            matrix.T,
        )
        GL.glUniform1f(GL.glGetUniformLocation(self.render_program, "u_glow"), glow)
        GL.glUniform1f(
            GL.glGetUniformLocation(self.render_program, "u_brightness"),
            brightness,
        )
        GL.glUniform1f(
            GL.glGetUniformLocation(self.render_program, "u_motion_blur"),
            float(self.preset["motion_blur"]),
        )
        GL.glUniform1f(
            GL.glGetUniformLocation(self.render_program, "u_color_intensity"),
            float(self.preset.get("color_intensity", 1.0)),
        )
        GL.glUniform1f(GL.glGetUniformLocation(self.render_program, "u_depth_strength"), depth_strength)
        GL.glUniform1f(GL.glGetUniformLocation(self.render_program, "u_focal_length"), focal_length)
        GL.glBindVertexArray(self.vao)
        GL.glDrawArrays(GL.GL_POINTS, 0, self.active_count)
        GL.glBindVertexArray(0)
        GL.glDepthMask(True)
        GL.glUseProgram(0)

    def snapshot(self) -> dict[str, np.ndarray | int | dict[str, Any]]:
        return {
            "count": self.active_count,
            "positions": self.buffers.positions[: self.active_count],
            "previous_positions": self.buffers.previous_positions[: self.active_count],
            "velocities": self.buffers.velocities[: self.active_count],
            "colors": self.buffers.colors[: self.active_count],
            "life": self.buffers.life[: self.active_count],
            "sizes": self.buffers.sizes[: self.active_count],
            "preset": self.preset,
        }

    def _spawn(self, indices: np.ndarray, initial: bool) -> None:
        indices = np.asarray(indices, dtype=np.int64)
        if indices.size == 0:
            return

        emitter = self.preset.get("emitter", "fullscreen")
        if emitter == "depth_starfield":
            self._spawn_depth_starfield(indices)
        elif emitter == "center_depth":
            self._spawn_warp(indices)
        elif emitter == "left_edge":
            self._spawn_stellar_wind(indices)
        else:
            self._spawn_cosmic_dust(indices)

        lifetime = float(self.preset["lifetime"])
        max_life = self.rng.uniform(lifetime * 0.75, lifetime * 1.25, size=indices.size).astype(np.float32)
        current = self.rng.uniform(0.0, max_life, size=indices.size).astype(np.float32) if initial else 0.0
        self.buffers.life[indices, 0] = current
        self.buffers.life[indices, 1] = max_life
        self.buffers.sizes[indices] = self._random_sizes(indices.size)

        self._assign_colors(indices, refresh_opacity=True)
        self.buffers.previous_positions[indices] = self.buffers.positions[indices]

    def _reset_simulation(self) -> None:
        self.rng = np.random.default_rng(self.seed)
        self.time_seconds = 0.0
        self._spawn(np.arange(self.active_count), initial=True)

    def _spawn_depth_starfield(self, indices: np.ndarray) -> None:
        n = indices.size
        depth_range = float(self.preset.get("depth_range", 3.2))
        focal = float(self.preset.get("focal_length", 1.18))
        z = self.rng.uniform(0.45, depth_range, n).astype(np.float32)
        spread = (z / max(focal, 0.001)) * self.rng.uniform(0.18, 1.12, n).astype(np.float32)
        angle = self.rng.uniform(0.0, math.tau, n).astype(np.float32)
        self.buffers.positions[indices, 0] = np.cos(angle) * spread
        self.buffers.positions[indices, 1] = np.sin(angle) * spread
        self.buffers.positions[indices, 2] = z

        speed = float(self.preset["speed"])
        self.buffers.velocities[indices, 0] = self.rng.normal(0.0, 0.018 * speed, n)
        self.buffers.velocities[indices, 1] = self.rng.normal(0.0, 0.018 * speed, n)
        self.buffers.velocities[indices, 2] = -self.rng.uniform(speed * 0.32, speed * 1.05, n)

    def _spawn_cosmic_dust(self, indices: np.ndarray) -> None:
        n = indices.size
        self.buffers.positions[indices, 0] = self.rng.uniform(-1.0, 1.0, n)
        self.buffers.positions[indices, 1] = self.rng.uniform(-1.0, 1.0, n)
        self.buffers.positions[indices, 2] = self.rng.uniform(-0.25, 0.25, n)

        speed = float(self.preset["speed"])
        self.buffers.velocities[indices] = self.rng.normal(0.0, speed * 0.28, size=(n, 3)).astype(np.float32)
        self.buffers.velocities[indices, 2] *= 0.15

    def _spawn_warp(self, indices: np.ndarray) -> None:
        n = indices.size
        angle = self.rng.uniform(0.0, math.tau, n).astype(np.float32)
        radius = self.rng.uniform(0.0, 0.035, n).astype(np.float32)
        direction = np.column_stack((np.cos(angle), np.sin(angle))).astype(np.float32)

        self.buffers.positions[indices, 0:2] = direction * radius[:, None]
        self.buffers.positions[indices, 2] = self.rng.uniform(-1.0, -0.25, n)

        speed = float(self.preset["speed"])
        radial = self.rng.uniform(speed * 0.35, speed * 0.95, n).astype(np.float32)
        z_speed = self.rng.uniform(speed * 0.55, speed * 1.15, n).astype(np.float32)
        self.buffers.velocities[indices, 0:2] = direction * radial[:, None]
        self.buffers.velocities[indices, 2] = z_speed

    def _spawn_stellar_wind(self, indices: np.ndarray) -> None:
        n = indices.size
        self.buffers.positions[indices, 0] = self.rng.uniform(-1.18, -0.98, n)
        self.buffers.positions[indices, 1] = self.rng.uniform(-1.0, 1.0, n)
        self.buffers.positions[indices, 2] = self.rng.uniform(-0.15, 0.15, n)
        direction = np.asarray(self.preset.get("wind_direction", (1.0, 0.0, 0.0)), dtype=np.float32)
        direction /= max(float(np.linalg.norm(direction)), 1e-6)
        speed = float(self.preset["speed"])
        self.buffers.velocities[indices] = direction * self.rng.uniform(speed * 0.55, speed * 1.15, (n, 1))

    def _out_of_bounds(self, positions: np.ndarray, emitter: str) -> np.ndarray:
        if emitter == "depth_starfield":
            projected = project_positions(positions, self.preset)
            return (
                (positions[:, 2] <= 0.12)
                | (np.abs(projected[:, 0]) > 1.45)
                | (np.abs(projected[:, 1]) > 1.45)
            )
        if emitter == "center_depth":
            return (
                (np.abs(positions[:, 0]) > 1.55)
                | (np.abs(positions[:, 1]) > 1.55)
                | (positions[:, 2] > 1.25)
            )
        if emitter == "left_edge":
            return positions[:, 0] > 1.25
        return (np.abs(positions[:, 0]) > 1.18) | (np.abs(positions[:, 1]) > 1.18)

    def _random_sizes(self, count: int) -> np.ndarray:
        base = float(self.preset["size"])
        return self.rng.uniform(base * 0.55, base * 1.55, int(count)).astype(np.float32)

    def _assign_colors(self, indices: np.ndarray, refresh_opacity: bool) -> None:
        indices = np.asarray(indices, dtype=np.int64)
        if indices.size == 0:
            return

        colors = np.asarray(self.preset.get("theme_colors", []), dtype=np.float32)
        if colors.ndim != 2 or colors.shape[1] != 4 or colors.shape[0] == 0:
            colors = np.asarray([(0.92, 0.96, 1.0, 1.0)], dtype=np.float32)
        picked = colors[self.rng.integers(0, colors.shape[0], size=indices.size)].copy()
        if self.preset.get("emitter") == "depth_starfield":
            picked[:, :3] = self._vary_star_colors(picked[:, :3])
        self.buffers.colors[indices] = picked

        if refresh_opacity:
            opacity_jitter = self.rng.uniform(0.72, 1.1, size=indices.size).astype(np.float32)
            self._base_alpha[indices] = np.clip(float(self.preset["opacity"]) * opacity_jitter, 0.0, 1.0)

    def _vary_star_colors(self, rgb: np.ndarray) -> np.ndarray:
        count = int(rgb.shape[0])
        if count == 0:
            return rgb

        color_intensity = float(np.clip(self.preset.get("color_intensity", 1.0), 0.0, 5.0))
        varied = rgb.astype(np.float32, copy=True)
        temperature_scale = 0.35 + color_intensity * 0.65
        temperature = self.rng.normal(0.0, 0.045 * temperature_scale, size=(count, 1)).astype(np.float32)
        channel_jitter = self.rng.normal(1.0, 0.035, size=(count, 3)).astype(np.float32)
        brightness = self.rng.uniform(0.82, 1.18, size=(count, 1)).astype(np.float32)

        # Negative temperature makes a cooler blue-white point, positive warms
        # it slightly. The deltas are intentionally small to avoid rainbow noise.
        varied[:, 0:1] += temperature * 0.90
        varied[:, 1:2] += temperature * 0.32
        varied[:, 2:3] -= temperature * 0.70
        varied *= channel_jitter * brightness
        neutral = np.mean(varied, axis=1, keepdims=True)
        varied = neutral + (varied - neutral) * color_intensity
        return np.clip(varied, 0.0, 1.0).astype(np.float32)

    def _apply_turbulence(
        self,
        positions: np.ndarray,
        velocities: np.ndarray,
        dt: float,
        turbulence: float,
    ) -> None:
        t = self.time_seconds
        field_x = np.sin(positions[:, 1] * 7.7 + t * 0.61) + np.cos(positions[:, 2] * 5.1 - t * 0.37)
        field_y = np.cos(positions[:, 0] * 6.9 - t * 0.53) + np.sin(positions[:, 2] * 4.3 + t * 0.43)
        field_z = np.sin((positions[:, 0] + positions[:, 1]) * 3.1 + t * 0.19)
        wind = np.column_stack((field_x, field_y, field_z)).astype(np.float32)

        emitter = self.preset.get("emitter", "fullscreen")
        if emitter == "depth_starfield":
            wind[:, 2] *= 0.08
            multiplier = 0.045
        else:
            multiplier = 0.015 if emitter == "center_depth" else 0.08
        velocities += wind * (turbulence * multiplier * dt)

    def _update_alpha(self) -> None:
        count = self.active_count
        life = self.buffers.life[:count]
        age = np.divide(life[:, 0], life[:, 1], out=np.zeros(count, dtype=np.float32), where=life[:, 1] > 0)
        fade_in = np.clip(age / 0.10, 0.0, 1.0)
        fade_out = np.clip((1.0 - age) / 0.18, 0.0, 1.0)
        alpha = self._base_alpha[:count] * np.minimum(fade_in, fade_out)
        if self.preset.get("emitter") == "depth_starfield":
            z = np.maximum(self.buffers.positions[:count, 2], 0.12)
            depth_gain = np.clip(0.75 / z, 0.18, 1.85)
            alpha *= depth_gain
        self.buffers.colors[:count, 3] = np.clip(alpha, 0.0, 1.0).astype(np.float32)

    def _mark_gpu_dirty(self) -> None:
        if not self._suppress_upload:
            self.gpu_dirty = True

    def flush_gpu_buffers(self) -> None:
        """Upload CPU particle buffers while an OpenGL context is current."""

        if not self.gpu_dirty:
            return
        self._upload_gpu_buffers()
        if self.gl_initialized and self.gl is not None and self.active_count > 0:
            self.gpu_dirty = False

    def _upload_gpu_buffers(self) -> None:
        if self._suppress_upload or not self.gl_initialized or self.gl is None or self.active_count <= 0:
            return
        GL = self.gl
        packed = interleave_for_gpu(self.buffers, self.active_count)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, int(self.vbo))
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, packed.nbytes, packed)

        if self.trail_vbo:
            trails = interleave_trails_for_gpu(self.buffers, self.active_count)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, int(self.trail_vbo))
            GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, trails.nbytes, trails)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)


def _gl_version_at_least(version: str, major: int, minor: int) -> bool:
    head = version.split()[0]
    try:
        got_major, got_minor = head.split(".")[:2]
        return (int(got_major), int(got_minor)) >= (major, minor)
    except Exception:
        return False
