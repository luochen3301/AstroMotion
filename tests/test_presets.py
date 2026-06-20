import unittest

from astromotion.presets import PRESETS, default_preset_name, get_preset, normalize_preset


class PresetTests(unittest.TestCase):
    def test_required_presets_exist(self):
        self.assertEqual(
            set(PRESETS),
            {
                "Deep Space Flythrough",
                "Cinematic Star Drift",
                "Nebula Close Pass",
                "Rotating Nebula Push-in",
            },
        )
        self.assertIn("Deep Space Flythrough", PRESETS)
        self.assertIn("Cinematic Star Drift", PRESETS)
        self.assertIn("Nebula Close Pass", PRESETS)
        self.assertIn("Rotating Nebula Push-in", PRESETS)

    def test_deep_space_is_default(self):
        self.assertEqual(default_preset_name(), "Deep Space Flythrough")
        self.assertEqual(get_preset()["name"], "Deep Space Flythrough")

    def test_deep_space_defaults_are_subtle(self):
        preset = get_preset("Deep Space Flythrough")
        self.assertLessEqual(preset["particle_count"], 25_000)
        self.assertLessEqual(preset["size"], 1.6)
        self.assertLessEqual(preset["glow"], 0.9)
        self.assertGreaterEqual(preset["brightness"], 1.6)
        self.assertGreaterEqual(preset["color_intensity"], 1.0)
        self.assertLessEqual(preset["trail_length"], 0.3)
        self.assertEqual(preset["zoom_start"], 1.0)
        self.assertEqual(preset["zoom_speed"], 1.0)
        self.assertEqual(preset["rotation_degrees"], 0.0)

    def test_cinematic_star_drift_is_slower(self):
        default = get_preset("Deep Space Flythrough")
        cinematic = get_preset("Cinematic Star Drift")
        self.assertLess(cinematic["particle_count"], default["particle_count"])
        self.assertLess(cinematic["speed"], default["speed"])
        self.assertLess(cinematic["zoom_speed"], default["zoom_speed"])
        self.assertGreater(cinematic["trail_length"], default["trail_length"])
        self.assertLessEqual(cinematic["size"], 1.7)

    def test_nebula_close_pass_matches_saved_settings(self):
        preset = get_preset("Nebula Close Pass")
        self.assertEqual(preset["particle_count"], 9_779)
        self.assertAlmostEqual(preset["speed"], 0.07)
        self.assertAlmostEqual(preset["size"], 1.10)
        self.assertAlmostEqual(preset["glow"], 0.85)
        self.assertAlmostEqual(preset["brightness"], 1.75)
        self.assertAlmostEqual(preset["color_intensity"], 4.05)
        self.assertAlmostEqual(preset["opacity"], 0.48)
        self.assertAlmostEqual(preset["turbulence"], 0.05)
        self.assertAlmostEqual(preset["zoom_start"], 1.0)
        self.assertAlmostEqual(preset["zoom_end"], 1.40)
        self.assertAlmostEqual(preset["zoom_speed"], 1.0)
        self.assertAlmostEqual(preset["trail_length"], 0.16)
        self.assertAlmostEqual(preset["depth_strength"], 0.90)
        self.assertAlmostEqual(preset["rotation_degrees"], 0.0)

    def test_rotating_nebula_push_in_adds_rotation(self):
        preset = get_preset("Rotating Nebula Push-in")
        self.assertEqual(preset["particle_count"], 9_000)
        self.assertAlmostEqual(preset["speed"], 0.05)
        self.assertAlmostEqual(preset["zoom_end"], 1.28)
        self.assertAlmostEqual(preset["rotation_degrees"], 4.0)

    def test_presets_have_required_fields(self):
        required = {
            "particle_count",
            "emitter",
            "speed",
            "size",
            "glow",
            "brightness",
            "color_intensity",
            "opacity",
            "turbulence",
            "lifetime",
            "motion_blur",
            "zoom_start",
            "zoom_end",
            "zoom_speed",
            "rotation_degrees",
            "trail_length",
            "depth_range",
            "depth_strength",
        }
        for preset in PRESETS.values():
            self.assertTrue(required.issubset(preset.keys()))

    def test_get_preset_returns_copy(self):
        preset = get_preset("Deep Space Flythrough")
        preset["particle_count"] = 1
        self.assertNotEqual(get_preset("Deep Space Flythrough")["particle_count"], 1)

    def test_normalize_clamps_values(self):
        preset = normalize_preset({"particle_count": -1, "opacity": 5.0, "lifetime": 0.0})
        self.assertEqual(preset["particle_count"], 1)
        self.assertEqual(preset["opacity"], 1.0)
        self.assertGreaterEqual(preset["lifetime"], 0.05)

    def test_brightness_is_clamped(self):
        preset = normalize_preset({"brightness": 99.0})
        self.assertEqual(preset["brightness"], 5.0)
        preset = normalize_preset({"brightness": -1.0})
        self.assertEqual(preset["brightness"], 0.0)

    def test_color_intensity_is_clamped(self):
        preset = normalize_preset({"color_intensity": 99.0})
        self.assertEqual(preset["color_intensity"], 5.0)
        preset = normalize_preset({"color_intensity": -1.0})
        self.assertEqual(preset["color_intensity"], 0.0)

    def test_rotation_degrees_is_clamped(self):
        preset = normalize_preset({"rotation_degrees": 99.0})
        self.assertEqual(preset["rotation_degrees"], 20.0)
        preset = normalize_preset({"rotation_degrees": -99.0})
        self.assertEqual(preset["rotation_degrees"], -20.0)


if __name__ == "__main__":
    unittest.main()
