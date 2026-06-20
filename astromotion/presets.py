"""Particle preset definitions for AstroMotion."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PRESET_DEFAULTS: dict[str, Any] = {
    "particle_count": 20_000,
    "emitter": "depth_starfield",
    "speed": 0.9,
    "size": 1.35,
    "glow": 0.85,
    "brightness": 1.75,
    "color_intensity": 1.15,
    "opacity": 0.48,
    "turbulence": 0.05,
    "lifetime": 7.0,
    "motion_blur": 0.24,
    "color_mode": "theme",
    "star_detection_sensitivity": 0.55,
    "source_star_strength": 1.0,
    "theme_colors": [
        (0.96, 0.98, 1.0, 1.0),
        (0.84, 0.91, 1.0, 1.0),
        (0.72, 0.82, 1.0, 1.0),
        (0.90, 0.94, 1.0, 1.0),
        (1.0, 0.96, 0.86, 1.0),
        (1.0, 0.90, 0.72, 1.0),
        (0.92, 0.88, 1.0, 1.0),
        (1.0, 0.99, 0.94, 1.0),
    ],
    "zoom_start": 1.0,
    "zoom_end": 1.12,
    "zoom_speed": 1.0,
    "rotation_degrees": 0.0,
    "trail_length": 0.16,
    "depth_range": 3.2,
    "depth_strength": 0.9,
    "focal_length": 1.18,
    "softness": 0.5,
}


PRESETS: dict[str, dict[str, Any]] = {
    "Deep Space Flythrough": {
        **PRESET_DEFAULTS,
        "name": "Deep Space Flythrough",
        "display_name": "Deep Space Flythrough",
    },
    "Cinematic Star Drift": {
        **PRESET_DEFAULTS,
        "name": "Cinematic Star Drift",
        "display_name": "Cinematic Star Drift",
        "particle_count": 12_000,
        "speed": 0.38,
        "size": 1.55,
        "glow": 0.75,
        "brightness": 1.9,
        "color_intensity": 1.05,
        "opacity": 0.44,
        "turbulence": 0.025,
        "lifetime": 12.0,
        "motion_blur": 0.16,
        "zoom_end": 1.08,
        "zoom_speed": 0.55,
        "trail_length": 0.20,
        "depth_range": 4.2,
        "depth_strength": 0.78,
        "focal_length": 1.08,
    },
    "Nebula Close Pass": {
        **PRESET_DEFAULTS,
        "name": "Nebula Close Pass",
        "display_name": "Nebula Close Pass",
        "particle_count": 9_779,
        "speed": 0.07,
        "size": 4.00,
        "glow": 0.85,
        "brightness": 1.75,
        "color_intensity": 4.05,
        "opacity": 0.48,
        "turbulence": 0.05,
        "zoom_start": 1.0,
        "zoom_end": 1.40,
        "zoom_speed": 1.0,
        "rotation_degrees": 4.80,
        "trail_length": 0.16,
        "depth_strength": 0.90,
    },
    "Rotating Nebula Push-in": {
        **PRESET_DEFAULTS,
        "name": "Rotating Nebula Push-in",
        "display_name": "Rotating Nebula Push-in",
        "particle_count": 9_000,
        "speed": 0.05,
        "size": 1.10,
        "glow": 0.85,
        "brightness": 1.75,
        "color_intensity": 4.05,
        "opacity": 0.48,
        "turbulence": 0.05,
        "zoom_start": 1.0,
        "zoom_end": 1.28,
        "zoom_speed": 1.0,
        "rotation_degrees": 4.0,
        "trail_length": 0.16,
        "depth_strength": 0.90,
    },
}


def preset_names() -> list[str]:
    return list(PRESETS)


def default_preset_name() -> str:
    return "Nebula Close Pass"


def get_preset(name: str | None = None) -> dict[str, Any]:
    """Return a deep copy so caller-side mutation never changes global presets."""

    if name is None:
        name = default_preset_name()
    if name not in PRESETS:
        raise KeyError(f"Unknown preset: {name}")
    return deepcopy(PRESETS[name])


def normalize_preset(preset: dict[str, Any]) -> dict[str, Any]:
    """Merge a partial preset dict with defaults and clamp risky values."""

    merged = deepcopy(PRESET_DEFAULTS)
    merged.update(deepcopy(preset))
    merged["particle_count"] = int(max(1, merged["particle_count"]))
    merged["speed"] = float(max(0.0, merged["speed"]))
    merged["size"] = float(max(0.1, merged["size"]))
    merged["glow"] = float(max(0.0, merged["glow"]))
    merged["brightness"] = float(min(5.0, max(0.0, merged["brightness"])))
    merged["color_intensity"] = float(min(5.0, max(0.0, merged["color_intensity"])))
    merged["opacity"] = float(min(1.0, max(0.0, merged["opacity"])))
    merged["turbulence"] = float(max(0.0, merged["turbulence"]))
    merged["lifetime"] = float(max(0.05, merged["lifetime"]))
    merged["motion_blur"] = float(min(1.0, max(0.0, merged["motion_blur"])))
    merged["star_detection_sensitivity"] = float(
        min(1.0, max(0.0, merged["star_detection_sensitivity"]))
    )
    merged["source_star_strength"] = float(min(2.0, max(0.0, merged["source_star_strength"])))
    merged["zoom_start"] = float(max(0.1, merged["zoom_start"]))
    merged["zoom_end"] = float(max(0.1, merged["zoom_end"]))
    merged["zoom_speed"] = float(min(5.0, max(0.05, merged["zoom_speed"])))
    merged["rotation_degrees"] = float(min(20.0, max(-20.0, merged["rotation_degrees"])))
    merged["trail_length"] = float(min(2.0, max(0.0, merged["trail_length"])))
    merged["depth_range"] = float(max(0.2, merged["depth_range"]))
    merged["depth_strength"] = float(min(2.5, max(0.0, merged["depth_strength"])))
    merged["focal_length"] = float(max(0.2, merged["focal_length"]))
    return merged
