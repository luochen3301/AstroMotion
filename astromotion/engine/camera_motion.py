"""Time-based camera motion helpers shared by preview and export."""

from __future__ import annotations


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
