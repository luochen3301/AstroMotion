"""Particle buffer containers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class ParticleBuffers:
    """Structure-of-arrays particle data optimized for vectorized NumPy updates."""

    positions: np.ndarray
    previous_positions: np.ndarray
    velocities: np.ndarray
    colors: np.ndarray
    life: np.ndarray
    sizes: np.ndarray

    @property
    def capacity(self) -> int:
        return int(self.positions.shape[0])


def create_empty_buffers(capacity: int) -> ParticleBuffers:
    capacity = int(capacity)
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    return ParticleBuffers(
        positions=np.zeros((capacity, 3), dtype=np.float32),
        previous_positions=np.zeros((capacity, 3), dtype=np.float32),
        velocities=np.zeros((capacity, 3), dtype=np.float32),
        colors=np.zeros((capacity, 4), dtype=np.float32),
        life=np.zeros((capacity, 2), dtype=np.float32),
        sizes=np.ones((capacity,), dtype=np.float32),
    )


def interleave_for_gpu(buffers: ParticleBuffers, count: int) -> np.ndarray:
    """Pack active particles into one VBO-friendly float32 matrix.

    Layout per particle:
    position.xyz, color.rgba, life.current/max, size, velocity.xyz, previous.xyz
    """

    count = int(count)
    packed = np.empty((count, 16), dtype=np.float32)
    packed[:, 0:3] = buffers.positions[:count]
    packed[:, 3:7] = buffers.colors[:count]
    packed[:, 7:9] = buffers.life[:count]
    packed[:, 9] = buffers.sizes[:count]
    packed[:, 10:13] = buffers.velocities[:count]
    packed[:, 13:16] = buffers.previous_positions[:count]
    return packed


def interleave_trails_for_gpu(buffers: ParticleBuffers, count: int) -> np.ndarray:
    """Return 2 vertices per particle for GL_LINES trail rendering.

    Layout per vertex: position.xyz, color.rgba. The first vertex is the older
    trail endpoint with lower alpha; the second is the current particle.
    """

    count = int(count)
    packed = np.empty((count * 2, 7), dtype=np.float32)
    packed[0::2, 0:3] = buffers.previous_positions[:count]
    packed[1::2, 0:3] = buffers.positions[:count]
    packed[0::2, 3:7] = buffers.colors[:count]
    packed[1::2, 3:7] = buffers.colors[:count]
    packed[0::2, 6] *= 0.18
    return packed
