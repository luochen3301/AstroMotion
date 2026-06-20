import sys
import unittest

from PySide6.QtWidgets import QApplication

from astromotion.ui.main_window import MainWindow


class ExportResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_resolves_2k_and_4k_presets(self):
        window = MainWindow()
        self.assertEqual(window._resolve_export_size("2k"), (2560, 1440))
        self.assertEqual(window._resolve_export_size("4k"), (3840, 2160))
        window.close()

    def test_source_resolution_uses_loaded_image_size_and_even_dimensions(self):
        window = MainWindow()
        window.preview.current_image_size = (3001, 2001)
        self.assertEqual(window._resolve_export_size("source"), (3000, 2000))
        window.close()

    def test_source_resolution_falls_back_to_2k_without_image(self):
        window = MainWindow()
        window.preview.current_image_size = None
        self.assertEqual(window._resolve_export_size("source"), (2560, 1440))
        window.close()


if __name__ == "__main__":
    unittest.main()

