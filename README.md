# AstroMotion

[中文说明](README.zh-CN.md)

AstroMotion is a desktop post-production tool for turning static deep-sky
photography into cinematic motion videos. Import a JPG, PNG, TIFF, or FITS
image, extract the real stars from the photo, add subtle 3D star-particle
motion, preview the result in real time, and export an MP4 video.

Recommended GitHub repository name: **`AstroMotion`**  
Python package name: **`astromotion`**

![AstroMotion main interface](docs/images/astromotion-main-en.png)

## Highlights

- Modern dark PySide6 desktop interface for astrophotography workflows.
- OpenGL preview canvas with realtime particle rendering.
- Automatic real-star extraction from imported photos, with generated-star
  fallback when too few source stars are detected.
- Real-Star Motion converts detected source-star positions, colors, and
  brightness from the photo into animated particles instead of relying only on
  random generated stars.
- Presets for deep-space flythrough, cinematic star drift, close nebula pass,
  and rotating nebula push-in.
- Advanced controls for particle count, speed, size, glow, brightness, color,
  opacity, turbulence, real-star detection sensitivity, real-star strength,
  zoom, rotation, trails, depth, duration, FPS, and export resolution.
- Video-style preview controls with play/pause and a draggable timeline.
- Chinese/English runtime language switching from the top toolbar.
- Export resolution choices for 2K, 4K, or matching the imported image.
- Social-compatible MP4 export using FFmpeg H.264/AVC with 8-bit `yuv420p`.
- Portable Windows release workflow with bundled FFmpeg support.

## Quick Start

### Option 1: Use the Portable Windows Build

1. Download `AstroMotion-V3.0-windows-x64.zip` from the GitHub Releases page.
2. Extract the full folder.
3. Double-click `AstroMotion.exe`.
4. Keep the extracted folder intact; do not move only the `.exe`.

### Option 2: Run from Source

```powershell
py -m pip install -e .[fits]
py -m astromotion.app
```

In this workspace, the prepared virtual environment can be launched directly:

```powershell
.\.venv\Scripts\python.exe -m astromotion.app
```

## Basic Workflow

1. Click **Import Image** and select a deep-sky photo. AstroMotion extracts real
   source stars automatically when the image contains enough point stars.
2. Choose a preset such as **Deep Space Flythrough** or
   **Rotating Nebula Push-in**.
3. Press **Play** or drag the timeline to preview the motion.
4. Fine-tune the right-side **Advanced Settings** panel:
   - **Particles**: density, speed, size, glow, brightness, color, opacity.
   - **Real Stars**: detection sensitivity and real-star strength.
   - **Camera Motion**: start scale, target scale, zoom speed, rotation,
     trail length, and depth strength.
   - **Export**: duration, frame rate, and output resolution.
5. Click **Render Video** and choose an MP4 output path.

## Real-Star Motion

AstroMotion can use the actual stars in your imported image as the motion
source. When you import a deep-sky photo, the app analyzes the background,
detects point stars, samples their color and brightness, and converts those
real source stars into animated particles.

This means the moving starfield follows the real structure of the photo rather
than a purely random generated field. The extracted stars support push-in depth
motion, rotation, trails, glow, and strength adjustment. Preview and MP4 export
share the same extracted-star data, so the final render matches what you saw in
the preview.

If the image does not contain enough detectable point stars, AstroMotion falls
back to the generated depth starfield automatically. Use **Real Stars** in
Advanced Settings to tune detection sensitivity and the strength of the
extracted stars.

## Export Notes

AstroMotion defaults to a social-compatible MP4 path: H.264/AVC video, 8-bit
`yuv420p`, BT.709 color metadata, limited-range video levels, and `faststart`
MP4 metadata. This avoids decoder failures such as green frames on players and
social platforms that do not reliably support RGB or 4:4:4 H.264 uploads.

For best results:

- Use the portable build or install FFmpeg locally.
- Use 2K export for fast previews.
- Use 4K or Match Source for final delivery.
- Keep particle opacity and glow moderate when the photo should remain the
  visual focus.

## Build a Portable Release

Install the release dependencies, then run:

```powershell
py -m pip install -e .[fits,release]
.\.venv\Scripts\python.exe scripts\build_release.py
```

The release package is written to:

```text
release/AstroMotion-V3.0-windows-x64.zip
```

For GitHub, upload this ZIP to a GitHub Release instead of committing it to the
source repository.

## Development

Run tests:

```powershell
py -m unittest discover -s tests
```

Compile-check the package:

```powershell
py -m compileall astromotion tests scripts
```

## Project Structure

```text
astromotion/
  app.py                    # Application entry point
  presets.py                # Particle and camera-motion presets
  i18n.py                   # Chinese/English runtime text
  engine/                   # Particle buffers, camera helpers, color sampling
  export/                   # Render worker, offscreen renderers, video encoder
  media/                    # Image/FITS/texture loading
  shaders/                  # OpenGL shaders
  ui/                       # Main window, preview widget, settings panel, theme
tests/                      # Unit and regression tests
scripts/build_release.py    # Windows portable package builder
```

## License

No open-source license has been selected yet. Add a `LICENSE` file before
accepting external contributions.
