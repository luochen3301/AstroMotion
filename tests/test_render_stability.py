import unittest
from pathlib import Path

import numpy as np

from astromotion.engine.camera_motion import rotation_at_time
from astromotion.export.offscreen_renderer import OffscreenRenderer
from astromotion.media.image_loader import fit_image_to_canvas
from astromotion.presets import get_preset


class RenderStabilityTests(unittest.TestCase):
    def test_background_shader_has_no_tone_mapping(self):
        shader = Path("astromotion/shaders/fullscreen_image.frag").read_text(encoding="utf-8")
        self.assertNotIn("exp(-color", shader)
        self.assertNotIn("u_exposure", shader)
        self.assertIn("u_image_size", shader)
        self.assertIn("u_canvas_size", shader)
        self.assertIn("u_rotation_degrees", shader)
        self.assertIn("fit_size", shader)

    def test_rotation_curve_reaches_target(self):
        preset = {"rotation_degrees": 4.0, "zoom_speed": 1.0}
        self.assertAlmostEqual(rotation_at_time(preset, 0.0, 10.0), 0.0)
        self.assertGreater(rotation_at_time(preset, 5.0, 10.0), 1.9)
        self.assertAlmostEqual(rotation_at_time(preset, 10.0, 10.0), 4.0)

    def test_fit_image_to_canvas_letterboxes_wide_images(self):
        image = np.zeros((50, 200, 3), dtype=np.uint8)
        image[:, :, 0] = 210
        image[:, :, 1] = 70
        image[:, :, 2] = 30

        canvas = fit_image_to_canvas(image, 200, 100)

        self.assertEqual(canvas.shape, (100, 200, 3))
        self.assertEqual(int(canvas[0].max()), 0)
        self.assertEqual(int(canvas[-1].max()), 0)
        self.assertEqual(canvas[50, 100].tolist(), [210, 70, 30])

    def test_affine_zoom_keeps_center_stable(self):
        renderer = OffscreenRenderer(
            width=160,
            height=90,
            preset={**get_preset("Deep Space Flythrough"), "particle_count": 1},
            duration_seconds=10.0,
            seed=20,
        )
        gradient = np.zeros((90, 160, 3), dtype=np.uint8)
        gradient[:, :, 0] = np.arange(160, dtype=np.uint8)[None, :]
        gradient[:, :, 1] = np.arange(90, dtype=np.uint8)[:, None]
        gradient[:, :, 2] = 128
        renderer.background = gradient

        center = (45, 80)
        base = renderer._zoom_background(1.0)
        zoomed = renderer._zoom_background(1.2)
        self.assertEqual(zoomed.shape, gradient.shape)
        self.assertLessEqual(int(np.abs(zoomed[center].astype(np.int16) - base[center].astype(np.int16)).max()), 1)

    def test_affine_zoom_changes_smoothly_across_small_steps(self):
        renderer = OffscreenRenderer(
            width=160,
            height=90,
            preset={**get_preset("Deep Space Flythrough"), "particle_count": 1},
            duration_seconds=10.0,
            seed=21,
        )
        x = np.linspace(0, 255, 160, dtype=np.float32)[None, :]
        y = np.linspace(0, 255, 90, dtype=np.float32)[:, None]
        renderer.background = np.dstack(
            [
                np.repeat(x, 90, axis=0),
                np.repeat(y, 160, axis=1),
                np.full((90, 160), 96.0),
            ]
        ).astype(np.uint8)

        frames = [renderer._zoom_background(1.0 + i * 0.002).astype(np.int16) for i in range(8)]
        diffs = [float(np.abs(frames[i + 1] - frames[i]).mean()) for i in range(len(frames) - 1)]
        self.assertLess(max(diffs), 0.35)
        self.assertLess(max(diffs) - min(diffs), 0.2)

    def test_rotate_background_keeps_shape_and_center(self):
        renderer = OffscreenRenderer(
            width=160,
            height=90,
            preset={**get_preset("Rotating Nebula Push-in"), "particle_count": 1},
            duration_seconds=10.0,
            seed=23,
        )
        background = np.zeros((90, 160, 3), dtype=np.uint8)
        background[:, :, 0] = 80
        background[:, :, 1] = 40
        background[:, :, 2] = 20
        background[43:48, 78:83] = (210, 70, 30)
        renderer.background = background

        rotated = renderer._transform_background(1.0, 4.0)
        self.assertEqual(rotated.shape, background.shape)
        self.assertLessEqual(
            int(np.abs(rotated[45, 80].astype(np.int16) - background[45, 80].astype(np.int16)).max()),
            3,
        )

    def test_no_particle_no_zoom_frame_preserves_background_color(self):
        renderer = OffscreenRenderer(
            width=96,
            height=64,
            preset={
                **get_preset("Deep Space Flythrough"),
                "opacity": 0.0,
                "glow": 0.0,
                "zoom_start": 1.0,
                "zoom_end": 1.0,
            },
            duration_seconds=10.0,
            seed=22,
        )
        background = np.zeros((64, 96, 3), dtype=np.uint8)
        background[:, :, 0] = 210
        background[:, :, 1] = 70
        background[:, :, 2] = 30
        renderer.background = background

        frame = renderer.render_frame(1.0 / 60.0)
        max_diff = int(np.abs(frame.astype(np.int16) - background.astype(np.int16)).max())
        self.assertLessEqual(max_diff, 1)

    def test_offscreen_color_intensity_changes_particle_frame_color(self):
        base = {
            **get_preset("Deep Space Flythrough"),
            "particle_count": 1800,
            "opacity": 1.0,
            "brightness": 2.0,
            "glow": 0.0,
            "trail_length": 0.0,
            "zoom_start": 1.0,
            "zoom_end": 1.0,
        }
        muted = OffscreenRenderer(160, 90, {**base, "color_intensity": 0.0}, duration_seconds=10.0, seed=31)
        vivid = OffscreenRenderer(160, 90, {**base, "color_intensity": 5.0}, duration_seconds=10.0, seed=31)
        muted.background[:] = 0
        vivid.background[:] = 0

        muted_frame = muted.render_frame(1.0 / 60.0).astype(np.int16)
        vivid_frame = vivid.render_frame(1.0 / 60.0).astype(np.int16)
        muted_chroma = float(np.mean(np.abs(muted_frame[:, :, 0] - muted_frame[:, :, 2])))
        vivid_chroma = float(np.mean(np.abs(vivid_frame[:, :, 0] - vivid_frame[:, :, 2])))
        self.assertGreater(vivid_chroma, muted_chroma + 0.5)


if __name__ == "__main__":
    unittest.main()
