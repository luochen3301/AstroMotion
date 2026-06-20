import sys
import unittest

from PySide6.QtWidgets import QApplication

from astromotion.ui.advanced_settings_panel import AdvancedSettingsPanel
from astromotion.ui.theme import app_stylesheet


class AdvancedSettingsPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_zoom_controls_are_exposed(self):
        panel = AdvancedSettingsPanel()
        settings = panel.current_settings()
        self.assertIn("zoom_start", settings)
        self.assertIn("zoom_end", settings)
        self.assertIn("zoom_speed", settings)
        self.assertIn("rotation_degrees", settings)
        self.assertIn("brightness", settings)
        self.assertIn("color_intensity", settings)
        self.assertIn("star_detection_sensitivity", settings)
        self.assertIn("source_star_strength", settings)
        self.assertAlmostEqual(settings["zoom_start"], 1.0)
        self.assertAlmostEqual(settings["zoom_speed"], 1.0)
        self.assertAlmostEqual(settings["rotation_degrees"], 4.8)
        self.assertAlmostEqual(settings["star_detection_sensitivity"], 0.55)
        self.assertAlmostEqual(settings["source_star_strength"], 1.0)
        self.assertAlmostEqual(settings["size"], 4.0)
        self.assertGreater(settings["brightness"], 1.0)
        self.assertGreater(settings["color_intensity"], 1.0)
        self.assertEqual(panel._rows["color_intensity"].spin.maximum(), 5.0)
        self.assertEqual(panel._rows["source_star_strength"].spin.maximum(), 2.0)
        self.assertEqual(panel._rows["rotation_degrees"].spin.minimum(), -20.0)
        self.assertEqual(panel._rows["rotation_degrees"].spin.maximum(), 20.0)
        panel.close()

    def test_slider_rows_keep_clickable_control_widths(self):
        panel = AdvancedSettingsPanel()
        row = panel._rows["star_detection_sensitivity"]

        self.assertGreaterEqual(panel.minimumWidth(), 420)
        self.assertGreaterEqual(row.slider.minimumWidth(), 96)
        self.assertGreaterEqual(row.spin.minimumWidth(), 128)
        panel.close()

    def test_export_resolution_options_are_exposed(self):
        panel = AdvancedSettingsPanel()
        options = panel.render_options()
        self.assertEqual(options["resolution_mode"], "source")
        labels = [panel.resolution_combo.itemText(i) for i in range(panel.resolution_combo.count())]
        modes = [panel.resolution_combo.itemData(i) for i in range(panel.resolution_combo.count())]
        self.assertIn("跟随原图", labels)
        self.assertEqual(modes, ["source", "2k", "4k"])
        panel.close()

    def test_theme_does_not_paint_black_label_backgrounds(self):
        stylesheet = app_stylesheet()
        self.assertIn("QLabel#FormLabel", stylesheet)
        self.assertIn("QWidget#SliderRow", stylesheet)
        self.assertIn("background-color: transparent", stylesheet)
        self.assertNotIn("QWidget {\n        background:", stylesheet)


if __name__ == "__main__":
    unittest.main()
