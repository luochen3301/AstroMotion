#version 330 core

in vec4 v_color;
in float v_age;
in float v_velocity_len;
in float v_depth_gain;

uniform float u_glow;
uniform float u_motion_blur;
uniform float u_brightness;
uniform float u_color_intensity;

out vec4 frag_color;

void main() {
    vec2 uv = gl_PointCoord * 2.0 - 1.0;
    float radius = length(uv);
    float star_core = exp(-radius * radius * 18.0);
    float star_halo = exp(-radius * radius * 5.2) * 0.26;
    float star_alpha = star_core + star_halo;
    float warp_boost = 1.0 + u_motion_blur * clamp(v_velocity_len * 0.12, 0.0, 1.6);
    float alpha = v_color.a * star_alpha * warp_boost * clamp(v_depth_gain, 0.45, 1.65);
    float color_keep = smoothstep(0.0, 1.0, u_color_intensity);
    float luma = dot(v_color.rgb, vec3(0.2126, 0.7152, 0.0722));
    vec3 star_color = mix(vec3(luma), v_color.rgb, color_keep);
    float white_mix = clamp(star_core * 0.42 * (1.0 - color_keep), 0.0, 0.42);
    vec3 core_color = mix(star_color, vec3(max(max(star_color.r, star_color.g), star_color.b)), white_mix);
    vec3 rgb = core_color * u_brightness * (0.75 + u_glow * 0.55) * clamp(v_depth_gain, 0.65, 2.4);
    frag_color = vec4(rgb, alpha);
}
