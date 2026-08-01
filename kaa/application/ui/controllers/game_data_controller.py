"""GameDataUpdateController — 游戏数据后台更新控制器。

在 UI 就绪后于后台线程检查游戏数据更新：
- 发现新版本且 ``auto_update`` 开启 → 自动下载到 staging（不阻塞 UI）
- ``auto_update`` 关闭 → 暴露 ``updateAvailable`` 供 QML 展示提醒，
  用户点击后经 ``triggerUpdate()`` 手动触发下载
- 下载完成后设置 ``game_data_pending_version`` + ``restartNeeded``，
  下次启动时由 ``apply_staging_if_pending()`` 原子替换活跃数据

所有状态变更通过 Qt Signal 触发主线程 setter，后台线程不直接修改
QML 绑定属性。
"""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QObject, Property, Signal, Slot

from kaa.util.progress import ProgressAggregator

if TYPE_CHECKING:
    from kaa.game_data.updater import CheckResult, GameDataUpdater

logger = logging.getLogger(__name__)


class GameDataUpdateController(QObject):
    """游戏数据后台更新控制器。"""

    # ── 信号 ──
    updateAvailableChanged = Signal(bool)
    updateStatusChanged = Signal(str)
    availableVersionChanged = Signal(str)
    downloadFilesChanged = Signal(list)
    restartNeededChanged = Signal(bool)
    progressChanged = Signal(str)
    buildPercentChanged = Signal(float)
    buildMessageChanged = Signal(str)

    # ── 状态常量 ──
    STATUS_IDLE = "idle"
    STATUS_CHECKING = "checking"
    STATUS_DOWNLOADING = "downloading"
    STATUS_BUILDING = "building"
    STATUS_READY = "ready"
    STATUS_FAILED = "failed"

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._update_available = False
        self._update_status = self.STATUS_IDLE
        self._available_version = ""
        self._download_files: list = []
        self._restart_needed = False
        self._pending_version = ""
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._agg = ProgressAggregator()
        self._progress_message = ""
        self._build_percent = 0.0
        self._build_message = ""

        # 启动时检查是否有未应用的 staging
        self._check_pending_staging()

    def _check_pending_staging(self):
        """从配置读取 pending_version，判断是否有待应用的 staging。"""
        try:
            from kaa.config import manager as config_manager
            shared = config_manager.read_shared()
            pv = shared.misc.game_data_pending_version
            if pv:
                self._pending_version = pv
                self._restart_needed = True
                self._set_update_status(self.STATUS_READY)
        except Exception:
            logger.debug("Failed to check pending staging version.", exc_info=True)

    # ── Qt Properties ──

    def _get_update_available(self) -> bool:
        return self._update_available

    def _set_update_available(self, v: bool) -> None:
        if self._update_available != v:
            self._update_available = v
            self.updateAvailableChanged.emit(v)

    def _get_update_status(self) -> str:
        return self._update_status

    def _set_update_status(self, v: str) -> None:
        if self._update_status != v:
            self._update_status = v
            self.updateStatusChanged.emit(v)

    def _get_available_version(self) -> str:
        return self._available_version

    def _set_available_version(self, v: str) -> None:
        if self._available_version != v:
            self._available_version = v
            self.availableVersionChanged.emit(v)

    def _get_download_files(self) -> list:
        return self._download_files

    def _set_download_files(self, v: list) -> None:
        self._download_files = v
        self.downloadFilesChanged.emit(v)

    def _get_restart_needed(self) -> bool:
        return self._restart_needed

    def _set_restart_needed(self, v: bool) -> None:
        if self._restart_needed != v:
            self._restart_needed = v
            self.restartNeededChanged.emit(v)

    def _get_progress_message(self) -> str:
        return self._progress_message

    def _set_progress_message(self, v: str) -> None:
        if self._progress_message != v:
            self._progress_message = v
            self.progressChanged.emit(v)

    def _get_build_percent(self) -> float:
        return self._build_percent

    def _set_build_percent(self, v: float) -> None:
        if self._build_percent != v:
            self._build_percent = v
            self.buildPercentChanged.emit(v)

    def _get_build_message(self) -> str:
        return self._build_message

    def _set_build_message(self, v: str) -> None:
        if self._build_message != v:
            self._build_message = v
            self.buildMessageChanged.emit(v)

    updateAvailable = Property(bool, _get_update_available, _set_update_available, notify=updateAvailableChanged)
    updateStatus = Property(str, _get_update_status, _set_update_status, notify=updateStatusChanged)
    availableVersion = Property(str, _get_available_version, _set_available_version, notify=availableVersionChanged)
    downloadFiles = Property(list, _get_download_files, _set_download_files, notify=downloadFilesChanged)
    restartNeeded = Property(bool, _get_restart_needed, _set_restart_needed, notify=restartNeededChanged)
    progressMessage = Property(str, _get_progress_message, _set_progress_message, notify=progressChanged)
    buildPercent = Property(float, _get_build_percent, _set_build_percent, notify=buildPercentChanged)
    buildMessage = Property(str, _get_build_message, _set_build_message, notify=buildMessageChanged)

    # ── 公开方法（由 _startup_task 调用）──

    def startBackgroundCheck(self):
        """UI 就绪后启动后台检查线程。"""
        with self._lock:
            if self._update_status not in (self.STATUS_IDLE, self.STATUS_FAILED):
                return
        t = threading.Thread(target=self._background_check, daemon=True)
        t.start()

    # ── 内线程方法 ──

    def _background_check(self):
        try:
            from kaa.config import manager as config_manager
            from kaa.game_data.updater import GameDataUpdater, should_check

            shared = config_manager.read_shared()
            if not should_check(shared.misc):
                return

            self._set_update_status(self.STATUS_CHECKING)
            self._set_progress_message("正在检查游戏资源…")

            updater = GameDataUpdater(cancel=self._cancel_event)
            result = updater.check_only(progress_cb=self._set_progress_message)

            if result is None:
                self._set_update_status(self.STATUS_FAILED)
                return

            updater._mark_checked()

            if not result.needs_update:
                self._set_update_status(self.STATUS_IDLE)
                return

            # 发现新版本
            self._set_available_version(result.manifest.version)

            if result.auto_update_enabled:
                # 自动下载到 staging
                self._do_staging_download(updater, result)
            else:
                # 提示用户手动更新
                self._set_update_available(True)
                self._set_update_status(self.STATUS_IDLE)
        except Exception:
            logger.exception("Background game data check failed.")
            self._set_update_status(self.STATUS_FAILED)

    def _do_staging_download(self, updater: GameDataUpdater, result: CheckResult) -> None:
        self._set_update_available(False)
        self._set_update_status(self.STATUS_DOWNLOADING)
        self._set_progress_message("正在下载游戏资源更新…")

        updater.download_to_staging(
            result,
            file_progress_cb=self._on_file_progress,
            build_started_cb=self._on_build_started,
            build_progress_cb=self._on_build_progress,
        )

        self._set_restart_needed(True)
        self._set_update_status(self.STATUS_READY)
        self._set_progress_message(
            f"游戏数据 {result.manifest.version[:8]} 下载完成，"
            "将在下次启动时自动应用。"
        )

    def _on_build_started(self):
        """图像索引构建阶段开始（子线程触发，经信号推送主线程）。"""
        self._set_update_status(self.STATUS_BUILDING)
        self._set_progress_message("正在构建图像数据索引…")

    def _on_build_progress(self, index: int, total: int, name: str, cur: int, tot: int):
        """图像索引构建阶段进度（子线程触发，经信号推送主线程）。

        :param index: 当前 builder 序号（1 起）
        :param total: builder 总数
        :param name: builder 名称
        :param cur: 当前 builder 内文件进度
        :param tot: 当前 builder 文件总数（0 表示未知）
        """
        frac = ((index - 1) / total) if total else 0.0
        if total and tot:
            frac += (cur / tot) / total
        self._set_build_percent(round(frac * 100, 1))
        self._set_build_message(f"构建图像数据索引（{index}/{total}）：{name}")

    def _on_file_progress(self, name: str, downloaded: int, total: int):
        """文件级下载进度回调（子线程触发，经信号推送主线程）。"""
        self._agg.update(name, downloaded, total)
        files = self._agg.flush()
        if files is not None:
            self._set_download_files(files)

    def _final_flush_progress(self):
        """下载结束后兜底刷新一次进度。"""
        files = self._agg.force_flush()
        if files is not None:
            self._set_download_files(files)

    # ── QML Slots ──

    @Slot()
    def triggerUpdate(self):
        """用户点击通知后触发后台下载。"""
        with self._lock:
            if self._update_status != self.STATUS_IDLE:
                return
        t = threading.Thread(target=self._do_manual_download, daemon=True)
        t.start()

    def _do_manual_download(self):
        try:
            from kaa.game_data.updater import GameDataUpdater
            self._set_update_status(self.STATUS_CHECKING)
            updater = GameDataUpdater(cancel=self._cancel_event)
            result = updater.check_only()
            if result is None or not result.needs_update:
                self._set_update_status(self.STATUS_IDLE)
                self._set_progress_message("目前已是最新版本，无需更新。")
                return
            self._do_staging_download(updater, result)
        except Exception as e:
            logger.exception("Manual game data download failed.")
            self._set_update_status(self.STATUS_FAILED)
            self._set_progress_message(f"下载失败：{e}")

    @Slot()
    def dismissUpdate(self):
        """用户忽略更新通知。"""
        self._set_update_available(False)

    @Slot()
    def skipDownload(self):
        """跳过当前下载。"""
        self._cancel_event.set()
