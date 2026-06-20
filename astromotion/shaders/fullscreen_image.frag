#version 330 core

in vec2 v_uv;

uniform sampler2D u_image;
uniform float u_zoom;
uniform float u_rotation_degrees;
uniform vec2 u_image_size;
uniform vec2 u_canvas_size;

out vec4 frag_color;

void main() {
    float angle = radians(u_rotation_degrees);
    float c = cos(angle);
    float s = sin(angle);
    vec2 centered_uv = v_uv - 0.5;
    vec2 rotated_uv = vec2(
        c * centered_uv.x + s * centered_uv.y,
        -s * centered_uv.x + c * centered_uv.y
    );
    vec2 canvas_uv = rotated_uv / max(u_zoom, 0.001) + 0.5;
    if (canvas_uv.x < 0.0 || canvas_uv.x > 1.0 || canvas_uv.y < 0.0 || canvas_uv.y > 1.0) {
        frag_color = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    float image_aspect = max(u_image_size.x, 1.0) / max(u_image_size.y, 1.0);
    float canvas_aspect = max(u_canvas_size.x, 1.0) / max(u_canvas_size.y, 1.0);
    vec2 fit_size = vec2(1.0, 1.0);
    if (canvas_aspect > image_aspect) {
        fit_size.x = image_aspect / canvas_aspect;
    } else {
        fit_size.y = canvas_aspect / image_aspect;
    }
    vec2 fit_origin = (vec2(1.0, 1.0) - fit_size) * 0.5;
    if (canvas_uv.x < fit_origin.x || canvas_uv.x > fit_origin.x + fit_size.x
        || canvas_uv.y < fit_origin.y || canvas_uv.y > fit_origin.y + fit_size.y) {
        frag_color = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    vec2 image_uv = (canvas_uv - fit_origin) / fit_size;
    vec3 color = texture(u_image, image_uv).rgb;
    frag_color = vec4(color, 1.0);
}
