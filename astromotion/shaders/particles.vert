#version 330 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec4 a_color;
layout(location = 2) in vec2 a_life;
layout(location = 3) in float a_size;
layout(location = 4) in vec3 a_velocity;
layout(location = 5) in vec3 a_previous_position;

uniform mat4 u_view_projection;
uniform float u_motion_blur;
uniform float u_depth_strength;
uniform float u_focal_length;

out vec4 v_color;
out float v_age;
out float v_velocity_len;
out float v_depth_gain;

void main() {
    float max_life = max(a_life.y, 0.0001);
    v_age = clamp(a_life.x / max_life, 0.0, 1.0);
    v_color = a_color;
    v_velocity_len = length(a_velocity);

    vec3 projected = a_position;
    v_depth_gain = 1.0;
    if (u_depth_strength > 0.001) {
        float z = max(a_position.z, 0.08);
        float perspective = u_focal_length / z;
        projected.xy = a_position.xy * perspective * u_depth_strength;
        projected.z = 0.0;
        v_depth_gain = clamp(0.8 / z, 0.35, 3.2);
    }

    gl_Position = u_view_projection * vec4(projected, 1.0);

    // Keep star sprites compact. Trails carry the sense of motion; the point
    // itself should read as a sharp star core, not a large soft blob.
    float stretch_hint = 1.0 + clamp(v_velocity_len * 0.10, 0.0, 1.8) * u_motion_blur;
    gl_PointSize = clamp(a_size * stretch_hint * v_depth_gain, 1.0, 96.0);
}
