import sys
import unittest

from PySide6.QtWidgets import QApplication

from astromotion.ui.gl_preview_widget import GLPreviewWidget


class PreviewCanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_canvas_viewport_matches_wide_image_aspect(self):
        preview = GLPreviewWidget()
        preview.current_image_size = (2000, 1000)

        self.assertEqual(preview._canvas_viewport_rect(1000, 800), (0, 150, 1000, 500))
        self.assertEqual(preview.heightForWidth(1000), 500)
        preview.close()

    def test_canvas_viewport_matches_square_image_aspect(self):
        preview = GLPreviewWidget()
        preview.current_image_size = (1200, 1200)

        self.assertEqual(preview._canvas_viewport_rect(1000, 500), (250, 0, 500, 500))
        self.assertEqual(preview.heightForWidth(640), 640)
        preview.close()

    def test_canvas_viewport_defaults_to_widescreen_without_image(self):
        preview = GLPreviewWidget()

        x, y, width, height = preview._canvas_viewport_rect(1600, 1000)

        self.assertEqual((x, y), (0, 50))
        self.assertEqual((width, height), (1600, 900))
        preview.close()


if __name__ == "__main__":
    unittest.main()
