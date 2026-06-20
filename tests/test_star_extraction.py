import unittest

import numpy as np

from astromotion.engine.star_extraction import extract_star_field


class StarExtractionTests(unittest.TestCase):
    def test_extracts_point_stars_with_positions_and_colors(self):
        image = np.zeros((96, 144, 3), dtype=np.uint8)
        image[:, :] = (8, 10, 18)
        image[28:74, 24:116] = (72, 26, 34)
        stars = [
            (14, 20, (245, 248, 255)),
            (30, 92, (110, 168, 255)),
            (58, 46, (255, 214, 136)),
            (75, 122, (225, 240, 255)),
            (44, 70, (255, 140, 92)),
        ]
        for y, x, color in stars:
            image[y - 1 : y + 2, x - 1 : x + 2] = np.maximum(
                image[y - 1 : y + 2, x - 1 : x + 2],
                58,
            )
            image[y, x] = color

        field = extract_star_field(image, sensitivity=0.55, max_stars=20)

        self.assertGreaterEqual(field.count, len(stars))
        self.assertEqual(field.source_size, (144, 96))
        self.assertEqual(field.xy.shape[1], 2)
        self.assertEqual(field.colors.shape[1], 3)
        self.assertTrue(np.all((field.xy >= 0.0) & (field.xy <= 1.0)))
        self.assertTrue(np.any(field.colors[:, 2] > field.colors[:, 0] + 0.08))
        self.assertTrue(np.any(field.colors[:, 0] > field.colors[:, 2] + 0.08))

    def test_broad_nebula_without_point_sources_does_not_create_dense_field(self):
        y = np.linspace(0.0, 1.0, 128, dtype=np.float32)[:, None]
        x = np.linspace(0.0, 1.0, 192, dtype=np.float32)[None, :]
        cloud = np.dstack(
            [
                np.broadcast_to(24 + 80 * x, (128, 192)),
                np.broadcast_to(18 + 42 * y, (128, 192)),
                np.broadcast_to(34 + 36 * (1.0 - x), (128, 192)),
            ]
        ).astype(np.uint8)

        field = extract_star_field(cloud, sensitivity=0.45, max_stars=200)

        self.assertLess(field.count, 8)

    def test_sensitivity_increases_detected_star_count(self):
        image = np.zeros((80, 120, 3), dtype=np.uint8)
        image[:, :] = (10, 10, 18)
        for index, (y, x) in enumerate([(10, 10), (20, 40), (40, 70), (60, 100), (68, 24)]):
            value = 90 + index * 30
            image[y, x] = (value, value, min(255, value + 18))

        low = extract_star_field(image, sensitivity=0.0, max_stars=50)
        high = extract_star_field(image, sensitivity=1.0, max_stars=50)

        self.assertGreaterEqual(high.count, low.count)
        self.assertGreater(high.count, 0)

    def test_empty_image_returns_empty_field(self):
        field = extract_star_field(np.empty((0, 0, 3), dtype=np.uint8))

        self.assertEqual(field.count, 0)
        self.assertEqual(field.xy.shape, (0, 2))


if __name__ == "__main__":
    unittest.main()
