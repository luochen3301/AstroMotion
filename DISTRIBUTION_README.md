# AstroMotion Portable Package

## How to Run

1. Extract the ZIP package to a local folder.
2. Double-click `AstroMotion.exe`.
3. Import a JPG, PNG, TIFF, or FITS deep-sky image.
4. AstroMotion automatically extracts real source stars when the image has enough point stars.
5. Choose a preset, adjust Advanced Settings if needed, then render MP4.

## Notes

- The app includes a bundled FFmpeg executable when the release script can find `imageio_ffmpeg`.
- Social-compatible H.264 MP4 export uses FFmpeg. If export fails, keep the app folder intact and avoid moving files out of it.
- The interface language follows your Windows language by default. Change it from the top toolbar.
- If too few real stars are detected, AstroMotion falls back to the generated starfield.
