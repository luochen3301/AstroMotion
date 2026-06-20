#version 330 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec4 a_color;

uniform mat4 u_view_projection;
uniform float u_depth_strength;
uniform float u_focal_length;
uniform float u_trail_strength;
uniform float u_brightness;
uniform float u_color_intensity;

out vec4 v_color;

void main() {
    vec3 projected = a_position;
    float depth_gain = 1.0;
    if (u_depth_strength > 0.001) {
        float z = max(a_position.z, 0.08);
        float perspective = u_focal_length / z;
        projected.xy = a_position.xy * perspective * u_depth_strength;
        projected.z = 0.0;
        depth_gain = clamp(0.85 / z, 0.22, 2.2);
    }

    float color_keep = smoothstep(0.0, 1.0, u_color_intensity);
    float luma = dot(a_color.rgb, vec3(0.2126, 0.7152, 0.0722));
    vec3 trail_color = mix(vec3(luma), a_color.rgb, color_keep);
    v_color = vec4(trail_color * depth_gain * u_brightness, a_color.a * u_trail_strength * 0.72);
    gl_Position = u_view_projection * vec4(projected, 1.0);
}
