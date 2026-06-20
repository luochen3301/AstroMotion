#version 430 core

// Compute Shader design sketch for the next performance step.
// The MVP keeps CPU simulation as the safe default and uploads VBO data each
// frame. This shader documents the SSBO layout needed to move update() fully
// onto GPU without changing preset data structures.

layout(local_size_x = 256) in;

struct Particle {
    vec4 position_life_current; // xyz + current life
    vec4 velocity_life_max;     // xyz + max life
    vec4 color;                 // rgba
    vec4 size_misc;             // size + reserved
};

layout(std430, binding = 0) buffer Particles {
    Particle particles[];
};

uniform uint u_count;
uniform float u_dt;
uniform float u_time;
uniform float u_turbulence;

float hash(vec3 p) {
    return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
}

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= u_count) {
        return;
    }

    Particle p = particles[id];
    vec3 pos = p.position_life_current.xyz;
    vec3 vel = p.velocity_life_max.xyz;

    vec3 wind = vec3(
        sin(pos.y * 7.7 + u_time * 0.61),
        cos(pos.x * 6.9 - u_time * 0.53),
        sin((pos.x + pos.y) * 3.1 + u_time * 0.19)
    );

    vel += wind * u_turbulence * 0.08 * u_dt;
    pos += vel * u_dt;
    p.position_life_current = vec4(pos, p.position_life_current.w + u_dt);
    p.velocity_life_max.xyz = vel;
    particles[id] = p;
}

