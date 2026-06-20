import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from astromotion.export.video_encoder import (
    COLOR_FIDELITY_YUV_FILTER,
    COMPATIBILITY_FILTER,
    RGB_ENCODER,
    VideoEncoder,
    find_ffmpeg_executable,
    choose_color_fidelity_encoder,
    choose_ffmpeg_encoder,
)


class VideoEncoderFallbackTests(unittest.TestCase):
    def test_prefers_h264_nvenc(self):
        encoder = choose_ffmpeg_encoder({"libx264", "h264_nvenc", "hevc_nvenc"})
        self.assertEqual(encoder, "h264_nvenc")

    def test_compatibility_path_does_not_choose_hevc(self):
        encoder = choose_ffmpeg_encoder({"libx264", "hevc_nvenc"})
        self.assertEqual(encoder, "libx264")

    def test_falls_back_to_libx264(self):
        encoder = choose_ffmpeg_encoder({"libx264"})
        self.assertEqual(encoder, "libx264")

    def test_disables_nvenc_preference(self):
        encoder = choose_ffmpeg_encoder({"libx264", "h264_nvenc"}, prefer_nvenc=False)
        self.assertEqual(encoder, "libx264")

    def test_color_fidelity_prefers_rgb_encoder(self):
        encoder = choose_color_fidelity_encoder({"libx264", RGB_ENCODER, "h264_nvenc"}, prefer_nvenc=True)
        self.assertEqual(encoder, RGB_ENCODER)

    def test_default_command_uses_social_compatible_h264(self):
        encoder = VideoEncoder(
            Path("out.mp4"),
            width=1920,
            height=1080,
            fps=60,
            ffmpeg_path="ffmpeg",
        )
        encoder.encoder_name = "libx264"
        command = encoder._build_ffmpeg_command()

        self.assertIn("libx264", command)
        self.assertIn("yuv420p", command)
        self.assertIn(COMPATIBILITY_FILTER, command)
        self.assertIn("-profile:v", command)
        self.assertEqual(command[command.index("-profile:v") + 1], "high")
        self.assertIn("-tag:v", command)
        self.assertEqual(command[command.index("-tag:v") + 1], "avc1")
        self.assertIn("-crf", command)
        self.assertEqual(command[command.index("-crf") + 1], "18")
        self.assertIn("-preset", command)
        self.assertEqual(command[command.index("-preset") + 1], "medium")
        self.assertIn("-color_range", command)
        self.assertIn("tv", command)
        self.assertIn("+faststart", command)
        self.assertNotIn(RGB_ENCODER, command)
        self.assertNotIn("yuv444p", command)

    def test_color_fidelity_command_uses_rgb_full_range_when_requested(self):
        encoder = VideoEncoder(
            Path("out.mp4"),
            width=1920,
            height=1080,
            fps=60,
            ffmpeg_path="ffmpeg",
            color_fidelity=True,
            quality_crf=14,
        )
        encoder.encoder_name = RGB_ENCODER
        command = encoder._build_ffmpeg_command()

        self.assertIn(RGB_ENCODER, command)
        self.assertIn("rgb24", command)
        self.assertIn("-crf", command)
        self.assertEqual(command[command.index("-crf") + 1], "14")
        self.assertIn("-color_range", command)
        self.assertIn("pc", command)
        self.assertIn("iec61966-2-1", command)
        self.assertNotIn("yuv420p", command)

    def test_quality_crf_is_clamped(self):
        high = VideoEncoder(Path("out.mp4"), 1920, 1080, 60, ffmpeg_path="ffmpeg", quality_crf=99)
        low = VideoEncoder(Path("out.mp4"), 1920, 1080, 60, ffmpeg_path="ffmpeg", quality_crf=-5)
        self.assertEqual(high.quality_crf, 30)
        self.assertEqual(low.quality_crf, 0)

    def test_color_fidelity_yuv_fallback_uses_444_full_range(self):
        encoder = VideoEncoder(
            Path("out.mp4"),
            width=1920,
            height=1080,
            fps=60,
            ffmpeg_path="ffmpeg",
            prefer_nvenc=True,
            color_fidelity=True,
        )
        encoder.encoder_name = "h264_nvenc"
        command = encoder._build_ffmpeg_command()

        self.assertIn("yuv444p", command)
        self.assertIn(COLOR_FIDELITY_YUV_FILTER, command)
        self.assertIn("-color_range", command)
        self.assertIn("pc", command)
        self.assertNotIn("yuv420p", command)

    def test_finds_bundled_ffmpeg_when_available(self):
        self.assertIsNotNone(find_ffmpeg_executable())

    def test_finds_ffmpeg_next_to_packaged_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            executable = temp_path / "AstroMotion.exe"
            ffmpeg = temp_path / "ffmpeg.exe"
            executable.write_bytes(b"")
            ffmpeg.write_bytes(b"")
            with (
                patch("astromotion.export.video_encoder.sys.frozen", True, create=True),
                patch("astromotion.export.video_encoder.sys.executable", str(executable)),
            ):
                self.assertEqual(find_ffmpeg_executable(), str(ffmpeg))

    def test_color_fidelity_requires_ffmpeg_when_none_is_available(self):
        with patch("astromotion.export.video_encoder.find_ffmpeg_executable", return_value=None):
            encoder = VideoEncoder(
                Path("out.mp4"),
                width=64,
                height=48,
                fps=24,
                ffmpeg_path=None,
                color_fidelity=True,
            )
        with self.assertRaisesRegex(RuntimeError, "Color-fidelity export requires FFmpeg"):
            encoder.open()

    def test_opencv_fallback_roundtrip_keeps_color_close(self):
        try:
            import cv2
        except ImportError:
            self.skipTest("OpenCV is not installed")

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "roundtrip.mp4"
            frame = np.zeros((48, 64, 3), dtype=np.uint8)
            frame[:, :21] = (210, 70, 30)
            frame[:, 21:42] = (40, 200, 80)
            frame[:, 42:] = (30, 80, 220)

            with patch("astromotion.export.video_encoder.find_ffmpeg_executable", return_value=None):
                with VideoEncoder(output, 64, 48, 24, ffmpeg_path=None, color_fidelity=False) as encoder:
                    for _ in range(5):
                        encoder.write_frame(frame)

            capture = cv2.VideoCapture(str(output))
            ok, bgr = capture.read()
            capture.release()
            self.assertTrue(ok)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            self.assertLess(float(np.abs(rgb.astype(np.int16) - frame.astype(np.int16)).mean()), 6.0)


if __name__ == "__main__":
    unittest.main()
