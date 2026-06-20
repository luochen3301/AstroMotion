import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from astromotion.media.image_loader import load_image_rgb


class ImageLoaderColorTests(unittest.TestCase):
    def test_png_loader_preserves_rgb_channel_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rgb_test.png"
            source = np.zeros((8, 12, 3), dtype=np.uint8)
            source[:, :4] = (220, 30, 10)
            source[:, 4:8] = (20, 210, 40)
            source[:, 8:] = (15, 45, 230)
            Image.fromarray(source).save(path)

            loaded = load_image_rgb(path)
            self.assertEqual(loaded.shape, source.shape)
            self.assertLessEqual(int(np.abs(loaded.astype(np.int16) - source.astype(np.int16)).max()), 1)


if __name__ == "__main__":
    unittest.main()
