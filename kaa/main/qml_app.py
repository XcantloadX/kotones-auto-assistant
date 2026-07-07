"""QML 入口模块。

多 Profile 架构：
- TabManager 管理多 profile tab 生命周期（每个 tab 一个 KaaSession）
- 启动时显示 Splash，后台完成游戏数据更新后恢复 tabs
"""

import logging
import sys
import time
import threading
from dataclasses import asdict, dataclass, field
from importlib.metadata import version as pkg_version, PackageNotFoundError
from typing import cast
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QObject, Property, Signal, Slot
from kaa.application.ui.error_bridge import ErrorDialogBridge, set_bridge
from kaa.application.core.hotkeys import HotkeyManager
from kaa.application.ui.controllers import (
    TabManager,
    ProfileStoreBackend,
    AppThemeController,
)
from kaa.application.ui.controllers.notice_backend import NoticeBackend
from PySide6.QtGui import QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQuick import QQuickWindow

if sys.platform == 'win32':
    from kaa.application.ui.platform_win32 import (
        MaxHoverBridge,
        TabBarHitTestBridge,
        WindowEventFilter,
        apply_window_style,
        resolve_window_style,
        setup_frameless_window,
    )

logger = logging.getLogger(__name__)

_UI_DIR = Path(__file__).resolve().parent.parent / "application" / "ui"
_QML_DIR = _UI_DIR / "qml"
_ICON_PATH = _UI_DIR / "icon.png"

try:
    _APP_VERSION = pkg_version("ksaa")
except PackageNotFoundError:
    _APP_VERSION = "dev"


@dataclass
class _FileProgress:
    fileName: str
    percent: float
    speed: float
    speedText: str
    sizeText: str


@dataclass
class _SpeedState:
    last_t: float = field(default_factory=time.monotonic)
    last_bytes: int = 0
    speed_ema: float = 0.0


# ── Background worker ──────────────────────────────────────────────

_MB = 1024 * 1024
_KB = 1024


def _fmt_size(n: int) -> str:
    if n >= _MB:
        return f"{n / _MB:.1f} MB"
    if n >= _KB:
        return f"{n / _KB:.1f} KB"
    return f"{n} B"


def _fmt_size_pair(downloaded: int, total: int) -> str:
    if total <= 0:
        return f"{_fmt_size(downloaded)} / —"
    if total >= _MB:
        return f"{downloaded / _MB:.1f} / {total / _MB:.1f} MB"
    if total >= _KB:
        return f"{downloaded / _KB:.1f} / {total / _KB:.1f} KB"
    return f"{downloaded} / {total} B"


def _fmt_speed(bps: float) -> str:
    if bps <= 0:
        return "—"
    if bps >= _MB:
        return f"{bps / _MB:.1f} MB/s"
    return f"{bps / _KB:.0f} KB/s"


class _SplashBridge(QObject):
    """Python↔QML 通信桥，同时作为 worker signal 的接收端（Slot）。

    通过 ``engine.rootContext().setContextProperty("splash", bridge)`` 暴露给 QML。
    """

    statusTextChanged     = Signal(str)
    gameDataActiveChanged = Signal(bool)
    downloadFilesChanged  = Signal(list)
    showChangelogDialog   = Signal(str, str)
    showMigrationDialog   = Signal(list)
    readyChanged          = Signal(bool)

    _EMA_ALPHA      = 0.25
    _FLUSH_INTERVAL = 0.15

    def __init__(self) -> None:
        super().__init__()
        self._status_text     = "正在初始化…"
        self._gd_active       = False
        self._download_files: list = []
        self._files: dict[str, _FileProgress] = {}
        self._speed_state: dict[str, _SpeedState] = {}
        self._last_flush: float = 0.0
        self._dirty: bool = False
        self._ready: bool = False

    # ── Qt Properties ──────────────────────────────────────────────

    def _get_status_text(self) -> str:
        return self._status_text

    def _set_status_text(self, v: str) -> None:
        if self._status_text != v:
            self._status_text = v
            self.statusTextChanged.emit(v)

    def _get_game_data_active(self) -> bool:
        return self._gd_active

    def _set_game_data_active(self, v: bool) -> None:
        if self._gd_active != v:
            self._gd_active = v
            self.gameDataActiveChanged.emit(v)

    def _get_download_files(self) -> list:
        return self._download_files

    def _set_download_files(self, v: list) -> None:
        self._download_files = v
        self.downloadFilesChanged.emit(v)

    statusText     = Property(str,  _get_status_text,      _set_status_text,      notify=statusTextChanged)
    gameDataActive = Property(bool, _get_game_data_active, _set_game_data_active, notify=gameDataActiveChanged)
    downloadFiles  = Property(list, _get_download_files,   _set_download_files,   notify=downloadFilesChanged)

    def _get_ready(self) -> bool:
        return self._ready

    def _set_ready(self, v: bool) -> None:
        if self._ready != v:
            self._ready = v
            self.readyChanged.emit(v)

    ready          = Property(bool, _get_ready,             _set_ready,             notify=readyChanged)
    appVersion     = Property(str,  lambda self: _APP_VERSION, constant=True)
    iconPath       = Property(str,  lambda self: str(_ICON_PATH).replace("\\", "/"), constant=True)

    def _check_and_show_changelog(self) -> None:
        try:
            from kaa.config import manager as config_manager
            from kaa.application.services.update_service import get_changelogs_since

            shared = config_manager.read_shared()
            if shared.misc.last_seen_changelog != _APP_VERSION:
                text = get_changelogs_since(shared.misc.last_seen_changelog)
                if text:
                    self.showChangelogDialog.emit(_APP_VERSION, text)
        except Exception:
            logger.debug("Failed to check changelog version.", exc_info=True)

    def _check_and_show_migration(self) -> None:
        try:
            from kaa.config.migration import get_deferred_messages

            messages = get_deferred_messages()
            if messages:
                data = [
                    {
                        "text": msg.text,
                        "level": msg.level,
                        "oldVersion": msg.old_version or "",
                        "newVersion": msg.new_version or "",
                    }
                    for msg in messages
                ]
                self.showMigrationDialog.emit(data)
        except Exception:
            logger.debug("Failed to check migration messages.", exc_info=True)

    @Slot()
    def onChangelogDismissed(self) -> None:
        try:
            from kaa.config import manager as config_manager
            shared = config_manager.read_shared()
            shared.misc.last_seen_changelog = _APP_VERSION
            config_manager.write_shared(shared)
        except Exception:
            logger.debug("Failed to save last_seen_changelog.", exc_info=True)

    @Slot(str)
    def onStatusChanged(self, text: str) -> None:
        self._set_status_text(text)

    @Slot()
    def onGameDataStarted(self) -> None:
        self._set_game_data_active(True)
        self._set_status_text("更新游戏资源中")

    @Slot()
    def onGameDataFinished(self) -> None:
        self._flush_progress()
        self._set_game_data_active(False)

    @Slot(str, int, int)
    def onFileProgress(self, name: str, downloaded: int, total: int) -> None:
        now = time.monotonic()
        state = self._speed_state.get(name)
        if state is None:
            state = _SpeedState(last_t=now)
            self._speed_state[name] = state

        dt = now - state.last_t
        if dt > 0.05:
            instant = (downloaded - state.last_bytes) / dt
            ema = state.speed_ema
            ema = instant if ema == 0 else self._EMA_ALPHA * instant + (1 - self._EMA_ALPHA) * ema
            state.speed_ema = ema
            state.last_t = now
            state.last_bytes = downloaded
            speed_bps = ema
        else:
            speed_bps = state.speed_ema

        pct = round(downloaded / total * 100, 1) if total else 0.0
        self._files[name] = _FileProgress(
            fileName=name,
            percent=pct,
            speed=speed_bps,
            speedText=_fmt_speed(speed_bps),
            sizeText=_fmt_size_pair(downloaded, total),
        )
        self._dirty = True
        if now - self._last_flush >= self._FLUSH_INTERVAL:
            self._flush_progress()

    def _flush_progress(self) -> None:
        if not self._dirty:
            return
        self._dirty = False
        self._last_flush = time.monotonic()
        self._set_download_files([asdict(f) for f in self._files.values()])


def _startup_task(bridge: _SplashBridge, tab_manager: TabManager, hotkey_mgr: HotkeyManager) -> None:
    """后台线程入口：游戏数据更新 → 还原 tabs → 标记就绪。"""
    # ── Phase 1: 游戏数据更新 ────────────────────────────────
    try:
        from kaa.config import manager as config_manager
        from kaa.game_data.updater import GameDataUpdater, should_check

        shared = config_manager.read_shared()
        if should_check(shared.misc):
            bridge.onGameDataStarted()
            logger.info("Starting game data update (QML mode).")

            updater = GameDataUpdater()
            updater.check_and_update(
                progress_cb=None,
                file_progress_cb=lambda name, dl, total: bridge.onFileProgress(name, dl, total),
            )
            bridge.onGameDataFinished()
            logger.info("Game data update finished.")
        else:
            logger.info("Game data update skipped (not needed).")
    except BaseException:
        logger.exception("Game data update failed; continuing.")
        bridge.onGameDataFinished()

    # ── Phase 2: 还原已保存 tabs ────────────────────────────
    try:
        bridge.onStatusChanged("正在恢复标签页…")
        tab_manager.restore_tabs()
    except Exception:
        logger.exception("Tab restoration failed; continuing.")

    # ── Phase 3: 检查迁移和更新日志 ─────────────────────────
    bridge._check_and_show_migration()
    bridge._check_and_show_changelog()

    # ── Phase 4: 启动全局热键 ──────────────────────────────
    try:
        hotkey_mgr.start()
    except Exception:
        logger.exception("Failed to start hotkeys")

    # ── UI 就绪：隐藏 Splash，显示主界面 ─────────────────────
    bridge._set_ready(True)


# ── Entry point ────────────────────────────────────────────────────

def _hotkey_stop(tab_manager: TabManager) -> None:
    ts = tab_manager.get_active_task_service()
    if ts is not None:
        ts.stop_tasks()

def _hotkey_get_pause(tab_manager: TabManager) -> bool | None:
    ts = tab_manager.get_active_task_service()
    if ts is None:
        return None
    return ts.get_pause_status()

def _hotkey_pause(tab_manager: TabManager) -> None:
    ts = tab_manager.get_active_task_service()
    if ts is not None:
        ts.request_pause()

def _hotkey_resume(tab_manager: TabManager) -> None:
    ts = tab_manager.get_active_task_service()
    if ts is not None:
        ts.request_resume()


def apply_color_scheme(app: QApplication, color_scheme: str) -> None:
    if color_scheme not in ('auto', 'light', 'dark'):
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
    palette = QPalette()
    if color_value:
        color = QColor(color_value)
        if color.isValid():
            palette.setColor(QPalette.ColorRole.Highlight, color)
            accent_role = getattr(QPalette.ColorRole, 'Accent', None)
            if accent_role is not None:
                palette.setColor(accent_role, color)
    app.setPalette(palette)


def main() -> None:
    """
    启动 QML 主窗口，Multi-Profile 架构。

    1. 创建 QApplication，加载 main.qml（显示 Splash）
    2. 后台线程完成游戏数据更新 + 恢复 tabs
    3. 用户通过 TitleBar 新建 tab → TabManager.openTab
    """
    # ── 0. 设置 Fluent 控件样式 ─────────────────────────────────
    QQuickStyle.setStyle("FluentWinUI3")

    # ── 1. 创建 QApplication ─────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("琴音小助手")
    app.setWindowIcon(QIcon(str(_ICON_PATH)))

    if sys.platform == "win32":
        _font = QFont("Microsoft YaHei UI", 9)
    elif sys.platform == "darwin":
        _font = QFont("PingFang SC", 13)
    else:
        _font = QFont("Noto Sans CJK SC", 10)
    app.setFont(_font)

    # ── 2. 创建 controllers ─────────────────────────────────────
    tab_manager = TabManager()
    profile_store = ProfileStoreBackend(tab_manager)
    notice = NoticeBackend()
    app_theme = AppThemeController()
    hotkey_mgr = HotkeyManager(
        request_stop=lambda: _hotkey_stop(tab_manager),
        get_pause_status=lambda: _hotkey_get_pause(tab_manager),
        request_pause=lambda: _hotkey_pause(tab_manager),
        request_resume=lambda: _hotkey_resume(tab_manager),
    )

    # ── 3. 创建 bridge，加载 QML ────────────────────────────────
    qml_file = _QML_DIR / "main.qml"
    if not qml_file.exists():
        logger.error("QML file not found: %s", qml_file)
        raise FileNotFoundError(f"QML file not found: {qml_file}")

    bridge = _SplashBridge()
    error_bridge = ErrorDialogBridge()
    set_bridge(error_bridge)
    engine = QQmlApplicationEngine()

    # ── 创建平台相关桥接对象 ────────────────────────────────────
    max_hover_bridge = MaxHoverBridge() if sys.platform == 'win32' else None
    tab_bar_bridge = TabBarHitTestBridge() if sys.platform == 'win32' else None

    # 注册 QML 上下文属性
    engine.rootContext().setContextProperty("splash", bridge)
    engine.rootContext().setContextProperty("errorDialog", error_bridge)
    engine.rootContext().setContextProperty("TabManager", tab_manager)
    engine.rootContext().setContextProperty("ProfileStore", profile_store)
    engine.rootContext().setContextProperty("Notice", notice)
    engine.rootContext().setContextProperty('maxHoverBridge', max_hover_bridge)
    engine.rootContext().setContextProperty('tabBarBridge', tab_bar_bridge)
    engine.rootContext().setContextProperty('fluentFontPath',
        str(_UI_DIR / "fonts" / "FluentSystemIcons-Regular.ttf").replace("\\", "/"))

    # 注册 AppThemeController context property（供 AppTheme.qml 读取 windowStyle）
    engine.rootContext().setContextProperty("AppThemeController", app_theme)

    # 添加 QML 导入路径，使 qmldir 中注册的 AppTheme 单例对子目录组件可见
    engine.addImportPath(str(_QML_DIR))

    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        logger.error("Failed to load QML file. Exiting.")
        return

    # ── 4. 应用界面偏好（配色、主题色、窗口样式）──
    from kaa.config import manager as config_manager
    _shared = config_manager.read_shared()
    apply_color_scheme(app, _shared.interface.color_scheme)
    apply_theme_color(app, _shared.interface.theme_color)

    # ── 5. 无边框窗口 + Win32 event filter + 窗口特效（仅 Windows）──
    if sys.platform == 'win32' and max_hover_bridge is not None and tab_bar_bridge is not None:
        window = cast(QQuickWindow, engine.rootObjects()[0])
        hwnd = int(window.winId())
        setup_frameless_window(hwnd)
        apply_window_style(hwnd, resolve_window_style(_shared.interface.window_style))
        _win_event_filter = WindowEventFilter(window, max_hover_bridge, tab_bar_bridge)
        app.installNativeEventFilter(_win_event_filter)

    # ── 5. 后台线程：游戏数据更新 → 恢复 tabs ──────────────────
    _startup_thread = threading.Thread(
        target=_startup_task,
        args=(bridge, tab_manager, hotkey_mgr),
        daemon=True,
    )
    _startup_thread.start()

    # ── 6. 运行 Qt 事件循环 ─────────────────────────────────────
    logger.info("Starting Qt event loop (Multi-Profile QML mode).")
    exit_code = app.exec()
    logger.info("Qt event loop exited with code %s.", exit_code)

    # ── 7. 清理 ─────────────────────────────────────────────────
    hotkey_mgr.stop()
    set_bridge(None)
    del engine
