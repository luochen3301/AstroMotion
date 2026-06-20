"""Small PyOpenGL shader helpers.

Imports are intentionally local so non-GUI tests can import the package without
requiring a valid OpenGL context.
"""

from __future__ import annotations

from pathlib import Path


class ShaderCompileError(RuntimeError):
    pass


def shader_path(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "shaders" / name


def read_shader(name: str) -> str:
    return shader_path(name).read_text(encoding="utf-8")


def compile_program(vertex_source: str, fragment_source: str) -> int:
    from OpenGL import GL

    vertex = _compile_shader(GL.GL_VERTEX_SHADER, vertex_source)
    fragment = _compile_shader(GL.GL_FRAGMENT_SHADER, fragment_source)
    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex)
    GL.glAttachShader(program, fragment)
    GL.glLinkProgram(program)
    ok = GL.glGetProgramiv(program, GL.GL_LINK_STATUS)
    if not ok:
        log = GL.glGetProgramInfoLog(program).decode("utf-8", errors="replace")
        raise ShaderCompileError(log)
    GL.glDeleteShader(vertex)
    GL.glDeleteShader(fragment)
    return int(program)


def compile_compute_program(source: str) -> int:
    from OpenGL import GL

    shader = _compile_shader(GL.GL_COMPUTE_SHADER, source)
    program = GL.glCreateProgram()
    GL.glAttachShader(program, shader)
    GL.glLinkProgram(program)
    ok = GL.glGetProgramiv(program, GL.GL_LINK_STATUS)
    if not ok:
        log = GL.glGetProgramInfoLog(program).decode("utf-8", errors="replace")
        raise ShaderCompileError(log)
    GL.glDeleteShader(shader)
    return int(program)


def _compile_shader(shader_type: int, source: str) -> int:
    from OpenGL import GL

    shader = GL.glCreateShader(shader_type)
    GL.glShaderSource(shader, source)
    GL.glCompileShader(shader)
    ok = GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS)
    if not ok:
        log = GL.glGetShaderInfoLog(shader).decode("utf-8", errors="replace")
        raise ShaderCompileError(log)
    return int(shader)

