"""Optional MoviePy audio muxing."""

from __future__ import annotations

from pathlib import Path


def attach_audio(video_path: str | Path, audio_path: str | Path | None, output_path: str | Path) -> Path:
    if audio_path is None:
        return Path(video_path)

    try:
        from moviepy.editor import AudioFileClip, VideoFileClip
    except ImportError as exc:
        raise RuntimeError("MoviePy is required to attach audio.") from exc

    output = Path(output_path)
    with VideoFileClip(str(video_path)) as video, AudioFileClip(str(audio_path)) as audio:
        final = video.set_audio(audio.subclip(0, min(audio.duration, video.duration)))
        final.write_videofile(str(output), codec="libx264", audio_codec="aac")
    return output

