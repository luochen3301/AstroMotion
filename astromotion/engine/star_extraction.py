"""Extract point-like stars from imported deep-sky images."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class ExtractedStarField:
    """Compact, renderer-neutral representation of detected source stars."""

    source_size: tuple[int, int]
    xy: np.ndarray
    colors: np.ndarray
    intensity: np.ndarray
    radius: np.ndarray
    score: np.ndarray

    @property
    def count(self) -> int:
        return int(self.xy.shape[0])

    def limited(self, max_count: int) -> "ExtractedStarField":
        count = max(0, min(int(max_count), self.count))
        return ExtractedStarField(
            source_size=self.source_size,
            xy=self.xy[:count].copy(),
            colors=self.colors[:count].copy(),
            intensity=self.intensity[:count].copy(),
            radius=self.radius[:count].copy(),
            score=self.score[:count].copy(),
        )


def empty_star_field(source_size: tuple[int, int] = (0, 0)) -> ExtractedStarField:
    return ExtractedStarField(
        source_size=(int(source_size[0]), int(source_size[1])),
        xy=np.empty((0, 2), dtype=np.float32),
        colors=np.empty((0, 3), dtype=np.float32),
        intensity=np.empty((0,), dtype=np.float32),
        radius=np.empty((0,), dtype=np.float32),
        score=np.empty((0,), dtype=np.float32),
    )


def extract_star_field(
    image_rgb: np.ndarray,
    sensitivity: float = 0.55,
    max_stars: int = 80_000,
    max_analysis_pixels: int = 2_000_000,
) -> ExtractedStarField:
    """Detect compact stars and return source-image normalized coordinates.

    The extractor favors local contrast over absolute brightness so stars can be
    found in dim photos while broad nebula clouds are filtered out.
    """

    image = np.asarray(image_rgb)
    if image.size == 0 or image.ndim < 2:
        return empty_star_field()

    source_height, source_width = image.shape[:2]
    source_size = (int(source_width), int(source_height))
    if source_width <= 0 or source_height <= 0:
        return empty_star_field(source_size)

    analysis, scale = _prepare_analysis_image(image, max_analysis_pixels=max_analysis_pixels)
    img = _as_float_rgb(analysis)
    if img.size == 0:
        return empty_star_field(source_size)

    luminance = img @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    background = _background_luminance(luminance)
    contrast = np.clip(luminance - background, 0.0, 1.0)
    if contrast.size == 0 or float(contrast.max(initial=0.0)) <= 0.0:
        return empty_star_field(source_size)

    sensitivity = float(np.clip(sensitivity, 0.0, 1.0))
    maxima = _local_maxima(luminance)
    contrast_threshold = _contrast_threshold(contrast, sensitivity)
    bright_threshold = float(np.quantile(luminance, 0.78 - sensitivity * 0.16))
    mask = maxima & (contrast >= contrast_threshold) & (luminance >= bright_threshold)

    yx = np.argwhere(mask)
    if yx.size == 0:
        return empty_star_field(source_size)

    y = yx[:, 0]
    x = yx[:, 1]
    score = contrast[y, x] * 0.78 + luminance[y, x] * 0.22
    limit = min(int(max_stars), yx.shape[0])
    if yx.shape[0] > limit:
        top = np.argpartition(score, -limit)[-limit:]
        yx = yx[top]
        score = score[top]

    order = np.argsort(score)[::-1]
    yx = yx[order]
    score = score[order].astype(np.float32)

    colors = _patch_mean_colors(img, yx)
    radius = _estimate_star_radius(contrast, yx, scale=scale)
    intensity = _normalize_intensity(score)

    height, width = img.shape[:2]
    xy = np.column_stack(
        (
            (yx[:, 1].astype(np.float32) + 0.5) / max(1.0, float(width)),
            (yx[:, 0].astype(np.float32) + 0.5) / max(1.0, float(height)),
        )
    ).astype(np.float32)
    xy = np.clip(xy, 0.0, 1.0)

    return ExtractedStarField(
        source_size=source_size,
        xy=xy,
        colors=colors.astype(np.float32),
        intensity=intensity.astype(np.float32),
        radius=radius.astype(np.float32),
        score=score,
    )


def _prepare_analysis_image(
    image_rgb: np.ndarray,
    max_analysis_pixels: int,
) -> tuple[np.ndarray, float]:
    height, width = image_rgb.shape[:2]
    pixels = height * width
    if pixels <= max_analysis_pixels:
        return image_rgb, 1.0

    scale = (max_analysis_pixels / float(pixels)) ** 0.5
    target_width = max(1, int(round(width * scale)))
    target_height = max(1, int(round(height * scale)))
    try:
        import cv2

        resized = cv2.resize(image_rgb, (target_width, target_height), interpolation=cv2.INTER_AREA)
        return resized, scale
    except ImportError:
        step = max(1, int(round(1.0 / max(scale, 1e-6))))
        sampled = image_rgb[::step, ::step].copy()
        return sampled, 1.0 / float(step)


def _as_float_rgb(image_rgb: np.ndarray) -> np.ndarray:
    img = np.asarray(image_rgb, dtype=np.float32)
    if img.ndim == 2:
        img = np.repeat(img[:, :, None], 3, axis=2)
    if img.shape[-1] > 3:
        img = img[:, :, :3]
    if img.max(initial=0.0) > 1.0:
        img /= 255.0
    return np.clip(img, 0.0, 1.0)


def _background_luminance(luminance: np.ndarray) -> np.ndarray:
    try:
        import cv2

        sigma = max(1.2, min(luminance.shape[:2]) / 160.0)
        return cv2.GaussianBlur(luminance.astype(np.float32), (0, 0), sigmaX=sigma, sigmaY=sigma)
    except ImportError:
        return _box_blur(luminance, radius=5)


def _contrast_threshold(contrast: np.ndarray, sensitivity: float) -> float:
    nonzero = contrast[contrast > 1e-6]
    if nonzero.size == 0:
        return 1.0
    q = 0.992 - sensitivity * 0.06
    quantile_threshold = float(np.quantile(nonzero, np.clip(q, 0.90, 0.995)))
    median = float(np.median(nonzero))
    mad = float(np.median(np.abs(nonzero - median)))
    noise_threshold = median + (3.5 - sensitivity * 1.8) * max(mad, 0.002)
    absolute_floor = 0.018 - sensitivity * 0.006
    return max(min(quantile_threshold, noise_threshold), absolute_floor)


def _local_maxima(luminance: np.ndarray) -> np.ndarray:
    try:
        import cv2

        dilated = cv2.dilate(luminance.astype(np.float32), np.ones((3, 3), dtype=np.uint8))
        return luminance >= dilated - 1e-6
    except ImportError:
        padded = np.pad(luminance, 1, mode="edge")
        maxima = np.ones_like(luminance, dtype=bool)
        for dy in range(3):
            for dx in range(3):
                if dy == 1 and dx == 1:
                    continue
                maxima &= luminance >= padded[dy : dy + luminance.shape[0], dx : dx + luminance.shape[1]]
        return maxima


def _patch_mean_colors(img: np.ndarray, yx: np.ndarray) -> np.ndarray:
    colors = []
    height, width = img.shape[:2]
    for y, x in yx:
        y0 = max(0, int(y) - 1)
        y1 = min(height, int(y) + 2)
        x0 = max(0, int(x) - 1)
        x1 = min(width, int(x) + 2)
        patch = img[y0:y1, x0:x1, :3]
        center = img[int(y), int(x), :3]
        colors.append(center * 0.7 + patch.reshape(-1, 3).mean(axis=0) * 0.3)
    return np.asarray(colors, dtype=np.float32)


def _estimate_star_radius(contrast: np.ndarray, yx: np.ndarray, scale: float) -> np.ndarray:
    radii = []
    height, width = contrast.shape[:2]
    for y, x in yx:
        y0 = max(0, int(y) - 2)
        y1 = min(height, int(y) + 3)
        x0 = max(0, int(x) - 2)
        x1 = min(width, int(x) + 3)
        patch = contrast[y0:y1, x0:x1]
        center = float(contrast[int(y), int(x)])
        if center <= 0.0:
            radii.append(1.0)
            continue
        area = int(np.count_nonzero(patch >= center * 0.35))
        radius = max(0.8, (area / np.pi) ** 0.5)
        radii.append(radius / max(scale, 1e-6))
    return np.clip(np.asarray(radii, dtype=np.float32), 0.8, 6.0)


def _normalize_intensity(score: np.ndarray) -> np.ndarray:
    if score.size == 0:
        return score.astype(np.float32)
    low = float(np.quantile(score, 0.08))
    high = float(np.quantile(score, 0.98))
    if high <= low + 1e-6:
        return np.ones_like(score, dtype=np.float32)
    normalized = (score - low) / (high - low)
    return np.clip(normalized, 0.12, 1.0).astype(np.float32)


def _box_blur(image: np.ndarray, radius: int) -> np.ndarray:
    padded = np.pad(image, radius, mode="reflect")
    out = np.zeros_like(image, dtype=np.float32)
    area = float((radius * 2 + 1) ** 2)
    for dy in range(radius * 2 + 1):
        for dx in range(radius * 2 + 1):
            out += padded[dy : dy + image.shape[0], dx : dx + image.shape[1]]
    return out / area
