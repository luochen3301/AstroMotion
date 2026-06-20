"""Theme color extraction from imported nebula images."""

from __future__ import annotations

import numpy as np


NATURAL_STAR_COLORS: tuple[tuple[float, float, float, float], ...] = (
    (0.96, 0.98, 1.00, 1.0),  # neutral white
    (0.84, 0.91, 1.00, 1.0),  # blue white
    (0.72, 0.82, 1.00, 1.0),  # cool blue
    (0.90, 0.94, 1.00, 1.0),  # pale blue
    (1.00, 0.96, 0.86, 1.0),  # warm white
    (1.00, 0.90, 0.72, 1.0),  # soft amber
    (0.92, 0.88, 1.00, 1.0),  # faint violet
    (1.00, 0.99, 0.94, 1.0),  # creamy highlight
)


def sample_theme_colors(image_rgb: np.ndarray, count: int = 3) -> list[tuple[float, float, float, float]]:
    """Pick representative star colors from an RGB deep-sky image.

    The primary path samples point-like local maxima so broad nebula structures
    do not dominate particle tinting. It falls back to the older broad theme
    sampling when an image has too few detectable star points.
    """

    if image_rgb.size == 0:
        return [(0.62, 0.78, 1.0, 1.0), (0.92, 0.74, 1.0, 1.0), (1.0, 0.86, 0.58, 1.0)]

    sampling_image = _prepare_sampling_image(image_rgb)
    star_colors = sample_star_colors(sampling_image, count=count)
    if len(star_colors) >= count:
        return star_colors[:count]

    fallback = _sample_broad_theme_colors(sampling_image, count=count)
    return (star_colors + fallback)[:count]


def _prepare_sampling_image(image_rgb: np.ndarray, max_pixels: int = 2_000_000) -> np.ndarray:
    """Create a bounded analysis image for color sampling.

    Astro photos can be far larger than the preview canvas. Star-color sampling
    only needs representative chroma, so we downsample the analysis copy while
    leaving the imported original untouched for preview and export.
    """

    image = np.asarray(image_rgb)
    if image.size == 0 or image.ndim < 2:
        return image

    height, width = image.shape[:2]
    pixels = height * width
    if pixels <= max_pixels:
        return image

    scale = (max_pixels / float(pixels)) ** 0.5
    target_width = max(1, int(round(width * scale)))
    target_height = max(1, int(round(height * scale)))
    try:
        import cv2

        return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)
    except ImportError:
        step = max(1, int(round((pixels / max_pixels) ** 0.5)))
        return image[::step, ::step].copy()


def sample_star_colors(image_rgb: np.ndarray, count: int = 5) -> list[tuple[float, float, float, float]]:
    """Sample colors from point-like stars using local contrast filtering."""

    if image_rgb.size == 0:
        return []

    img = _as_float_rgb(image_rgb)
    luminance = img @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    local_mean = _box_blur(luminance, radius=3)
    contrast = luminance - local_mean
    if contrast.size == 0 or float(contrast.max()) <= 0.0:
        return []

    maxima = _local_maxima(luminance)
    bright_threshold = np.quantile(luminance, 0.82)
    contrast_threshold = max(float(np.quantile(contrast, 0.92)), 0.025)
    mask = maxima & (luminance >= bright_threshold) & (contrast >= contrast_threshold)
    yx = np.argwhere(mask)
    if yx.size == 0:
        return []

    y = yx[:, 0]
    x = yx[:, 1]
    score = contrast[y, x] * 0.7 + luminance[y, x] * 0.3
    limit = min(max(count * 80, 160), yx.shape[0])
    top = np.argpartition(score, -limit)[-limit:]
    selected = yx[top]
    selected_score = score[top]
    order = np.argsort(selected_score)[::-1]
    candidates = _patch_mean_colors(img, selected[order])
    candidates = _deduplicate_colors(candidates)
    if candidates.shape[0] == 0:
        return []
    return [_tuple_color(color) for color in _quantile_pick_by_temperature(candidates, count)]


def _sample_broad_theme_colors(image_rgb: np.ndarray, count: int = 3) -> list[tuple[float, float, float, float]]:
    img = _as_float_rgb(image_rgb)

    flat = img.reshape(-1, img.shape[-1])[:, :3]
    luminance = flat @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    saturation = flat.max(axis=1) - flat.min(axis=1)
    score = luminance * 0.55 + saturation * 0.45
    candidate_count = max(count * 32, 96)
    idx = np.argpartition(score, -min(candidate_count, score.size))[-min(candidate_count, score.size):]
    candidates = flat[idx]
    order = np.argsort(candidates @ np.array([0.25, 0.5, 0.25], dtype=np.float32))
    ranked = candidates[order]

    if ranked.shape[0] == 0:
        ranked = flat[np.argsort(luminance)[-count:]]

    picks = []
    for q in np.linspace(0.15, 0.85, count):
        color = ranked[min(ranked.shape[0] - 1, int(q * (ranked.shape[0] - 1)))]
        picks.append((float(color[0]), float(color[1]), float(color[2]), 1.0))
    return picks


def _as_float_rgb(image_rgb: np.ndarray) -> np.ndarray:
    img = np.asarray(image_rgb, dtype=np.float32)
    if img.ndim == 2:
        img = np.repeat(img[:, :, None], 3, axis=2)
    if img.shape[-1] > 3:
        img = img[:, :, :3]
    if img.max(initial=0.0) > 1.0:
        img /= 255.0
    return np.clip(img, 0.0, 1.0)


def _box_blur(image: np.ndarray, radius: int) -> np.ndarray:
    try:
        import cv2

        kernel = radius * 2 + 1
        return cv2.blur(image.astype(np.float32), (kernel, kernel), borderType=cv2.BORDER_REFLECT)
    except ImportError:
        padded = np.pad(image, radius, mode="reflect")
        out = np.zeros_like(image, dtype=np.float32)
        area = float((radius * 2 + 1) ** 2)
        for dy in range(radius * 2 + 1):
            for dx in range(radius * 2 + 1):
                out += padded[dy : dy + image.shape[0], dx : dx + image.shape[1]]
        return out / area


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
        # Weighted blend keeps tiny colored star cores without overreacting to
        # single-pixel sensor noise.
        colors.append(center * 0.65 + patch.reshape(-1, 3).mean(axis=0) * 0.35)
    return np.asarray(colors, dtype=np.float32)


def _deduplicate_colors(colors: np.ndarray) -> np.ndarray:
    if colors.size == 0:
        return colors.reshape((0, 3)).astype(np.float32)
    rounded = np.round(colors * 32.0).astype(np.int32)
    _, unique_idx = np.unique(rounded, axis=0, return_index=True)
    return colors[np.sort(unique_idx)]


def _quantile_pick_by_temperature(colors: np.ndarray, count: int) -> np.ndarray:
    temperature = colors[:, 0] - colors[:, 2]
    brightness = colors @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    order = np.lexsort((-brightness, temperature))
    ranked = colors[order]
    if ranked.shape[0] <= count:
        return ranked

    picks = []
    for q in np.linspace(0.05, 0.95, count):
        picks.append(ranked[min(ranked.shape[0] - 1, int(q * (ranked.shape[0] - 1)))])
    return np.asarray(picks, dtype=np.float32)


def _tuple_color(color: np.ndarray) -> tuple[float, float, float, float]:
    clipped = np.clip(color, 0.0, 1.0)
    return (float(clipped[0]), float(clipped[1]), float(clipped[2]), 1.0)


def build_star_color_palette(
    sampled_colors: list[tuple[float, float, float, float]] | None = None,
) -> list[tuple[float, float, float, float]]:
    """Build a natural star palette with subtle image-derived tints.

    Real star fields are mostly white with small cool/warm differences. Nebula
    samples are blended toward white so imported photos influence the effect
    without turning the particles into saturated colored noise.
    """

    palette = list(NATURAL_STAR_COLORS)
    if not sampled_colors:
        return palette

    white = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    cool_white = np.array([0.86, 0.92, 1.0], dtype=np.float32)
    for color in sampled_colors[:3]:
        rgb = np.clip(np.asarray(color[:3], dtype=np.float32), 0.0, 1.0)
        soft_tint = rgb * 0.28 + white * 0.72
        cool_tint = rgb * 0.18 + cool_white * 0.82
        palette.append((float(soft_tint[0]), float(soft_tint[1]), float(soft_tint[2]), 1.0))
        palette.append((float(cool_tint[0]), float(cool_tint[1]), float(cool_tint[2]), 1.0))
    return palette
