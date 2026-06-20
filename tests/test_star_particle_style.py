import unittest
from pathlib import Path


class StarParticleStyleTests(unittest.TestCase):
    def test_particle_shader_uses_sharp_star_core(self):
        shader = Path("astromotion/shaders/particles.frag").read_text(encoding="utf-8")
        self.assertIn("star_core", shader)
        self.assertIn("18.0", shader)
        self.assertIn("u_color_intensity", shader)
        self.assertIn("color_keep", shader)
        self.assertNotIn("white_core", shader)
        self.assertNotIn("star_core * 0.54", shader)
        self.assertNotIn("star_core * 0.72", shader)
        self.assertNotIn("mix(v_color.rgb, vec3(1.0)", shader)

    def test_trail_shader_uses_color_intensity(self):
        shader = Path("astromotion/shaders/trail.vert").read_text(encoding="utf-8")
        self.assertIn("u_color_intensity", shader)
        self.assertIn("color_keep", shader)
        self.assertNotIn("vec3(0.92, 0.96, 1.0), 0.35", shader)

    def test_vertex_shader_keeps_star_sprites_compact(self):
        shader = Path("astromotion/shaders/particles.vert").read_text(encoding="utf-8")
        self.assertIn("clamp(v_velocity_len * 0.10", shader)
        self.assertNotIn("v_velocity_len * 0.35", shader)


if __name__ == "__main__":
    unittest.main()
