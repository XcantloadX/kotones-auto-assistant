"""KAA UI 固定路径集中管理。"""
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent
"""kaa UI 模块根目录。"""

QML_DIR = UI_DIR / 'qml'
"""KAA QML 根目录（shell QML 由 EuiShell 提供）。"""

ICON_PATH = UI_DIR / 'icon.png'
"""应用图标 PNG 路径。"""
