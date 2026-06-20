"""MP4 encoding helpers with FFmpeg H.264 compatibility defaults."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import numpy as np


NVENC_ENCODERS = ("h264_nvenc",)
RGB_ENCODER = "libx264rgb"
COMPATIBILITY_FILTER = (
    "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,"
    "format=yuv420p,"
    "setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709"
)
COLOR_FIDELITY_YUV_FILTER = "scale=in_range=pc:out_range=pc:out_color_matrix=bt709,format=yuv444p"


def find_ffmpeg_executable() -> str | None:
    packaged_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None
    if packaged_dir is not None:
        for candidate in (packaged_dir / "ffmpeg.exe", packaged_dir / "ffmpeg"):
            if candidate.exists():
                return str(candidate)

    path_ffmpeg = shutil.which("ffmpeg")
    if path_ffmpeg:
        return path_ffmpeg
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def list_ffmpeg_encoders(ffmpeg_path: str | None = None) -> set[str]:
    executable = ffmpeg_path or find_ffmpeg_executable()
    if not executable:
        return set()
    proc = subprocess.run(
        [executable, "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return set()
    encoders: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("V"):
            encoders.add(parts[1])
    return encoders


def choose_ffmpeg_encoder(available: Iterable[str], prefer_nvenc: bool = True) -> str:
    available_set = set(available)
    if prefer_nvenc:
        for encoder in NVENC_ENCODERS:
            if encoder in available_set:
                return encoder
    if "libx264" in available_set:
        return "libx264"
    if "mpeg4" in available_set:
        return "mpeg4"
    return "libx264"


def choose_color_fidelity_encoder(available: Iterable[str], prefer_nvenc: bool = False) -> str:
    available_set = set(available)
    if RGB_ENCODER in available_set:
        return RGB_ENCODER
    if prefer_nvenc:
        for encoder in NVENC_ENCODERS:
            if encoder in available_set:
                return encoder
    if "libx264" in available_set:
        return "libx264"
    return RGB_ENCODER


class VideoEncoder:
    """Streaming RGB frame encoder.

    Frames are accepted as uint8 RGB arrays. FFmpeg receives rawvideo via stdin,
    which avoids writing thousands of temporary images to disk.
    """

    def __init__(
        self,
        output_path: str | Path,
        width: int,
        height: int,
        fps: int,
        prefer_nvenc: bool = True,
        ffmpeg_path: str | None = None,
        color_fidelity: bool = False,
        quality_crf: int = 18,
    ) -> None:
        self.output_path = Path(output_path)
        self.width = int(width) - (int(width) % 2)
        self.height = int(height) - (int(height) % 2)
        self.fps = int(fps)
        self.prefer_nvenc = prefer_nvenc
        self.ffmpeg_path = ffmpeg_path or find_ffmpeg_executable()
        self.color_fidelity = bool(color_fidelity)
        self.quality_crf = int(min(30, max(0, quality_crf)))
        self.encoder_name = "unopened"
        self._proc: subprocess.Popen[bytes] | None = None
        self._cv_writer = None

    def open(self) -> "VideoEncoder":
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.ffmpeg_path:
            available = list_ffmpeg_encoders(self.ffmpeg_path)
            if self.color_fidelity:
                self.encoder_name = choose_color_fidelity_encoder(available, self.prefer_nvenc)
            else:
                self.encoder_name = choose_ffmpeg_encoder(available, self.prefer_nvenc)
            command = self._build_ffmpeg_command()
            self._proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return self

        if self.color_fidelity:
            raise RuntimeError(
                "Color-fidelity export requires FFmpeg. Install FFmpeg or use compatibility mode; "
                "OpenCV/mp4v can visibly shift deep-sky image colors."
            )

        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("Neither FFmpeg nor OpenCV VideoWriter is available.") from exc

        self.encoder_name = "opencv-mp4v"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._cv_writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            float(self.fps),
            (self.width, self.height),
        )
        if not self._cv_writer.isOpened():
            raise RuntimeError("Could not open OpenCV VideoWriter for MP4 output.")
        return self

    def write_frame(self, frame_rgb: np.ndarray) -> None:
        frame = np.asarray(frame_rgb)
        if frame.shape[0] != self.height or frame.shape[1] != self.width:
            frame = frame[: self.height, : self.width]
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)

        if self._proc is not None:
            if self._proc.stdin is None:
                raise RuntimeError("FFmpeg stdin is not available.")
            self._proc.stdin.write(np.ascontiguousarray(frame[:, :, :3]).tobytes())
            return

        if self._cv_writer is not None:
            import cv2

            self._cv_writer.write(cv2.cvtColor(frame[:, :, :3], cv2.COLOR_RGB2BGR))
            return

        raise RuntimeError("VideoEncoder.open() must be called before write_frame().")

    def _build_ffmpeg_command(self) -> list[str]:
        if not self.ffmpeg_path:
            raise RuntimeError("FFmpeg path is not configured.")
        return [
            self.ffmpeg_path,
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{self.width}x{self.height}",
            "-r",
            str(self.fps),
            "-i",
            "-",
            "-an",
            *self._ffmpeg_output_args(),
            str(self.output_path),
        ]

    def _ffmpeg_output_args(self) -> list[str]:
        if self.color_fidelity and self.encoder_name == RGB_ENCODER:
            return [
                "-c:v",
                RGB_ENCODER,
                "-pix_fmt",
                "rgb24",
                "-crf",
                str(self.quality_crf),
                "-preset",
                "slow",
                "-color_range",
                "pc",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "iec61966-2-1",
                "-colorspace",
                "rgb",
                "-movflags",
                "+faststart",
            ]

        if self.color_fidelity:
            return [
                "-vf",
                COLOR_FIDELITY_YUV_FILTER,
                "-c:v",
                self.encoder_name,
                "-pix_fmt",
                "yuv444p",
                "-color_range",
                "pc",
                "-colorspace",
                "bt709",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "iec61966-2-1",
                "-movflags",
                "+faststart",
            ]

        if self.encoder_name == "libx264":
            return [
                "-vf",
                COMPATIBILITY_FILTER,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "high",
                "-crf",
                str(self.quality_crf),
                "-preset",
                "medium",
                "-tag:v",
                "avc1",
                "-colorspace",
                "bt709",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "bt709",
                "-color_range",
                "tv",
                "-movflags",
                "+faststart",
            ]

        if self.encoder_name == "h264_nvenc":
            return [
                "-vf",
                COMPATIBILITY_FILTER,
                "-c:v",
                "h264_nvenc",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "high",
                "-rc:v",
                "vbr",
                "-cq:v",
                str(self.quality_crf),
                "-b:v",
                "0",
                "-tag:v",
                "avc1",
                "-colorspace",
                "bt709",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "bt709",
                "-color_range",
                "tv",
                "-movflags",
                "+faststart",
            ]

        return [
            "-vf",
            COMPATIBILITY_FILTER,
            "-c:v",
            self.encoder_name,
            "-pix_fmt",
            "yuv420p",
            "-q:v",
            "3",
            "-tag:v",
            "mp4v",
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "iec61966-2-1",
            "-color_range",
            "tv",
            "-movflags",
            "+faststart",
        ]

    def close(self) -> None:
        if self._proc is not None:
            proc = self._proc
            self._proc = None
            stderr = b""
            if proc.stdin:
                proc.stdin.close()
            if proc.stderr:
                stderr = proc.stderr.read()
            return_code = proc.wait()
            if return_code != 0:
                message = stderr.decode("utf-8", errors="replace")[-4000:]
                raise RuntimeError(f"FFmpeg failed with exit code {return_code}: {message}")

        if self._cv_writer is not None:
            self._cv_writer.release()
            self._cv_writer = None

    def __enter__(self) -> "VideoEncoder":
        return self.open()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
