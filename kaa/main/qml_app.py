"""QML + WebEngine 入口模块。

启动一个 PySide6 QML 窗口，在 WebEngineView 内加载 Gradio 页面，
替代原先 ``inbrowser=True`` 直接打开系统浏览器的行为。

启动流程（串行）：
1. 立即创建 ``QApplication`` 并加载 ``main.qml`` —— 用户看到 Splash 画面
2. 后台 ``QThread`` 中依次执行：
   a. 检查并更新游戏数据（通过 signal 报告进度到 QML）
   b. 延迟导入 ``gradio`` 并启动 Gradio server
3. 通过 Qt signals 将服务器 URL 回传主线程，设置到 QML 属性
4. WebEngineView 加载 Gradio 页面，Splash 自动隐藏
"""

import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from importlib.metadata import version as pkg_version, PackageNotFoundError
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl, QObject, Property, QThread, Signal, Slot
from kaa.application.ui.error_bridge import ErrorDialogBridge, set_bridge
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
# 导入 QtWebEngineWidgets 以确保 WebEngine 共享库在 QML 引擎加载前初始化
from PySide6 import QtWebEngineWidgets  # noqa: F401

from kaa.application.ui.facade import KaaFacade

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
    """格式化字节大小，如 '1.2 MB' / '345.6 KB'。"""
    if n >= _MB:
        return f"{n / _MB:.1f} MB"
    if n >= _KB:
        return f"{n / _KB:.1f} KB"
    return f"{n} B"


def _fmt_size_pair(downloaded: int, total: int) -> str:
    """格式化已下载/总大小，如 '3.5 / 24.6 MB'。"""
    if total <= 0:
        return f"{_fmt_size(downloaded)} / —"
    if total >= _MB:
        return f"{downloaded / _MB:.1f} / {total / _MB:.1f} MB"
    if total >= _KB:
        return f"{downloaded / _KB:.1f} / {total / _KB:.1f} KB"
    return f"{downloaded} / {total} B"


def _fmt_speed(bps: float) -> str:
    """格式化下载速度，如 '2.3 MB/s' / '456 KB/s'。"""
    if bps <= 0:
        return "—"
    if bps >= _MB:
        return f"{bps / _MB:.1f} MB/s"
    return f"{bps / _KB:.0f} KB/s"


class _SplashBridge(QObject):
    """Python↔QML 通信桥，同时作为 worker signal 的接收端（Slot）。

    通过 ``engine.rootContext().setContextProperty("splash", bridge)`` 暴露给 QML。
    worker signal 直接 connect 到对应 Slot，无需在 main() 里定义中间闭包。
    进度追踪（EMA 速度 + 节流刷新）也内聚在此，因为它属于展示层行为。
    """

    gradioUrlChanged      = Signal(str)
    statusTextChanged     = Signal(str)
    gameDataActiveChanged = Signal(bool)
    downloadFilesChanged  = Signal(list)
    showChangelogDialog   = Signal(str, str)  # version, body
    showMigrationDialog   = Signal(list)      # list[dict] migration messages

    _EMA_ALPHA      = 0.25
    _FLUSH_INTERVAL = 0.15  # seconds

    def __init__(self) -> None:
        super().__init__()
        self._gradio_url      = ""
        self._status_text     = "正在初始化…"
        self._gd_active       = False
        self._download_files: list = []
        self._files: dict[str, _FileProgress] = {}
        self._speed_state: dict[str, _SpeedState] = {}
        self._last_flush: float = 0.0
        self._dirty: bool = False
        self.gradio_started: bool = False  # 供退出时决定是否调用 gr.close_all()

    # ── Qt Properties ──────────────────────────────────────────────

    def _get_gradio_url(self) -> str:
        return self._gradio_url

    def _set_gradio_url(self, v: str) -> None:
        if self._gradio_url != v:
            self._gradio_url = v
            self.gradioUrlChanged.emit(v)

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

    gradioUrl      = Property(str,  _get_gradio_url,       _set_gradio_url,       notify=gradioUrlChanged)
    statusText     = Property(str,  _get_status_text,      _set_status_text,      notify=statusTextChanged)
    gameDataActive = Property(bool, _get_game_data_active, _set_game_data_active, notify=gameDataActiveChanged)
    downloadFiles  = Property(list, _get_download_files,   _set_download_files,   notify=downloadFilesChanged)
    appVersion     = Property(str,  lambda self: _APP_VERSION, constant=True)
    iconPath       = Property(str,  lambda self: str(_ICON_PATH).replace("\\", "/"), constant=True)

    # ── Slots（直接接收 _StartupWorker signals）────────────────────

    @Slot(str)
    def onUrlReady(self, url: str) -> None:
        self.gradio_started = True
        self._set_gradio_url(url)
        logger.info("Gradio URL ready: %s", url)
        self._check_and_show_migration()
        self._check_and_show_changelog()

    def _check_and_show_changelog(self) -> None:
        try:
            from kaa.config import manager as config_manager  # noqa: PLC0415
            from kaa.application.services.update_service import get_version_changelog  # noqa: PLC0415

            shared = config_manager.read_shared()
            if shared.misc.last_seen_changelog != _APP_VERSION:
                text = get_version_changelog(_APP_VERSION)
                if text:
                    # 去掉第一行标题（### v...），只保留正文
                    lines = text.splitlines()
                    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else text
                    self.showChangelogDialog.emit(_APP_VERSION, body)
        except Exception:
            logger.debug("Failed to check changelog version.", exc_info=True)

    def _check_and_show_migration(self) -> None:
        try:
            from kaa.config.migration import get_deferred_messages  # noqa: PLC0415

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
            from kaa.config import manager as config_manager  # noqa: PLC0415

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


class _StartupWorker(QObject):
    """在后台线程中串行完成游戏数据更新与 Gradio 服务器启动。

    - 游戏数据更新：通过 ``fileProgress`` signal 报告每个文件的下载进度。
    - Gradio 是一个重型包，首次 ``import gradio`` 需要 5–15 秒。

    将这些操作放在后台线程，确保主线程的 Qt 事件循环（Splash 动画）不被阻塞。
    """

    urlReady = Signal(str)
    statusChanged = Signal(str)
    failed = Signal(str)
    # 游戏数据下载进度：file_name, downloaded_bytes, total_bytes
    fileProgress = Signal(str, int, int)
    gameDataStarted = Signal()
    gameDataFinished = Signal()

    def __init__(self, facade: KaaFacade, start_immediately: bool):
        super().__init__()
        self._facade = facade
        self._start_immediately = start_immediately

    def run(self) -> None:
        """Worker 入口：游戏数据更新 → 导入 gradio → 启动 server → 发射 urlReady。"""
        # ── Phase 1: 游戏数据更新 ────────────────────────────────
        try:
            from kaa.config import manager as config_manager  # noqa: PLC0415
            from kaa.game_data.updater import GameDataUpdater, should_check  # noqa: PLC0415

            shared = config_manager.read_shared()
            if should_check(shared.misc):
                self.gameDataStarted.emit()
                self.statusChanged.emit("正在更新游戏数据…")
                logger.info("Starting game data update (QML mode).")

                updater = GameDataUpdater()
                updater.check_and_update(
                    progress_cb=None,
                    file_progress_cb=lambda name, dl, total: self.fileProgress.emit(name, dl, total),
                )
                self.gameDataFinished.emit()
                logger.info("Game data update finished.")
            else:
                logger.info("Game data update skipped (not needed).")
        except BaseException:
            logger.exception("Game data update failed; continuing to start Gradio.")
            self.gameDataFinished.emit()

        # ── Phase 2: 启动 Gradio ─────────────────────────────────
        try:
            self.statusChanged.emit("正在加载依赖…")

            # 延迟导入 gradio（重型操作，5–15s）
            from kaa.main.gr import main as gr_main  # noqa: PLC0415

            self.statusChanged.emit("正在启动服务器…")

            url: Optional[str] = gr_main(
                self._facade,
                self._start_immediately,
            )

            if url:
                logger.info("Gradio server URL: %s", url)
                self.statusChanged.emit("正在加载页面…")
                self.urlReady.emit(url)
            else:
                logger.error("Failed to start Gradio server.")
                self.failed.emit("Gradio 服务器启动失败")
        except Exception:
            logger.exception("Gradio worker failed")
            self.failed.emit("Gradio 启动过程中发生异常，请查看日志")


# ── Entry point ────────────────────────────────────────────────────

def main(facade: KaaFacade, start_immediately: bool = False) -> None:
    """
    启动 QML 主窗口并加载 Gradio 页面。

    1. 立即创建 ``QApplication`` 并加载 ``main.qml``（显示 Splash）
    2. 后台线程导入 gradio 并启动 server
    3. server 就绪后通过 signal 将 URL 传回主线程
    4. 运行 Qt 事件循环（阻塞，直到窗口关闭）

    :param facade: KaaFacade 实例
    :param start_immediately: 是否立即开始所有任务
    """
    # ── 0. 设置 Fluent 控件样式（必须在 QApplication 创建前） ────
    QQuickStyle.setStyle("FluentWinUI3")

    # ── 1. 创建 QApplication ──────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("琴音小助手")
    app.setWindowIcon(QIcon(str(_ICON_PATH)))

    # ── 2. 创建 bridge，加载 QML（立即显示 Splash 画面） ─────────
    qml_file = _QML_DIR / "main.qml"
    if not qml_file.exists():
        logger.error(f"QML file not found: {qml_file}")
        raise FileNotFoundError(f"QML file not found: {qml_file}")

    bridge = _SplashBridge()
    error_bridge = ErrorDialogBridge()
    set_bridge(error_bridge)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("splash", bridge)
    engine.rootContext().setContextProperty("errorDialog", error_bridge)
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        logger.error("Failed to load QML file. Exiting.")
        return

    # ── 3. 后台线程：游戏数据更新 → Gradio 启动 ────────────────
    thread = QThread()
    worker = _StartupWorker(facade, start_immediately)
    worker.moveToThread(thread)

    def _on_finished() -> None:
        thread.quit()

    worker.urlReady.connect(bridge.onUrlReady)
    worker.statusChanged.connect(bridge.onStatusChanged)
    worker.failed.connect(bridge.onStatusChanged)
    worker.failed.connect(_on_finished)
    worker.urlReady.connect(_on_finished)
    worker.gameDataStarted.connect(bridge.onGameDataStarted)
    worker.gameDataFinished.connect(bridge.onGameDataFinished)
    worker.fileProgress.connect(bridge.onFileProgress)
    thread.started.connect(worker.run)

    # 确保线程结束时 worker 被清理
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()

    # ── 4. 运行 Qt 事件循环 ──────────────────────────────────────
    logger.info("Starting Qt event loop (QML WebView mode).")
    exit_code = app.exec()
    logger.info("Qt event loop exited with code %s.", exit_code)

    # ── 5. 清理 ──────────────────────────────────────────────────
    # 先销毁 QML 引擎：此时 bridge 仍存活，QML 绑定求值不会得到 null
    set_bridge(None)
    del engine

    # 等待后台线程退出（线程可能已通过 deleteLater 被销毁）
    try:
        if thread.isRunning():
            thread.quit()
            thread.wait(3000)
    except RuntimeError:
        logger.debug("QThread already deleted, skipping cleanup.")

    # 关闭 Gradio server（仅在成功启动后才尝试）
    if bridge.gradio_started:
        try:
            import gradio as gr  # noqa: PLC0415
            gr.close_all()
        except Exception:
            logger.debug("Failed to close Gradio servers during cleanup.", exc_info=True)
