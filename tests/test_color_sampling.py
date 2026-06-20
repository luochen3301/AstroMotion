import unittest
from unittest.mock import patch

import numpy as np

import astromotion.engine.color_sampling as color_sampling
from astromotion.engine.color_sampling import build_star_color_palette, sample_star_colors, sample_theme_colors


class ColorSamplingTests(unittest.TestCase):
    def test_star_palette_contains_cool_warm_and_sampled_tints(self):
        sampled = [(0.9, 0.25, 0.45, 1.0), (0.2, 0.45, 1.0, 1.0)]
        palette = np.asarray(build_star_color_palette(sampled), dtype=np.float32)

        self.assertGreaterEqual(palette.shape[0], 12)
        self.assertTrue(np.any(palette[:, 2] > palette[:, 0]))
        self.assertTrue(np.any(palette[:, 0] > palette[:, 2]))
        self.assertTrue(np.any((palette[:, 0] > 0.95) & (palette[:, 1] < 0.95) & (palette[:, 2] < 0.95)))

    def test_sample_theme_colors_accepts_empty_images(self):
        colors = sample_theme_colors(np.empty((0, 0, 3), dtype=np.uint8), count=3)
        self.assertEqual(len(colors), 3)
        self.assertTrue(all(len(color) == 4 for color in colors))

    def test_star_sampling_prefers_point_stars_over_nebula_cloud(self):
        image = np.zeros((80, 120, 3), dtype=np.uint8)
        image[:, :, :] = (18, 14, 22)
        image[20:62, 20:96] = (135, 42, 30)
        stars = [
            (12, 15, (245, 248, 255)),
            (24, 88, (105, 168, 255)),
            (54, 40, (255, 210, 130)),
            (65, 105, (225, 240, 255)),
            (36, 62, (255, 120, 90)),
        ]
        for y, x, color in stars:
            image[y, x] = color
            image[y - 1 : y + 2, x - 1 : x + 2] = np.maximum(image[y - 1 : y + 2, x - 1 : x + 2], 60)
            image[y, x] = color

        sampled = np.asarray(sample_star_colors(image, count=4), dtype=np.float32)[:, :3]

        self.assertEqual(sampled.shape[0], 4)
        self.assertTrue(np.any(sampled[:, 2] > sampled[:, 0] + 0.08))
        self.assertTrue(np.any(sampled[:, 0] > sampled[:, 2] + 0.08))
        self.assertGreater(float(sampled.mean()), 0.35)

    def test_theme_sampling_uses_star_path_when_available(self):
        image = np.zeros((48, 64, 3), dtype=np.uint8)
        image[:, :] = (90, 20, 20)
        image[10, 10] = (80, 150, 255)
        image[20, 30] = (255, 220, 150)
        image[35, 50] = (240, 245, 255)

        colors = sample_theme_colors(image, count=3)

        self.assertEqual(len(colors), 3)
        self.assertTrue(any(color[2] > color[0] for color in colors))

    def test_sample_theme_colors_downsamples_large_images_for_analysis(self):
        image = np.zeros((3000, 3000, 3), dtype=np.uint8)
        seen_shapes = []

        def fake_star_colors(sampling_image, count):
            seen_shapes.append(sampling_image.shape)
            return []

        def fake_broad_colors(sampling_image, count):
            seen_shapes.append(sampling_image.shape)
            return [(0.7, 0.8, 1.0, 1.0)] * count

        with (
            patch.object(color_sampling, "sample_star_colors", side_effect=fake_star_colors),
            patch.object(color_sampling, "_sample_broad_theme_colors", side_effect=fake_broad_colors),
        ):
            colors = sample_theme_colors(image, count=3)

        self.assertEqual(len(colors), 3)
        self.assertTrue(seen_shapes)
        self.assertLessEqual(seen_shapes[0][0] * seen_shapes[0][1], 2_000_000)


if __name__ == "__main__":
    unittest.main()
