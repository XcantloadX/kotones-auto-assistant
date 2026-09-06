"""SplashBridge — Shell 启动画面桥接，承载启动状态与下载进度。"""
import logging
import threading

from pydantic import BaseModel, Field
from PySide6.QtCore import Property, QObject, Signal, Slot

from euishell.bridges.progress import FileProgressItem, ProgressAggregator

logger = logging.getLogger(__name__)


class DownloadFileEntry(BaseModel):
    """Splash 下载进度列表条目（QML 消费）。"""

    file_name: str = Field(serialization_alias='fileName')
    """文件名。"""
    percent: float = 0.0
    """下载百分比。"""
    speed_text: str = Field(default='—', serialization_alias='speedText')
    """格式化速度文本。"""
    size_text: str = Field(default='—', serialization_alias='sizeText')
    """格式化大小文本。"""

    model_config = {'populate_by_name': True}


class SplashBridge(QObject):
    """Python↔QML Splash 桥接，同时作为后台启动线程的状态接收端。

    通过 ``engine.rootContext().setContextProperty("splash", bridge)`` 暴露给 QML。
    下游可子类化以追加自身信号（如更新日志弹窗）。
    """

    statusTextChanged = Signal(str)
    gameDataCheckingChanged = Signal(bool)
    gameDataDownloadingChanged = Signal(bool)
    gameDataSkippableChanged = Signal(bool)
    downloadFilesChanged = Signal(list)
    readyChanged = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._status_text = '正在初始化…'
        self._gd_checking = False
        self._gd_downloading = False
        self._gd_skippable = False
        self._cancel_event = threading.Event()
        self._download_files: list[DownloadFileEntry] = []
        self._agg = ProgressAggregator()
        self._ready = False
        self._app_name = ''
        self._app_version = ''
        self._icon_path = ''

    # ── ShellApp 注入 ─────────────────────────────────────

    def configure(self, app_name: str, app_version: str, icon_path: str) -> None:
        """写入应用静态信息（由 ShellApp 在加载 QML 前调用）。

        :param app_name: 应用显示名
        :param app_version: 应用版本字符串
        :param icon_path: 图标 file:// URL
        """
        self._app_name = app_name
        self._app_version = app_version
        self._icon_path = icon_path

    @property
    def cancel_event(self) -> threading.Event:
        """跳过下载的取消事件（下载方轮询以中断下载）。"""
        return self._cancel_event

    def mark_ready(self) -> None:
        """标记启动完成，隐藏 Splash 显示主界面（由 ShellApp 后台线程调用）。"""
        self._set_ready(True)

    # ── Qt Properties ──────────────────────────────────────

    def _get_status_text(self) -> str:
        return self._status_text

    def _set_status_text(self, v: str) -> None:
        if self._status_text != v:
            self._status_text = v
            self.statusTextChanged.emit(v)

    def _get_game_data_checking(self) -> bool:
        return self._gd_checking

    def _set_game_data_checking(self, v: bool) -> None:
        if self._gd_checking != v:
            self._gd_checking = v
            self.gameDataCheckingChanged.emit(v)

    def _get_game_data_downloading(self) -> bool:
        return self._gd_downloading

    def _set_game_data_downloading(self, v: bool) -> None:
        if self._gd_downloading != v:
            self._gd_downloading = v
            self.gameDataDownloadingChanged.emit(v)

    def _get_game_data_skippable(self) -> bool:
        return self._gd_skippable

    def _set_game_data_skippable(self, v: bool) -> None:
        if self._gd_skippable != v:
            self._gd_skippable = v
            self.gameDataSkippableChanged.emit(v)

    def _get_download_files(self) -> list:
        return [f.model_dump(by_alias=True) for f in self._download_files]

    def _set_download_files(self, v: list[DownloadFileEntry]) -> None:
        self._download_files = v
        self.downloadFilesChanged.emit(self._get_download_files())

    def _get_ready(self) -> bool:
        return self._ready

    def _set_ready(self, v: bool) -> None:
        if self._ready != v:
            self._ready = v
            self.readyChanged.emit(v)

    statusText = Property(str, _get_status_text, _set_status_text, notify=statusTextChanged)
    gameDataChecking = Property(bool, _get_game_data_checking, _set_game_data_checking, notify=gameDataCheckingChanged)
    gameDataDownloading = Property(bool, _get_game_data_downloading, _set_game_data_downloading, notify=gameDataDownloadingChanged)
    gameDataSkippable = Property(bool, _get_game_data_skippable, _set_game_data_skippable, notify=gameDataSkippableChanged)
    downloadFiles = Property(list, _get_download_files, _set_download_files, notify=downloadFilesChanged)
    ready = Property(bool, _get_ready, _set_ready, notify=readyChanged)
    appName = Property(str, lambda self: self._app_name, constant=True)
    appVersion = Property(str, lambda self: self._app_version, constant=True)
    iconPath = Property(str, lambda self: self._icon_path, constant=True)

    # ── 供后台启动线程调用的 Slot ─────────────────────────

    @Slot(str)
    def onStatusChanged(self, text: str) -> None:
        """更新 Splash 状态文本。

        :param text: 状态描述
        """
        self._set_status_text(text)

    @Slot()
    def onGameDataChecking(self) -> None:
        """标记进入「检查资源」阶段。"""
        self._cancel_event.clear()
        self._set_game_data_checking(True)
        self._set_game_data_downloading(False)
        self._set_game_data_skippable(False)
        self._set_status_text('正在检查资源…')

    @Slot(bool)
    def onGameDataDownloading(self, skippable: bool) -> None:
        """标记进入「下载资源」阶段。

        :param skippable: 下载是否允许被用户跳过
        """
        self._set_game_data_checking(False)
        self._set_game_data_downloading(True)
        self._set_game_data_skippable(skippable)
        self._set_status_text('正在更新资源…' if skippable else '首次下载资源，请稍候…')

    @Slot()
    def skipGameDataUpdate(self) -> None:
        """用户请求跳过当前下载（设置取消事件）。"""
        if self._gd_skippable:
            self._cancel_event.set()

    @Slot()
    def onGameDataFinished(self) -> None:
        """标记下载阶段结束并清空进度。"""
        self._flush_progress()
        self._set_game_data_checking(False)
        self._set_game_data_downloading(False)
        self._set_game_data_skippable(False)
        self._agg.clear()

    @Slot(str, int, int)
    def onFileProgress(self, name: str, downloaded: int, total: int) -> None:
        """记录单文件下载进度（EMA 聚合 + 节流刷新）。

        :param name: 文件名
        :param downloaded: 已下载字节数
        :param total: 总字节数
        """
        self._agg.update(name, downloaded, total)
        files = self._agg.flush()
        if files is not None:
            self._set_download_files(self._convert(files))

    def _flush_progress(self) -> None:
        files = self._agg.force_flush()
        if files is not None:
            self._set_download_files(self._convert(files))

    @staticmethod
    def _convert(items: list[FileProgressItem]) -> list[DownloadFileEntry]:
        return [
            DownloadFileEntry(
                file_name=i.file_name,
                percent=i.percent,
                speed_text=i.speed_text,
                size_text=i.size_text,
            )
            for i in items
        ]
