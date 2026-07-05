"""SharedSettingsController — 共享配置的 Qt 桥接。

即时写盘，无草稿。后续拆到独立页面时只需将 QML 的 target 从此对象改到新 Controller。
"""
import logging

from PySide6.QtCore import QObject, Signal, Slot

from kaa.application.ui.kaa_session import KaaSession

logger = logging.getLogger(__name__)


class SharedSettingsController(QObject):
    """共享配置控制器：即时写盘。"""

    configChanged = Signal()

    def __init__(self, session: KaaSession, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session

    @Slot(str, object)
    def setField(self, path: str, value) -> None:
        """即时写入 shared 字段。path 如 "misc.check_update"（不含 shared. 前缀）。"""
        cs = self._session.config_service
        if cs is None:
            return
        shared = cs.get_shared()
        parts = path.split('.')
        obj = shared
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
        cs.save_shared(shared)
        self.configChanged.emit()
