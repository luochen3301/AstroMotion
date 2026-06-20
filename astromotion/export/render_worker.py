"""Qt thread worker for non-blocking video export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from astromotion.config import DEFAULT_DURATION_SECONDS, DEFAULT_FPS
from astromotion.export.gpu_offscreen_renderer import GpuOffscreenRenderer, GpuRendererUnavailable
from astromotion.export.moviepy_muxer import attach_audio
from astromotion.export.offscreen_renderer import OffscreenRenderer
from astromotion.export.video_encoder import VideoEncoder


@dataclass(slots=True)
class RenderSettings:
    output_path: Path
    preset: dict
    image_path: Path | None = None
    audio_path: Path | None = None
    width: int = 1920
    height: int = 1080
    duration_seconds: float = DEFAULT_DURATION_SECONDS
    fps: int = DEFAULT_FPS
    prefer_nvenc: bool = False
    prefer_gpu: bool = True
    color_fidelity: bool = True
    quality_crf: int = 14


class RenderWorker(QThread):
    progress_changed = Signal(int)
    render_finished = Signal(str)
    render_failed = Signal(str)

    def __init__(self, settings: RenderSettings) -> None:
        super().__init__()
        self.settings = settings
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            settings = self.settings
            total_frames = max(1, int(round(settings.duration_seconds * settings.fps)))
            renderer = self._create_renderer()
            dt = 1.0 / max(1, settings.fps)
            temp_video = (
                settings.output_path.with_name(f"{settings.output_path.stem}.video_only.mp4")
                if settings.audio_path
                else settings.output_path
            )

            with VideoEncoder(
                temp_video,
                settings.width,
                settings.height,
                settings.fps,
                prefer_nvenc=settings.prefer_nvenc,
                color_fidelity=settings.color_fidelity,
                quality_crf=settings.quality_crf,
            ) as encoder:
                for frame_index in range(total_frames):
                    if self._cancelled:
                        raise RuntimeError("Render cancelled.")
                    frame = renderer.render_frame(dt)
                    encoder.write_frame(frame)
                    progress = int(((frame_index + 1) / total_frames) * 100)
                    self.progress_changed.emit(progress)
            close = getattr(renderer, "close", None)
            if callable(close):
                close()

            final_path = attach_audio(temp_video, settings.audio_path, settings.output_path)
            if settings.audio_path and temp_video != settings.output_path:
                try:
                    temp_video.unlink(missing_ok=True)
                except OSError:
                    pass
            self.render_finished.emit(str(final_path))
        except Exception as exc:
            self.render_failed.emit(str(exc))

    def _create_renderer(self):
        settings = self.settings
        if settings.prefer_gpu:
            try:
                return GpuOffscreenRenderer(
                    width=settings.width,
                    height=settings.height,
                    preset=settings.preset,
                    image_path=settings.image_path,
                    duration_seconds=settings.duration_seconds,
                )
            except Exception as exc:
                # Keep export working on machines where offscreen OpenGL is not
                # available or driver setup is incomplete.
                if not isinstance(exc, GpuRendererUnavailable):
                    exc = GpuRendererUnavailable(str(exc))
        return OffscreenRenderer(
            width=settings.width,
            height=settings.height,
            preset=settings.preset,
            image_path=settings.image_path,
            duration_seconds=settings.duration_seconds,
        )
