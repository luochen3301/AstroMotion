import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from astromotion.i18n import language_manager
from astromotion.ui.main_window import MainWindow


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_particle_inspector_feature_is_removed(self):
        window = MainWindow()
        self.assertFalse(hasattr(window, "particle_preview"))
        self.assertFalse(hasattr(window, "particle_dock"))
        self.assertFalse(hasattr(window, "particle_toggle_button"))
        self.assertTrue(hasattr(window, "preview"))
        window.close()

    def test_import_uses_main_preview_only(self):
        window = MainWindow()
        fake_path = str(Path("K:/software-test/nebula.png"))

        def fake_load(path):
            window.preview.current_image_path = Path(path)
            window.preview.current_image_size = (3200, 1800)
            window.preview.current_theme_colors = [(0.8, 0.9, 1.0, 1.0)]

        with (
            patch(
                "astromotion.ui.main_window.QFileDialog.getOpenFileName",
                return_value=(fake_path, ""),
            ),
            patch.object(window.preview, "load_image", side_effect=fake_load) as load_image,
            patch("astromotion.ui.main_window.QMessageBox.critical") as critical,
        ):
            window._choose_image()

        load_image.assert_called_once_with(fake_path)
        critical.assert_not_called()
        self.assertEqual(window.file_label.text(), Path(fake_path).name)
        window.close()

    def test_language_switch_updates_main_controls(self):
        window = MainWindow()
        language_manager.set_language("zh")
        self.assertEqual(window.import_button.text(), "导入图像")
        self.assertEqual(window.language_combo.currentData(), "zh")
        self.assertEqual(window.settings_panel.render_button.text(), "一键渲染导出")
        language_manager.set_language("en")
        self.assertEqual(window.import_button.text(), "Import Image")
        self.assertEqual(window.language_combo.currentData(), "en")
        self.assertEqual(window.settings_panel.render_button.text(), "Render Video")
        self.assertEqual(window.advanced_dock.windowTitle(), "Advanced Settings")
        window.close()
        language_manager.set_language("auto")

    def test_language_selector_is_in_top_toolbar_not_settings_panel(self):
        window = MainWindow()
        self.assertTrue(hasattr(window, "language_combo"))
        self.assertFalse(hasattr(window.settings_panel, "language_combo"))
        window.close()

    def test_advanced_dock_opens_wide_enough_for_controls(self):
        window = MainWindow()

        self.assertGreaterEqual(window.advanced_dock.minimumWidth(), 430)
        self.assertGreaterEqual(window.settings_panel.minimumWidth(), 420)
        self.assertGreaterEqual(window.advanced_dock.width(), 430)
        window.close()

    def test_nebula_close_pass_is_selected_on_startup(self):
        window = MainWindow()

        self.assertEqual(window.preview.current_preset_name, "Nebula Close Pass")
        self.assertTrue(window.preset_bar._buttons["Nebula Close Pass"].isChecked())
        self.assertAlmostEqual(window.settings_panel.current_settings()["size"], 4.0)
        self.assertAlmostEqual(window.settings_panel.current_settings()["rotation_degrees"], 4.8)
        window.close()

    def test_source_star_status_updates_with_language(self):
        window = MainWindow()
        window.preview.current_image_path = Path("K:/software-test/nebula.png")
        language_manager.set_language("en")

        window._source_stars_changed(42, True)
        self.assertEqual(window.status_label.text(), "42 real stars extracted")

        window._source_stars_changed(3, False)
        self.assertEqual(window.status_label.text(), "Using generated stars")

        window.close()
        language_manager.set_language("auto")


if __name__ == "__main__":
    unittest.main()
