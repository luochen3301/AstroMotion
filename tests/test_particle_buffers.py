import unittest

import numpy as np

from astromotion.engine.camera_motion import zoom_at_time
from astromotion.engine.particle_engine import ParticleEngine, _gl_handle
from astromotion.engine.particle_types import create_empty_buffers, interleave_for_gpu
from astromotion.export.offscreen_renderer import OffscreenRenderer
from astromotion.presets import get_preset


class ParticleBufferTests(unittest.TestCase):
    def test_buffer_shapes(self):
        buffers = create_empty_buffers(128)
        self.assertEqual(buffers.positions.shape, (128, 3))
        self.assertEqual(buffers.previous_positions.shape, (128, 3))
        self.assertEqual(buffers.velocities.shape, (128, 3))
        self.assertEqual(buffers.colors.shape, (128, 4))
        self.assertEqual(buffers.life.shape, (128, 2))
        self.assertEqual(buffers.sizes.shape, (128,))

    def test_interleaved_gpu_layout(self):
        buffers = create_empty_buffers(4)
        packed = interleave_for_gpu(buffers, 4)
        self.assertEqual(packed.shape, (4, 16))
        self.assertEqual(packed.dtype, np.float32)

    def test_engine_clamps_active_count(self):
        engine = ParticleEngine(max_particles=500, preset={"particle_count": 2000}, seed=1)
        self.assertEqual(engine.active_count, 500)

    def test_deep_space_update_changes_positions(self):
        engine = ParticleEngine(max_particles=2000, preset="Deep Space Flythrough", seed=2)
        before = engine.snapshot()["positions"].copy()
        engine.update(1.0 / 60.0)
        after = engine.snapshot()["positions"]
        self.assertGreater(float(np.mean(np.abs(after - before))), 0.0)

    def test_cinematic_star_drift_moves_slower_than_default(self):
        fast = ParticleEngine(max_particles=3000, preset="Deep Space Flythrough", seed=3)
        slow = ParticleEngine(max_particles=3000, preset="Cinematic Star Drift", seed=3)
        self.assertLess(
            float(np.mean(np.abs(slow.snapshot()["velocities"][:, 2]))),
            float(np.mean(np.abs(fast.snapshot()["velocities"][:, 2]))),
        )

    def test_deep_space_uses_varied_star_colors(self):
        engine = ParticleEngine(max_particles=3000, preset="Deep Space Flythrough", seed=9)
        colors = engine.snapshot()["colors"][:, :3]
        rounded_unique = np.unique(np.round(colors, 2), axis=0)

        self.assertGreater(rounded_unique.shape[0], 8)
        self.assertGreater(float(np.std(colors[:, 0] - colors[:, 2])), 0.02)
        self.assertTrue(np.any(colors[:, 2] > colors[:, 0]))
        self.assertTrue(np.any(colors[:, 0] > colors[:, 2]))

    def test_color_intensity_controls_star_color_variation(self):
        muted = {**get_preset("Deep Space Flythrough"), "color_intensity": 0.0}
        vivid = {**get_preset("Deep Space Flythrough"), "color_intensity": 5.0}
        muted_engine = ParticleEngine(max_particles=3000, preset=muted, seed=10)
        vivid_engine = ParticleEngine(max_particles=3000, preset=vivid, seed=10)

        muted_colors = muted_engine.snapshot()["colors"][:, :3]
        vivid_colors = vivid_engine.snapshot()["colors"][:, :3]
        muted_variation = float(np.std(muted_colors[:, 0] - muted_colors[:, 2]))
        vivid_variation = float(np.std(vivid_colors[:, 0] - vivid_colors[:, 2]))

        self.assertLess(muted_variation, 0.005)
        self.assertGreater(vivid_variation, muted_variation + 0.25)

    def test_update_params_changes_count(self):
        engine = ParticleEngine(max_particles=5000, preset="Deep Space Flythrough", seed=4)
        engine.update_params({"particle_count": 1234})
        self.assertEqual(engine.active_count, 1234)

    def test_state_changes_only_mark_gpu_dirty_without_binding_buffers(self):
        class ExplodingGL:
            GL_ARRAY_BUFFER = 0x8892

            def glBindBuffer(self, *_args):
                raise AssertionError("glBindBuffer must only run during render-time flush")

        engine = ParticleEngine(max_particles=300, preset="Deep Space Flythrough", seed=14)
        engine.gl_initialized = True
        engine.gl = ExplodingGL()
        engine.gpu_dirty = False

        engine.update_params({"color_intensity": 4.0})
        self.assertTrue(engine.gpu_dirty)

        engine.gpu_dirty = False
        engine.set_preset("Cinematic Star Drift")
        self.assertTrue(engine.gpu_dirty)

        engine.gpu_dirty = False
        engine.seek(0.25)
        self.assertTrue(engine.gpu_dirty)

        engine.gpu_dirty = False
        engine.update(1.0 / 60.0)
        self.assertTrue(engine.gpu_dirty)

    def test_gl_handle_normalizes_numpy_ids_to_python_ints(self):
        self.assertEqual(_gl_handle(np.uint32(5)), 5)
        self.assertIs(type(_gl_handle(np.uint32(5))), int)
        self.assertEqual(_gl_handle(np.asarray([7], dtype=np.uint32)), 7)
        self.assertIs(type(_gl_handle(np.asarray([7], dtype=np.uint32))), int)

    def test_update_color_intensity_recolors_without_moving_particles(self):
        engine = ParticleEngine(max_particles=2000, preset="Deep Space Flythrough", seed=13)
        positions_before = engine.snapshot()["positions"].copy()
        colors_before = engine.snapshot()["colors"][:, :3].copy()
        engine.update_params({"color_intensity": 5.0})
        positions_after = engine.snapshot()["positions"]
        colors_after = engine.snapshot()["colors"][:, :3]

        self.assertLess(float(np.mean(np.abs(positions_after - positions_before))), 1e-7)
        self.assertGreater(float(np.mean(np.abs(colors_after - colors_before))), 0.01)

    def test_deep_space_particles_move_toward_camera(self):
        engine = ParticleEngine(max_particles=3000, preset="Deep Space Flythrough", seed=5)
        before_z = engine.snapshot()["positions"][:, 2].copy()
        engine.update(1.0 / 60.0)
        after_z = engine.snapshot()["positions"][:, 2]
        self.assertLess(float(np.mean(after_z)), float(np.mean(before_z)))

    def test_previous_positions_track_trails(self):
        engine = ParticleEngine(max_particles=1000, preset="Deep Space Flythrough", seed=6)
        before = engine.snapshot()["positions"].copy()
        engine.update(1.0 / 60.0)
        previous = engine.snapshot()["previous_positions"]
        per_particle_delta = np.linalg.norm(previous - before, axis=1)
        self.assertGreater(float(np.mean(per_particle_delta < 1e-6)), 0.95)

    def test_zoom_curve_reaches_push_in(self):
        preset = {"zoom_start": 1.0, "zoom_end": 1.12}
        self.assertAlmostEqual(zoom_at_time(preset, 0.0, 10.0), 1.0)
        self.assertGreater(zoom_at_time(preset, 5.0, 10.0), 1.05)
        self.assertAlmostEqual(zoom_at_time(preset, 10.0, 10.0), 1.12)
        self.assertAlmostEqual(zoom_at_time(preset, 12.0, 10.0), 1.12)

    def test_zoom_speed_changes_curve_timing(self):
        slow = {"zoom_start": 1.0, "zoom_end": 1.2, "zoom_speed": 0.5}
        fast = {"zoom_start": 1.0, "zoom_end": 1.2, "zoom_speed": 2.0}
        self.assertLess(zoom_at_time(slow, 3.0, 10.0), zoom_at_time(fast, 3.0, 10.0))
        self.assertAlmostEqual(zoom_at_time(fast, 5.0, 10.0), 1.2)

    def test_seek_is_deterministic(self):
        engine = ParticleEngine(max_particles=1200, preset="Deep Space Flythrough", seed=11)
        engine.seek(3.0)
        first = engine.snapshot()["positions"].copy()
        engine.seek(3.0)
        second = engine.snapshot()["positions"].copy()
        self.assertAlmostEqual(engine.time_seconds, 3.0)
        self.assertLess(float(np.mean(np.abs(first - second))), 1e-7)

    def test_offscreen_deep_space_frame_renders(self):
        renderer = OffscreenRenderer(
            width=160,
            height=90,
            preset={**get_preset("Deep Space Flythrough"), "particle_count": 800},
            duration_seconds=10.0,
            seed=8,
        )
        frame = renderer.render_frame(1.0 / 60.0)
        self.assertEqual(frame.shape, (90, 160, 3))
        self.assertGreater(int(frame.max()), 20)

    def test_offscreen_brightness_increases_particle_energy(self):
        base = {**get_preset("Deep Space Flythrough"), "particle_count": 800, "brightness": 0.5}
        bright = {**get_preset("Deep Space Flythrough"), "particle_count": 800, "brightness": 3.0}
        dim_renderer = OffscreenRenderer(160, 90, base, duration_seconds=10.0, seed=12)
        bright_renderer = OffscreenRenderer(160, 90, bright, duration_seconds=10.0, seed=12)
        dim_frame = dim_renderer.render_frame(1.0 / 60.0)
        bright_frame = bright_renderer.render_frame(1.0 / 60.0)
        self.assertGreater(float(bright_frame.mean()), float(dim_frame.mean()))


if __name__ == "__main__":
    unittest.main()
