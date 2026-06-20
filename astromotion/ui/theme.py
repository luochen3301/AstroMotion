"""Central dark theme tokens and QSS."""

from __future__ import annotations


TOKENS = {
    "bg": "#070a0f",
    "surface": "#101823",
    "surface_2": "#152131",
    "surface_3": "#1b2a3d",
    "surface_4": "#29405a",
    "border": "#2b3b50",
    "border_hot": "#5bd6ff",
    "text": "#eef4ff",
    "muted": "#93a2b8",
    "accent": "#66d9ff",
    "accent_2": "#9cc7ff",
    "danger": "#ff6b8a",
    "disabled": "#3a4352",
}


def app_stylesheet() -> str:
    t = TOKENS
    return f"""
    QWidget {{
        color: {t["text"]};
        font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
        font-size: 13px;
    }}
    QMainWindow, QDialog, QWidget#AppRoot, QWidget#AdvancedSettingsPanel, QWidget#SettingsContent {{
        background: {t["bg"]};
    }}
    QFrame#TopBar, QFrame#PlaybackBar {{
        background: {t["surface"]};
        border: 1px solid {t["border"]};
        border-radius: 8px;
    }}
    QLabel#AppTitle {{
        background-color: transparent;
        font-size: 20px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: 0px;
    }}
    QLabel#PanelTitle {{
        background-color: transparent;
        font-size: 16px;
        font-weight: 800;
        color: #ffffff;
    }}
    QLabel#GroupTitle {{
        background-color: transparent;
        font-size: 13px;
        font-weight: 700;
        color: {t["accent_2"]};
    }}
    QLabel {{
        background-color: transparent;
        color: {t["text"]};
    }}
    QLabel#FormLabel {{
        background-color: transparent;
        color: {t["text"]};
        padding: 0px;
    }}
    QLabel#MutedLabel {{
        background-color: transparent;
        color: {t["muted"]};
    }}
    QLabel#StatusPill {{
        background: {t["surface_2"]};
        border: 1px solid {t["border"]};
        border-radius: 8px;
        padding: 6px 10px;
        color: {t["accent_2"]};
    }}
    QFrame#PreviewFrame {{
        background: #030509;
        border: 1px solid {t["border"]};
        border-radius: 8px;
    }}
    QFrame#SettingsGroup {{
        background-color: {t["surface"]};
        border: 1px solid {t["border"]};
        border-radius: 8px;
    }}
    QWidget#SliderRow {{
        background-color: transparent;
    }}
    QScrollArea#SettingsScroll {{
        background-color: transparent;
        border: 0;
    }}
    QScrollArea#SettingsScroll > QWidget > QWidget {{
        background-color: transparent;
    }}
    QPushButton {{
        background: {t["surface_2"]};
        border: 1px solid {t["border"]};
        border-radius: 7px;
        padding: 8px 12px;
        color: {t["text"]};
        font-weight: 600;
    }}
    QPushButton#ImportButton {{
        padding-left: 18px;
        padding-right: 18px;
    }}
    QPushButton#PlayButton {{
        min-width: 78px;
    }}
    QPushButton#PresetButton {{
        min-height: 44px;
        background: {t["surface_2"]};
    }}
    QPushButton#PresetButton:hover {{
        background: {t["surface_3"]};
    }}
    QPushButton#PresetButton:checked {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #244057, stop:1 #1b3045);
        border-color: {t["accent"]};
        color: white;
    }}
    QPushButton:hover {{
        background: {t["surface_3"]};
        border-color: {t["border_hot"]};
    }}
    QPushButton:checked {{
        background: {t["surface_4"]};
        border-color: {t["accent"]};
        color: white;
    }}
    QPushButton#RenderButton {{
        background: {t["accent"]};
        color: #041018;
        border: 0;
        font-size: 15px;
        font-weight: 800;
        padding: 12px 16px;
    }}
    QPushButton#RenderButton:hover {{
        background: #8ce6ff;
    }}
    QPushButton:disabled {{
        background: {t["disabled"]};
        color: {t["muted"]};
        border-color: {t["disabled"]};
    }}
    QDockWidget {{
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        background: {t["surface"]};
        border-left: 1px solid {t["border"]};
    }}
    QDockWidget::title {{
        background: {t["surface"]};
        padding: 9px;
        text-align: left;
        font-weight: 700;
        color: {t["text"]};
    }}
    QSlider::groove:horizontal {{
        height: 5px;
        background: #243247;
        border-radius: 3px;
    }}
    QSlider::sub-page:horizontal {{
        background: {t["accent"]};
        border-radius: 3px;
    }}
    QSlider::add-page:horizontal {{
        background: #243247;
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
        background: {t["accent"]};
        border: 1px solid #94eeff;
    }}
    QScrollBar:vertical {{
        width: 10px;
        margin: 0px;
        background: transparent;
    }}
    QScrollBar::handle:vertical {{
        min-height: 32px;
        background: #2a3c52;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #3b526d;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
        border: 0px;
        background: transparent;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {t["surface_2"]};
        border: 1px solid {t["border"]};
        border-radius: 6px;
        padding: 5px 8px;
        min-width: 82px;
    }}
    QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
        border-color: #3f5672;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border-color: {t["accent"]};
    }}
    QComboBox::drop-down {{
        border: 0;
        width: 24px;
    }}
    QComboBox#TopLanguageCombo {{
        min-width: 118px;
    }}
    QComboBox QAbstractItemView {{
        background: {t["surface_2"]};
        border: 1px solid {t["border"]};
        selection-background-color: {t["surface_4"]};
    }}
    QProgressBar {{
        border: 1px solid {t["border"]};
        border-radius: 6px;
        background: {t["surface_2"]};
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {t["accent"]};
        border-radius: 5px;
    }}
    """
