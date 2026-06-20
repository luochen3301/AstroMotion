"""Build a portable Windows release package for AstroMotion."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V2.0"
APP_NAME = "AstroMotion"
RELEASE_DIR = ROOT / "release"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
PACKAGE_NAME = f"{APP_NAME}-{VERSION}-windows-x64"
PACKAGE_DIR = RELEASE_DIR / PACKAGE_NAME
ZIP_PATH = RELEASE_DIR / f"{PACKAGE_NAME}.zip"


def main() -> int:
    os.chdir(ROOT)
    _run([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    _run([sys.executable, "-m", "compileall", "astromotion", "tests", "scripts"])
    _ensure_pyinstaller()

    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    RELEASE_DIR.mkdir(exist_ok=True)

    launcher = BUILD_DIR / "pyinstaller" / "astromotion_launcher.py"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        "from astromotion.app import main\nraise SystemExit(main())\n",
        encoding="utf-8",
    )

    add_data = f"{ROOT / 'astromotion' / 'shaders'}{os.pathsep}astromotion/shaders"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name",
        APP_NAME,
        "--paths",
        str(ROOT),
        "--add-data",
        add_data,
        "--hidden-import",
        "imageio_ffmpeg",
        "--hidden-import",
        "OpenGL.platform.win32",
        str(launcher),
    ]
    _run(command)

    dist_app = DIST_DIR / APP_NAME
    if not dist_app.exists():
        raise RuntimeError(f"PyInstaller output not found: {dist_app}")
    shutil.copytree(dist_app, PACKAGE_DIR)
    _copy_bootloader_exe(PACKAGE_DIR)
    _copy_ffmpeg(PACKAGE_DIR)
    _copy_docs(PACKAGE_DIR)
    _copy_bootloader_exe(PACKAGE_DIR)
    _zip_directory(PACKAGE_DIR, ZIP_PATH)
    _verify_release(PACKAGE_DIR, ZIP_PATH)
    print(f"Release package created: {ZIP_PATH}")
    return 0


def _run(command: list[str]) -> None:
    print(">", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "PyInstaller is not installed. Run: "
            f"{sys.executable} -m pip install pyinstaller"
        ) from exc


def _copy_ffmpeg(target_dir: Path) -> None:
    try:
        import imageio_ffmpeg

        ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        ffmpeg = None
    if ffmpeg and ffmpeg.exists():
        suffix = ".exe" if ffmpeg.suffix.lower() == ".exe" else ffmpeg.suffix
        shutil.copy2(ffmpeg, target_dir / f"ffmpeg{suffix}")


def _copy_bootloader_exe(target_dir: Path) -> None:
    target_exe = target_dir / f"{APP_NAME}.exe"
    if target_exe.exists():
        return
    candidates = [
        DIST_DIR / APP_NAME / f"{APP_NAME}.exe",
        BUILD_DIR / APP_NAME / f"{APP_NAME}.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            shutil.copy2(candidate, target_exe)
            return
    raise RuntimeError(f"Could not find {APP_NAME}.exe in PyInstaller output.")


def _copy_docs(target_dir: Path) -> None:
    for name in ("README.md", "RELEASE_NOTES.md", "DISTRIBUTION_README.md"):
        source = ROOT / name
        if source.exists():
            shutil.copy2(source, target_dir / name)


def _zip_directory(source_dir: Path, output_path: Path) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir.parent))


def _verify_release(package_dir: Path, zip_path: Path) -> None:
    required_files = [
        package_dir / f"{APP_NAME}.exe",
        package_dir / "README.md",
        package_dir / "RELEASE_NOTES.md",
        package_dir / "DISTRIBUTION_README.md",
    ]
    for path in required_files:
        if not path.exists():
            raise RuntimeError(f"Release package is missing required file: {path}")

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    required_archive_names = [
        f"{PACKAGE_NAME}/{APP_NAME}.exe",
        f"{PACKAGE_NAME}/README.md",
        f"{PACKAGE_NAME}/RELEASE_NOTES.md",
        f"{PACKAGE_NAME}/DISTRIBUTION_README.md",
    ]
    for name in required_archive_names:
        if name not in names:
            raise RuntimeError(f"Release ZIP is missing required file: {name}")
    if not any("astromotion/shaders/" in name.lower() for name in names):
        raise RuntimeError("Release ZIP is missing OpenGL shader resources.")


if __name__ == "__main__":
    raise SystemExit(main())
