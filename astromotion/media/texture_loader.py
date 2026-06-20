"""OpenGL texture helpers."""

from __future__ import annotations

import numpy as np


def create_texture_from_rgb(image_rgb: np.ndarray) -> int:
    from OpenGL import GL

    image = np.ascontiguousarray(image_rgb[:, :, :3], dtype=np.uint8)
    texture = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
    GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
    GL.glTexImage2D(
        GL.GL_TEXTURE_2D,
        0,
        GL.GL_RGB8,
        int(image.shape[1]),
        int(image.shape[0]),
        0,
        GL.GL_RGB,
        GL.GL_UNSIGNED_BYTE,
        image,
    )
    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
    return int(texture)


def delete_texture(texture: int) -> None:
    if texture:
        from OpenGL import GL

        GL.glDeleteTextures([int(texture)])

