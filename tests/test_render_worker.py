import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astromotion.export.gpu_offscreen_renderer import GpuRendererUnavailable
from astromotion.export.offscreen_renderer import OffscreenRenderer
from astromotion.export.render_worker import RenderSettings, RenderWorker
from astromotion.presets import get_preset


class RenderWorkerTests(unittest.TestCase):
    def test_render_settings_default_to_color_fidelity(self):
        settings = RenderSettings(
            output_path=Path(tempfile.gettempdir()) / "astromotion-test.mp4",
            preset={**get_preset("Deep Space Flythrough"), "particle_count": 10},
            width=64,
            height=36,
        )
        self.assertTrue(settings.color_fidelity)
        self.assertFalse(settings.prefer_nvenc)
        self.assertEqual(settings.quality_crf, 14)

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


if __name__ == "__main__":
    unittest.main()
