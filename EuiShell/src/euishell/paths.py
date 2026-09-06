"""框架内固定路径的集中管理。禁止在其他位置散落路径字符串字面量。"""
from importlib.resources import files
from pathlib import Path

from euishell.exceptions import MissingResourceError


def _package_dir() -> Path:
    """返回 euishell 包所在目录。"""
    return Path(str(files('euishell')))


PACKAGE_DIR: Path = _package_dir()
"""euishell 包根目录。"""

QML_DIR: Path = PACKAGE_DIR / 'qml'
"""QML import path 根目录（其下 EuiShell/ 为命名模块目录）。"""

QML_MODULE_DIR: Path = QML_DIR / 'EuiShell'
"""EuiShell 命名模块目录（main.qml 与全部 Shell QML 所在）。"""

FONTS_DIR: Path = PACKAGE_DIR / 'fonts'
"""内置字体目录。"""

FLUENT_ICON_FONT_PATH: Path = FONTS_DIR / 'FluentSystemIcons-Regular.ttf'
"""Fluent 系统图标字体文件路径。"""


def file_url(path: Path) -> str:
    """将本地路径转换为 QML 可用的 file:// URL。

    :param path: 本地文件路径
    :returns: 以 file:/// 开头、使用正斜杠的 URL 字符串
    """
    return 'file:///' + str(path.resolve()).replace('\\', '/')


def qml_url(path: Path) -> str:
    """将 QML 文件路径转换为 Loader 可用的 URL 字符串。

    :param path: QML 文件路径
    :returns: file:// URL 字符串
    """
    return file_url(path)


if not FLUENT_ICON_FONT_PATH.exists():
    raise MissingResourceError(f'内置字体缺失: {FLUENT_ICON_FONT_PATH}')
