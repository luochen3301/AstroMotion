"""Small runtime translation layer for AstroMotion."""

from __future__ import annotations

from PySide6.QtCore import QObject, QLocale, Signal


SUPPORTED_LANGUAGES = ("auto", "zh", "en")


TRANSLATIONS: dict[str, dict[str, str]] = {
    "app.title": {"zh": "AstroMotion", "en": "AstroMotion"},
    "app.subtitle": {"zh": "深空照片动态视频工作台", "en": "Deep-sky motion video workstation"},
    "toolbar.import": {"zh": "导入图像", "en": "Import Image"},
    "toolbar.no_image": {"zh": "未导入图像", "en": "No image loaded"},
    "toolbar.ready": {"zh": "预览就绪", "en": "Preview ready"},
    "toolbar.source_stars": {"zh": "已提取 {count} 个真实星点", "en": "{count} real stars extracted"},
    "toolbar.generated_stars": {"zh": "真实星点不足，使用生成星场", "en": "Using generated stars"},
    "play.pause": {"zh": "暂停", "en": "Pause"},
    "play.play": {"zh": "播放", "en": "Play"},
    "dock.advanced": {"zh": "高级设置", "en": "Advanced Settings"},
    "dialog.import_title": {"zh": "导入深空图像", "en": "Import deep-sky image"},
    "dialog.import_failed": {"zh": "图像导入失败：", "en": "Image import failed:"},
    "dialog.render_title": {"zh": "渲染视频", "en": "Render Video"},
    "dialog.render_failed": {"zh": "视频导出失败：", "en": "Video export failed:"},
    "dialog.render_success": {"zh": "视频导出成功！", "en": "Video exported successfully."},
    "dialog.open_folder": {"zh": "打开所在文件夹", "en": "Open Folder"},
    "panel.title": {"zh": "高级设置", "en": "Advanced Settings"},
    "panel.collapse": {"zh": "收起", "en": "Collapse"},
    "panel.expand": {"zh": "展开", "en": "Expand"},
    "panel.group.particles": {"zh": "粒子", "en": "Particles"},
    "panel.group.source": {"zh": "真实星点", "en": "Real Stars"},
    "panel.group.motion": {"zh": "运镜", "en": "Camera Motion"},
    "panel.group.export": {"zh": "导出", "en": "Export"},
    "language.auto": {"zh": "跟随系统", "en": "System"},
    "language.zh": {"zh": "中文", "en": "Chinese"},
    "language.en": {"zh": "English", "en": "English"},
    "setting.particle_count": {"zh": "粒子数量", "en": "Particle Count"},
    "setting.speed": {"zh": "飞行速度", "en": "Flight Speed"},
    "setting.size": {"zh": "粒子大小", "en": "Particle Size"},
    "setting.glow": {"zh": "发光强度", "en": "Glow"},
    "setting.brightness": {"zh": "粒子亮度", "en": "Particle Brightness"},
    "setting.color_intensity": {"zh": "星点色彩", "en": "Star Color"},
    "setting.opacity": {"zh": "透明度", "en": "Opacity"},
    "setting.turbulence": {"zh": "风场干扰", "en": "Turbulence"},
    "setting.star_detection_sensitivity": {"zh": "识别敏感度", "en": "Detection Sensitivity"},
    "setting.source_star_strength": {"zh": "真实星点强度", "en": "Real Star Strength"},
    "setting.zoom_start": {"zh": "初始大小", "en": "Start Scale"},
    "setting.zoom_end": {"zh": "目标大小", "en": "Target Scale"},
    "setting.zoom_speed": {"zh": "缩放速度", "en": "Zoom Speed"},
    "setting.rotation_degrees": {"zh": "旋转角度", "en": "Rotation"},
    "setting.trail_length": {"zh": "拖尾长度", "en": "Trail Length"},
    "setting.depth_strength": {"zh": "景深强度", "en": "Depth Strength"},
    "setting.duration": {"zh": "时长 (s)", "en": "Duration (s)"},
    "setting.fps": {"zh": "帧率 (FPS)", "en": "Frame Rate (FPS)"},
    "setting.resolution": {"zh": "导出分辨率", "en": "Export Resolution"},
    "resolution.source": {"zh": "跟随原图", "en": "Match Source"},
    "resolution.2k": {"zh": "2K (2560 x 1440)", "en": "2K (2560 x 1440)"},
    "resolution.4k": {"zh": "4K (3840 x 2160)", "en": "4K (3840 x 2160)"},
    "export.hint": {"zh": "输出：MP4", "en": "Output: MP4"},
    "export.render": {"zh": "一键渲染导出", "en": "Render Video"},
    "progress.title": {"zh": "正在渲染", "en": "Rendering"},
    "progress.label": {"zh": "正在导出视频", "en": "Exporting video"},
    "preset.Deep Space Flythrough": {"zh": "深空飞行", "en": "Deep Space Flythrough"},
    "preset.Cinematic Star Drift": {"zh": "电影星流", "en": "Cinematic Star Drift"},
    "preset.Nebula Close Pass": {"zh": "星云近景", "en": "Nebula Close Pass"},
    "preset.Rotating Nebula Push-in": {"zh": "旋转星云推进", "en": "Rotating Nebula Push-in"},
}


class LanguageManager(QObject):
    """Runtime language state with a Qt signal for widget refresh."""

    language_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.current_language = "auto"

    def set_language(self, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            language = "auto"
        if language == self.current_language:
            return
        self.current_language = language
        self.language_changed.emit(language)

    def resolved_language(self) -> str:
        if self.current_language != "auto":
            return self.current_language
        system_language = QLocale.system().language()
        if system_language in {
            QLocale.Language.Chinese,
            QLocale.Language.Cantonese,
        }:
            return "zh"
        return "en"


language_manager = LanguageManager()


def tr(key: str) -> str:
    language = language_manager.resolved_language()
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(language) or entry.get("en") or key


def preset_display_name(name: str) -> str:
    return tr(f"preset.{name}")
