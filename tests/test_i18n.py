import unittest

from astromotion.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, language_manager, preset_display_name, tr
from astromotion.presets import preset_names


class I18nTests(unittest.TestCase):
    def tearDown(self):
        language_manager.set_language("auto")

    def test_translation_table_has_required_languages(self):
        for key, values in TRANSLATIONS.items():
            for language in ("zh", "en"):
                self.assertIn(language, values, key)
                self.assertTrue(values[language].strip(), key)

    def test_language_switch_changes_text(self):
        language_manager.set_language("zh")
        self.assertEqual(tr("toolbar.import"), "导入图像")
        language_manager.set_language("en")
        self.assertEqual(tr("toolbar.import"), "Import Image")

    def test_all_presets_have_display_translations(self):
        for language in SUPPORTED_LANGUAGES:
            language_manager.set_language(language)
            for name in preset_names():
                self.assertNotEqual(preset_display_name(name), f"preset.{name}")


if __name__ == "__main__":
    unittest.main()
