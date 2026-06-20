"""FITS image loading.

This module is optional because astropy is relatively heavy. The rest of the
MVP works without it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def load_fits_rgb(path: str | Path) -> np.ndarray:
    try:
        from astropy.io import fits
    except ImportError as exc:
        raise RuntimeError("Install astromotion[fits] to load FITS images.") from exc

    with fits.open(path) as hdul:
        data = hdul[0].data
    if data is None:
        raise ValueError(f"FITS file contains no primary image data: {path}")

    arr = np.asarray(data, dtype=np.float32)
    while arr.ndim > 2:
        arr = arr[0]
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

    low, high = np.percentile(arr, (0.5, 99.5))
    if high <= low:
        high = float(arr.max() or 1.0)
        low = float(arr.min())
    stretched = np.clip((arr - low) / max(high - low, 1e-6), 0.0, 1.0)
    stretched = np.power(stretched, 1.0 / 1.8)
    rgb = np.dstack([stretched, stretched, stretched])
    return (rgb * 255.0 + 0.5).astype(np.uint8)

