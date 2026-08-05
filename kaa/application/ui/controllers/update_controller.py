"""UpdateController — 版本更新控制器。

后台线程加载版本信息，通过信号推送到 QML。
"""
import json
import logging
import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

if TYPE_CHECKING:
    from kaa.application.ui.kaa_session import KaaSession

logger = logging.getLogger(__name__)


class UpdateController(QObject):
    """版本更新控制器，通过 JSON 与 QML 交换数据。"""

    versionsLoaded = Signal(str)   # JSON {installed, latest, launcher, versions:[...]}
    loadFailed = Signal(str)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, session: 'KaaSession', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session

    @Slot()
    def loadVersionsAsync(self) -> None:
        """在后台线程中加载远程版本信息。"""
        def _work() -> None:
            try:
                us = self._session.update_service
                if us is None:
                    self.loadFailed.emit("会话未初始化")
                    return
                info = us.list_remote_versions()
                data = {
                    'installed': info.installed_version or '',
                    'latest': info.latest or '',
                    'launcher': info.launcher_version or '',
                    'versions': info.versions or [],
                }
                self.versionsLoaded.emit(json.dumps(data, ensure_ascii=False))
            except Exception as exc:
                logger.exception("Failed to load versions")
                self.loadFailed.emit(str(exc))

        threading.Thread(target=_work, daemon=True).start()

    # ── 安装版本 ─────────────────────────────────────────

    @Slot(str)
    def installVersion(self, version: str) -> None:
        """安装指定版本（会导致应用重启）。"""
        try:
            us = self._session.update_service
            if us is None:
                self.operationFailed.emit("会话未初始化")
                return
            us.install_version(version)
            # install_version 会重启应用，不会执行到这里
        except Exception as exc:
            logger.exception("Failed to install version: %s", version)
            self.operationFailed.emit(f"安装失败：{exc}")

    # ── 更新日志 ─────────────────────────────────────────

    @Slot(result=str)
    def changelogText(self) -> str:
        """返回完整更新日志文本。"""
        try:
            from kaa.metadata import CHANGELOG
            return CHANGELOG
        except Exception:
            logger.exception("Failed to load changelog")
            return ""
