# AstroMotion V3.0 Release Notes

AstroMotion V3.0 is the first full real-star motion release. It turns imported
deep-sky photos into animated MP4 clips by extracting source stars from the
image, matching the preview canvas to the photo aspect, and exporting with a
social-platform-compatible H.264 video path.

## Highlights

- Added automatic real-star extraction for imported deep-sky photos.
- Real source stars now replace generated random particles when enough stars
  are detected, with a generated-star fallback for low-signal images.
- Added real-star depth motion so extracted photo stars animate with push-in
  perspective, trails, and camera movement.
- Added controls for detection sensitivity and real-star strength.
- Preview and MP4 export now use the same extracted-star data path for
  consistent output.
- The preview canvas follows the imported image aspect, and source-resolution
  export follows the image dimensions.
- Fixed rotation distortion by using aspect-correct background rotation.
- Fixed rotation-exposed black corners with automatic safe zoom compensation.
- Expanded the default Advanced Settings sidebar width so sliders and numeric
  controls remain clickable on startup.
- Made Nebula Close Pass the startup default preset with the saved close-up
  parameter set.
- Switched default MP4 export to social-compatible H.264/AVC `yuv420p`,
  BT.709, limited-range, `avc1`, and `faststart` encoding to avoid green-frame
  decoder failures on some players and social platforms.

## Package

- Windows portable package: `AstroMotion-V3.0-windows-x64.zip`
- App version: `3.0.0`
- Includes `AstroMotion.exe`, shader resources, documentation, and bundled
  FFmpeg when available from the build environment.

## Upgrade Notes

- Keep the extracted portable folder intact; do not move only
  `AstroMotion.exe`.
- For social media upload, use the default export settings. The default encoder
  is now compatibility-first rather than RGB/full-range color-fidelity-first.
