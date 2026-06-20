"""Offline frame renderer.

The first MVP renderer is CPU/Numpy based so it can run safely inside a QThread
without fighting platform-specific OpenGL context ownership. It shares the exact
ParticleEngine buffers and preset data with the live OpenGL preview, and is kept
behind this class so a future FBO renderer can replace it without touching
RenderWorker.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from astromotion.engine.camera_motion import rotation_at_time, zoom_at_time
from astromotion.engine.particle_engine import ParticleEngine, project_positions
from astromotion.media.image_loader import fit_image_to_canvas, load_image_rgb


class OffscreenRenderer:
    def __init__(
        self,
        width: int,
        height: int,
        preset: dict,
        image_path: str | Path | None = None,
        duration_seconds: float = 10.0,
        seed: int | None = 1234,
    ) -> None:
        self.width = int(width) - (int(width) % 2)
        self.height = int(height) - (int(height) % 2)
        max_particles = max(1, int(preset.get("particle_count", 20_000)))
        self.engine = ParticleEngine(
            max_particles=max_particles,
            preset=preset,
            viewport_size=(self.width, self.height),
            gpu_mode="cpu",
            seed=seed,
        )
        self.duration_seconds = max(0.001, float(duration_seconds))
        self.background = self._load_background(image_path)

    def render_frame(self, dt: float) -> np.ndarray:
        zoom = zoom_at_time(self.engine.preset, self.engine.time_seconds, self.duration_seconds)
        rotation_degrees = rotation_at_time(
            self.engine.preset,
            self.engine.time_seconds,
            self.duration_seconds,
        )
        self.engine.update(dt)
        snap = self.engine.snapshot()
        count = int(snap["count"])
        frame = self._transform_background(zoom, rotation_degrees).astype(np.float32)
        if count <= 0:
            return frame.astype(np.uint8)

        preset = snap["preset"]
        positions = project_positions(snap["positions"], preset)
        previous_positions = project_positions(snap["previous_positions"], preset)
        colors = snap["colors"]
        sizes = snap["sizes"]

        glow = float(preset.get("glow", 1.0))
        brightness = float(preset.get("brightness", 1.0))
        trail_length = float(preset.get("trail_length", preset.get("motion_blur", 0.0)))
        accum = np.zeros_like(frame, dtype=np.float32)

        if trail_length > 0.001:
            self._draw_trails(accum, previous_positions, positions, colors, trail_length, brightness)
        self._splat_star_points(accum, positions, colors, sizes, brightness)

        try:
            import cv2

            kernel = max(3, int(round(3 + glow * 4)))
            if kernel % 2 == 0:
                kernel += 1
            halo = cv2.GaussianBlur(accum, (kernel, kernel), sigmaX=glow * 1.35)
        except ImportError:
            halo = accum

        frame += accum * 0.7 + halo * glow
        return np.clip(frame, 0.0, 255.0).astype(np.uint8)

    def _load_background(self, image_path: str | Path | None) -> np.ndarray:
        if image_path:
            image = load_image_rgb(image_path)
            return fit_image_to_canvas(image, self.width, self.height)
        return self._generated_background()

    def _generated_background(self) -> np.ndarray:
        rng = np.random.default_rng(42)
        y = np.linspace(0.0, 1.0, self.height, dtype=np.float32)[:, None]
        x = np.linspace(0.0, 1.0, self.width, dtype=np.float32)[None, :]
        bg = np.dstack(
            [
                5.0 + 12.0 * x + 10.0 * y,
                7.0 + 7.0 * x + 14.0 * y,
                16.0 + 26.0 * (1.0 - x) + 8.0 * y,
            ]
        )
        star_count = max(300, (self.width * self.height) // 4500)
        px = rng.integers(0, self.width, star_count)
        py = rng.integers(0, self.height, star_count)
        bg[py, px] = rng.uniform(120, 255, size=(star_count, 3))
        return np.clip(bg, 0, 255).astype(np.uint8)

    def _zoom_background(self, zoom: float) -> np.ndarray:
        return self._transform_background(zoom, 0.0)

    def _transform_background(self, zoom: float, rotation_degrees: float = 0.0) -> np.ndarray:
        zoom = max(0.1, float(zoom))
        rotation_degrees = float(rotation_degrees)
        if abs(zoom - 1.0) < 0.001 and abs(rotation_degrees) < 0.001:
            return self.background.copy()

        try:
            import cv2
        except ImportError:
            return self.background.copy()

        center_x = (self.width - 1) * 0.5
        center_y = (self.height - 1) * 0.5
        inv_zoom = 1.0 / zoom
        angle = np.deg2rad(rotation_degrees)
        cos_a = float(np.cos(angle))
        sin_a = float(np.sin(angle))
        matrix = np.array(
            [
                [
                    cos_a * inv_zoom,
                    sin_a * inv_zoom,
                    center_x - (cos_a * inv_zoom * center_x + sin_a * inv_zoom * center_y),
                ],
                [
                    -sin_a * inv_zoom,
                    cos_a * inv_zoom,
                    center_y - (-sin_a * inv_zoom * center_x + cos_a * inv_zoom * center_y),
                ],
            ],
            dtype=np.float32,
        )
        return cv2.warpAffine(
            self.background,
            matrix,
            (self.width, self.height),
            flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def _draw_trails(
        self,
        accum: np.ndarray,
        previous_positions: np.ndarray,
        positions: np.ndarray,
        colors: np.ndarray,
        trail_length: float,
        brightness: float,
    ) -> None:
        try:
            import cv2
        except ImportError:
            return

        start_x, start_y, start_mask = self._to_pixels(previous_positions, colors)
        end_x, end_y, end_mask = self._to_pixels(positions, colors)
        mask = start_mask & end_mask
        if not np.any(mask):
            return

        indices = np.flatnonzero(mask)
        # Drawing all 100k lines with cv2 is expensive. Deterministic thinning
        # keeps export practical while preserving the visual field density.
        stride = max(1, indices.size // 24_000)
        for i in indices[::stride]:
            alpha = float(colors[i, 3]) * float(trail_length)
            if alpha <= 0.002:
                continue
            rgb = tuple(float(v) for v in (colors[i, :3] * 255.0 * alpha * brightness))
            cv2.line(
                accum,
                (int(start_x[i]), int(start_y[i])),
                (int(end_x[i]), int(end_y[i])),
                rgb,
                1,
                cv2.LINE_AA,
            )

    def _splat_star_points(
        self,
        accum: np.ndarray,
        positions: np.ndarray,
        colors: np.ndarray,
        sizes: np.ndarray,
        weight: float,
    ) -> None:
        px, py, mask = self._to_pixels(positions, colors)
        if not np.any(mask):
            return

        px = px[mask]
        py = py[mask]
        alpha = colors[mask, 3:4]
        rgb = colors[mask, :3] * 255.0
        core_boost = np.clip(sizes[mask, None] / 2.0, 0.55, 1.8)
        contribution = rgb * alpha * core_boost * float(weight)
        for channel in range(3):
            np.add.at(accum[:, :, channel], (py, px), contribution[:, channel])
        self._add_star_cross(accum, px, py, contribution * 0.28)

    def _add_star_cross(self, accum: np.ndarray, px: np.ndarray, py: np.ndarray, contribution: np.ndarray) -> None:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sx = px + dx
            sy = py + dy
            mask = (sx >= 0) & (sx < self.width) & (sy >= 0) & (sy < self.height)
            if not np.any(mask):
                continue
            for channel in range(3):
                np.add.at(accum[:, :, channel], (sy[mask], sx[mask]), contribution[mask, channel])

    def _to_pixels(self, positions: np.ndarray, colors: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        px = ((positions[:, 0] * 0.5 + 0.5) * (self.width - 1)).astype(np.int32)
        py = ((1.0 - (positions[:, 1] * 0.5 + 0.5)) * (self.height - 1)).astype(np.int32)
        mask = (px >= 0) & (px < self.width) & (py >= 0) & (py < self.height) & (colors[:, 3] > 0.001)
        return px, py, mask
