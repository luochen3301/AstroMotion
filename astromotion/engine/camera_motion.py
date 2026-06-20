"""Time-based camera motion helpers shared by preview and export."""

from __future__ import annotations

import math


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * (3.0 - 2.0 * t)


def zoom_at_time(preset: dict, time_seconds: float, duration_seconds: float = 10.0) -> float:
    start = float(preset.get("zoom_start", 1.0))
    end = float(preset.get("zoom_end", start))
    speed = max(0.05, float(preset.get("zoom_speed", 1.0)))
    duration = max(0.001, float(duration_seconds))
    progress = max(0.0, min((float(time_seconds) / duration) * speed, 1.0))
    eased = smoothstep(progress)
    return start + (end - start) * eased


def rotation_at_time(preset: dict, time_seconds: float, duration_seconds: float = 10.0) -> float:
    end = float(preset.get("rotation_degrees", 0.0))
    speed = max(0.05, float(preset.get("zoom_speed", 1.0)))
    duration = max(0.001, float(duration_seconds))
    progress = max(0.0, min((float(time_seconds) / duration) * speed, 1.0))
    return end * smoothstep(progress)


def rotation_safe_zoom(
    zoom: float,
    rotation_degrees: float,
    canvas_size: tuple[int | float, int | float],
) -> float:
    """Return the minimum background zoom that hides rotation-exposed corners."""

    base_zoom = max(0.001, float(zoom))
    width, height = canvas_size
    aspect = max(float(width), 1.0) / max(float(height), 1.0)
    aspect_factor = max(aspect, 1.0 / max(aspect, 1e-6))
    angle = math.radians(float(rotation_degrees))
    required = abs(math.cos(angle)) + abs(math.sin(angle)) * aspect_factor
    return max(base_zoom, required)
