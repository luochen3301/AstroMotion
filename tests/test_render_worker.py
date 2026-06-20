import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astromotion.export.gpu_offscreen_renderer import GpuRendererUnavailable
from astromotion.export.offscreen_renderer import OffscreenRenderer
from astromotion.export.render_worker import RenderSettings, RenderWorker
from astromotion.engine.star_extraction import ExtractedStarField
from astromotion.presets import get_preset
import numpy as np


class RenderWorkerTests(unittest.TestCase):
    def test_render_settings_default_to_social_compatible_h264(self):
        settings = RenderSettings(
            output_path=Path(tempfile.gettempdir()) / "astromotion-test.mp4",
            preset={**get_preset("Deep Space Flythrough"), "particle_count": 10},
            width=64,
            height=36,
        )
        self.assertFalse(settings.color_fidelity)
        self.assertFalse(settings.prefer_nvenc)
        self.assertEqual(settings.quality_crf, 18)

    def test_falls_back_to_cpu_renderer_when_gpu_unavailable(self):
        settings = RenderSettings(
            output_path=Path(tempfile.gettempdir()) / "astromotion-test.mp4",
            preset={**get_preset("Deep Space Flythrough"), "particle_count": 10},
            width=64,
            height=36,
            prefer_gpu=True,
        )
        worker = RenderWorker(settings)
        with patch(
            "astromotion.export.render_worker.GpuOffscreenRenderer",
            side_effect=GpuRendererUnavailable("no test gpu"),
        ):
            renderer = worker._create_renderer()
        self.assertIsInstance(renderer, OffscreenRenderer)

    def test_can_disable_gpu_renderer(self):
        settings = RenderSettings(
            output_path=Path(tempfile.gettempdir()) / "astromotion-test.mp4",
            preset={**get_preset("Deep Space Flythrough"), "particle_count": 10},
            width=64,
            height=36,
            prefer_gpu=False,
        )
        renderer = RenderWorker(settings)._create_renderer()
        self.assertIsInstance(renderer, OffscreenRenderer)

    def test_cpu_renderer_receives_source_star_field(self):
        field = ExtractedStarField(
            source_size=(32, 18),
            xy=np.asarray([[0.5, 0.5]], dtype=np.float32),
            colors=np.asarray([[1.0, 0.95, 0.8]], dtype=np.float32),
            intensity=np.asarray([1.0], dtype=np.float32),
            radius=np.asarray([1.0], dtype=np.float32),
            score=np.asarray([1.0], dtype=np.float32),
        )
        settings = RenderSettings(
            output_path=Path(tempfile.gettempdir()) / "astromotion-test.mp4",
            preset={**get_preset("Deep Space Flythrough"), "emitter": "image_stars", "particle_count": 10},
            source_star_field=field,
            width=64,
            height=36,
            prefer_gpu=False,
        )

        renderer = RenderWorker(settings)._create_renderer()

        self.assertIs(renderer.engine.source_star_field, field)
        self.assertEqual(renderer.engine.active_count, 1)


if __name__ == "__main__":
    unittest.main()
