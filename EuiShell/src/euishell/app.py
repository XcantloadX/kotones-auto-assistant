"""ShellApp — EuiShell 启动编排入口。"""
import logging
import signal
import sys
import threading
from typing import cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from euishell import paths
from euishell.bridges.error_dialog import ErrorDialogBridge, set_bridge
from euishell.bridges.notice import NoticeBackend
from euishell.controllers.profile_store import ProfileStoreBackend
from euishell.controllers.tab_manager import TabManager
from euishell.exceptions import QmlLoadError
from euishell.plugin import EuiShellPlugin, ShellRegistry, StartupContext
from euishell.theme import AppearanceController

if sys.platform == 'win32':
    from euishell.win32 import (
        MaxHoverBridge,
        TabBarHitTestBridge,
        WindowEventFilter,
        WindowStateBridge,
        apply_window_style,
        setup_frameless_window,
    )

logger = logging.getLogger(__name__)


def _install_sigint_handler(app: QApplication) -> None:
    """将 Windows Ctrl+C 转换为正常的 Qt 事件循环退出请求。"""
    if sys.platform != 'win32':
        return

    def _handle_sigint(_signum: int, _frame: object) -> None:
        logger.info('SIGINT received; requesting Qt event loop shutdown.')
        app.quit()

    signal.signal(signal.SIGINT, _handle_sigint)


class ShellApp:
    """EuiShell 应用编排器：装配插件与 Shell 控制器并运行 Qt 事件循环。"""

    def __init__(self, plugin: EuiShellPlugin, argv: list[str] | None = None) -> None:
        """
        :param plugin: 下游插件实例
        :param argv: 传给 QApplication 的参数；None 时使用 sys.argv
        """
        self._plugin = plugin
        self._argv = list(argv) if argv is not None else None

    def run(self) -> int:
        """启动 Shell 并阻塞至事件循环退出。

        :returns: Qt 事件循环退出码
        """
        # Fluent 控件样式必须在 QApplication 创建前设置
        QQuickStyle.setStyle('FluentWinUI3')

        app = QApplication(self._argv or sys.argv)
        app.setApplicationName(self._plugin.app_name)
        app.setWindowIcon(QIcon(str(self._plugin.icon_path)))

        _install_sigint_handler(app)

        if sys.platform == 'win32':
            font = QFont('Microsoft YaHei UI', 9)
        elif sys.platform == 'darwin':
            font = QFont('PingFang SC', 13)
        else:
            font = QFont('Noto Sans CJK SC', 10)
        app.setFont(font)

        return self.exec_with(app)

    def exec_with(self, app: QApplication) -> int:
        """在给定 QApplication 上装配控制器与 QML，并运行事件循环。

        供测试或已持有 QApplication 的嵌入方复用。

        :param app: 应用实例
        :returns: Qt 事件循环退出码
        """
        plugin = self._plugin

        # ── 1. 插件注册 ─────────────────────────────────────────
        registry = ShellRegistry()
        registry.set_app_info(plugin.app_name, plugin.about_links())
        plugin.register(registry)

        # ── 2. Shell 控制器 ────────────────────────────────────
        appearance = AppearanceController(plugin.appearance_store())
        prefs_ctrl = plugin.create_preferences_controller()
        tab_manager = TabManager(
            session_factory=plugin.create_session,
            persistence=plugin.tab_persistence(),
            profile_provider=plugin.profile_provider(),
        )
        profile_store = ProfileStoreBackend(tab_manager, plugin.profile_provider())
        notice = NoticeBackend()
        error_bridge = ErrorDialogBridge()
        set_bridge(error_bridge)

        splash = plugin.create_splash_bridge()
        splash.configure(
            app_name=plugin.app_name,
            app_version=plugin.app_version,
            icon_path=paths.file_url(plugin.icon_path),
        )

        # ── 3. 插件全局控制器（需要 Tab 管理器，先于 QML 加载）──
        startup_ctx = StartupContext(splash=splash, tab_manager=tab_manager)
        global_controllers = plugin.global_controllers(startup_ctx)
        registry.set_global_controllers(global_controllers)

        # 外观必须在 QML 加载前应用，保证 palette / 暗色正确
        appearance.apply_to_app(app)
        prefs_ctrl.saved.connect(appearance.refresh)

        # ── 3. QML 引擎与上下文属性 ────────────────────────────
        engine = QQmlApplicationEngine()

        max_hover_bridge = MaxHoverBridge() if sys.platform == 'win32' else None
        tab_bar_bridge = TabBarHitTestBridge() if sys.platform == 'win32' else None

        context = engine.rootContext()
        context.setContextProperty('splash', splash)
        context.setContextProperty('errorDialog', error_bridge)
        context.setContextProperty('TabManager', tab_manager)
        context.setContextProperty('ProfileStore', profile_store)
        context.setContextProperty('Notice', notice)
        context.setContextProperty('AppearanceController', appearance)
        context.setContextProperty('PreferencesController', prefs_ctrl)
        context.setContextProperty('ShellRegistry', registry)
        context.setContextProperty('globalGuards', plugin.global_dirty_guards())
        context.setContextProperty('maxHoverBridge', max_hover_bridge)
        context.setContextProperty('tabBarBridge', tab_bar_bridge)
        context.setContextProperty('windowStateBridge', None)
        context.setContextProperty('fluentFontPath', paths.file_url(paths.FLUENT_ICON_FONT_PATH))

        for role, controller in global_controllers.items():
            context.setContextProperty(role, controller)

        engine.addImportPath(str(paths.QML_DIR))

        qml_file = paths.QML_MODULE_DIR / 'main.qml'
        engine.load(QUrl.fromLocalFile(str(qml_file)))

        if not engine.rootObjects():
            logger.error('Failed to load QML file: %s', qml_file)
            set_bridge(None)
            raise QmlLoadError(qml_file)

        # ── 4. 无边框窗口 + Win32 event filter（仅原生窗口平台）──
        # offscreen（测试/CI）平台没有真实系统窗口，跳过 Win32 特效装配
        native_window_ok = sys.platform == 'win32' and app.platformName() != 'offscreen'
        if native_window_ok and max_hover_bridge is not None and tab_bar_bridge is not None:
            window = cast(QQuickWindow, engine.rootObjects()[0])
            hwnd = int(window.winId())
            window_state_bridge = WindowStateBridge(window)
            context.setContextProperty('windowStateBridge', window_state_bridge)
            setup_frameless_window(hwnd)
            apply_window_style(hwnd, appearance.resolve_window_style())
            win_event_filter = WindowEventFilter(window, max_hover_bridge, tab_bar_bridge)
            app.installNativeEventFilter(win_event_filter)

        # ── 5. 后台启动线程 ────────────────────────────────────
        def _startup_task() -> None:
            try:
                plugin.startup(startup_ctx)
            except Exception:
                logger.exception('Plugin startup failed; continuing.')
            try:
                tab_manager.restore_tabs()
            except Exception:
                logger.exception('Tab restoration failed; continuing.')
            try:
                plugin.post_startup(startup_ctx)
            except Exception:
                logger.exception('Plugin post_startup failed; continuing.')
            splash.mark_ready()
            try:
                plugin.post_ready(startup_ctx)
            except Exception:
                logger.exception('Plugin post_ready failed; continuing.')

        threading.Thread(target=_startup_task, daemon=True).start()

        # ── 6. 事件循环与清理 ──────────────────────────────────
        logger.info('Starting Qt event loop (EuiShell mode).')
        exit_code = app.exec()
        logger.info('Qt event loop exited with code %s.', exit_code)

        try:
            plugin.shutdown(startup_ctx)
        except Exception:
            logger.exception('Plugin shutdown failed.')

        set_bridge(None)
        del engine
        return exit_code
