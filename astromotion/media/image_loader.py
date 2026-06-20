"""Image loading helpers for JPG/PNG/TIFF and FITS handoff."""

from __future__ import annotations

from pathlib import Path
from io import BytesIO

import numpy as np


def load_image_rgb(path: str | Path) -> np.ndarray:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".fits", ".fit"}:
        from astromotion.media.fits_loader import load_fits_rgb

        return load_fits_rgb(path)

    pillow_image = _load_with_pillow_srgb(path)
    if pillow_image is not None:
        return pillow_image

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to load raster images.") from exc

    data = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if data is None:
        raise ValueError(f"Could not read image: {path}")

    if data.ndim == 2:
        data = cv2.cvtColor(data, cv2.COLOR_GRAY2RGB)
    elif data.shape[2] == 4:
        data = cv2.cvtColor(data, cv2.COLOR_BGRA2RGBA)
        alpha = data[:, :, 3:4].astype(np.float32) / _max_value(data)
        rgb = data[:, :, :3].astype(np.float32)
        rgb = rgb * alpha + (1.0 - alpha) * 0.0
        return _normalize_to_uint8(rgb)
    else:
        data = cv2.cvtColor(data, cv2.COLOR_BGR2RGB)
    return _normalize_to_uint8(data)


def _load_with_pillow_srgb(path: Path) -> np.ndarray | None:
    try:
        from PIL import Image, ImageCms
    except ImportError:
        return None

    try:
        with Image.open(path) as image:
            has_alpha = "A" in image.getbands()
            image = image.convert("RGBA" if has_alpha else "RGB")
            icc_profile = image.info.get("icc_profile")
            if icc_profile:
                try:
                    source_profile = ImageCms.ImageCmsProfile(BytesIO(icc_profile))
                    srgb_profile = ImageCms.createProfile("sRGB")
                    if image.mode == "RGBA":
                        rgb = ImageCms.profileToProfile(image.convert("RGB"), source_profile, srgb_profile)
                        image = Image.merge("RGBA", (*rgb.split(), image.getchannel("A")))
                    else:
                        image = ImageCms.profileToProfile(image, source_profile, srgb_profile)
                except Exception:
                    image = image.convert("RGBA" if has_alpha else "RGB")
            data = np.asarray(image)
    except Exception:
        return None

    if data.ndim == 3 and data.shape[2] == 4:
        alpha = data[:, :, 3:4].astype(np.float32) / 255.0
        rgb = data[:, :, :3].astype(np.float32)
        return _normalize_to_uint8(rgb * alpha)
    if data.ndim == 3 and data.shape[2] >= 3:
        return _normalize_to_uint8(data[:, :, :3])
    if data.ndim == 2:
        rgb = np.repeat(data[:, :, None], 3, axis=2)
        return _normalize_to_uint8(rgb)
    return None


def fit_image_to_canvas(image_rgb: np.ndarray, width: int, height: int) -> np.ndarray:
    """Letterbox image to a target RGB canvas without distorting aspect ratio."""

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to resize images.") from exc

    src_h, src_w = image_rgb.shape[:2]
    scale = min(width / max(1, src_w), height / max(1, src_h))
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))
    resized = cv2.resize(image_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    x = (width - new_w) // 2
    y = (height - new_h) // 2
    canvas[y : y + new_h, x : x + new_w] = resized[:, :, :3]
    return canvas


def _max_value(array: np.ndarray) -> float:
    if np.issubdtype(array.dtype, np.integer):
        return float(np.iinfo(array.dtype).max)
    return float(max(1.0, array.max()))


def _normalize_to_uint8(data: np.ndarray) -> np.ndarray:
    arr = data.astype(np.float32)
    max_value = _max_value(data)
    if max_value > 1.0:
        arr /= max_value
    arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
    arr = np.clip(arr, 0.0, 1.0)
    return (arr * 255.0 + 0.5).astype(np.uint8)
