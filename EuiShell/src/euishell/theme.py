"""外观（主题色 / 色彩方案 / 窗口样式）控制器与应用辅助。"""
import logging
import sys

from PySide6.QtCore import Property, Qt, QObject, Signal, Slot
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from euishell.session import AppearanceSettingsStore

if sys.platform == 'win32':
    from euishell.win32 import resolve_window_style

logger = logging.getLogger(__name__)

_VALID_COLOR_SCHEMES = ('auto', 'light', 'dark')


def apply_color_scheme(app: QApplication, color_scheme: str) -> None:
    """将色彩方案应用到 QApplication。

    :param app: 应用实例
    :param color_scheme: 'auto' | 'light' | 'dark'；非法值忽略
    """
    if color_scheme not in _VALID_COLOR_SCHEMES:
        logger.warning('Invalid color scheme: %s', color_scheme)
        return
    style_hints = app.styleHints()
    unset_color_scheme = getattr(style_hints, 'unsetColorScheme', None)
    set_color_scheme = getattr(style_hints, 'setColorScheme', None)
    if not callable(set_color_scheme) and not callable(unset_color_scheme):
        return
    if color_scheme == 'auto':
        if callable(unset_color_scheme):
            unset_color_scheme()
        elif callable(set_color_scheme):
            set_color_scheme(Qt.ColorScheme.Unknown)
    elif color_scheme == 'light':
        if callable(set_color_scheme):
            set_color_scheme(Qt.ColorScheme.Light)
    else:
        if callable(set_color_scheme):
            set_color_scheme(Qt.ColorScheme.Dark)


def apply_theme_color(app: QApplication, color_value: str | None) -> None:
    """将主题色应用到 QApplication palette。

    :param app: 应用实例
    :param color_value: #RRGGBB 颜色；None 或非法值忽略
    """
    if not color_value:
        return
    color = QColor(color_value)
    if not color.isValid():
        logger.warning('Invalid theme color: %s', color_value)
        return
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Highlight, color)
    accent_role = getattr(QPalette.ColorRole, 'Accent', None)
    if accent_role is not None:
        palette.setColor(accent_role, color)
    app.setPalette(palette)


class AppearanceController(QObject):
    """外观控制器：偏好 store 与 Shell 主题应用之间的桥梁。

    以 ``AppearanceController`` 名义注册为 QML 上下文属性；
    AppTheme.qml 由此读取 windowStyle。偏好保存后由 ShellApp 调用
    :meth:`refresh` 重新读取 store 并实时应用。
    """

    windowStyleChanged = Signal()
    colorSchemeChanged = Signal()
    themeColorChanged = Signal()

    def __init__(self, store: AppearanceSettingsStore, parent: QObject | None = None) -> None:
        """
        :param store: 外观配置存取后端
        :param parent: Qt 父对象
        """
        super().__init__(parent)
        self._store = store

    # ── Qt Properties ─────────────────────────────────────

    def _get_window_style(self) -> str:
        try:
            style = self._store.get_window_style()
        except Exception:
            logger.exception('Failed to read window style')
            return 'solid'
        if sys.platform != 'win32':
            return 'solid'
        if style in ('mica', 'acrylic', 'blur', 'solid'):
            return style
        if sys.getwindowsversion().build >= 22000:
            return 'mica'
        return 'solid'

    def _get_color_scheme(self) -> str:
        try:
            return self._store.get_color_scheme()
        except Exception:
            logger.exception('Failed to read color scheme')
            return 'auto'

    def _get_theme_color(self) -> str:
        try:
            return self._store.get_theme_color() or ''
        except Exception:
            logger.exception('Failed to read theme color')
            return ''

    windowStyle = Property(str, _get_window_style, notify=windowStyleChanged)
    colorScheme = Property(str, _get_color_scheme, notify=colorSchemeChanged)
    themeColor = Property(str, _get_theme_color, notify=themeColorChanged)

    # ── 应用逻辑 ──────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        """重新读取 store，广播变更并实时应用到 QApplication。"""
        app = QApplication.instance()
        self.windowStyleChanged.emit()
        self.colorSchemeChanged.emit()
        self.themeColorChanged.emit()
        if not isinstance(app, QApplication):
            return
        scheme = self._get_color_scheme()
        color = self._get_theme_color()
        apply_color_scheme(app, scheme)
        apply_theme_color(app, color or None)
        logger.debug('Appearance refreshed (scheme=%s, color=%s)', scheme, color or 'auto')

    def apply_to_app(self, app: QApplication) -> None:
        """启动时将外观配置应用到 QApplication（QML 加载前调用）。

        :param app: 应用实例
        """
        apply_color_scheme(app, self._get_color_scheme())
        apply_theme_color(app, self._get_theme_color() or None)

    def resolve_window_style(self) -> str:
        """返回已解析的窗口背景样式（考虑 Windows 版本自动回退）。"""
        if sys.platform != 'win32':
            return 'solid'
        try:
            raw = self._store.get_window_style()
        except Exception:
            logger.exception('Failed to read window style')
            return 'solid'
        return resolve_window_style(raw)
