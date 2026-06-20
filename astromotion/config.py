"""Shared application constants."""

APP_NAME = "AstroMotion"
APP_VERSION = "3.0.0"

DEFAULT_CANVAS_SIZE = (1920, 1080)
DEFAULT_PARTICLE_COUNT = 100_000
DEFAULT_DURATION_SECONDS = 10
DEFAULT_FPS = 60

EXPORT_RESOLUTION_PRESETS = {
    "2k": (2560, 1440),
    "4k": (3840, 2160),
}
DEFAULT_EXPORT_RESOLUTION_MODE = "source"

SUPPORTED_IMAGE_FILTER = (
    "Deep-sky Images (*.jpg *.jpeg *.png *.tif *.tiff *.fits *.fit);;"
    "Raster Images (*.jpg *.jpeg *.png *.tif *.tiff);;"
    "FITS Images (*.fits *.fit);;"
    "All Files (*.*)"
)
