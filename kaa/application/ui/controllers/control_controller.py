"""KaaControlController — 完成后操作（关机/休眠）即时配置桥接。"""
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Property, QObject, Signal, Slot

if TYPE_CHECKING:
    from kaa.application.ui.kaa_session import KaaSession

logger = logging.getLogger(__name__)


class KaaControlController(QObject):
    """控制页 KAA 专有附加配置：任务完成后动作，即时写入。"""

    endActionChanged = Signal()

    def __init__(self, session: 'KaaSession', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session

    def _get_end_action(self) -> str:
        cs = self._session.config_service
        if cs is None:
            return 'nothing'
        try:
            config = cs.get_config()
            if config.tasks.end_game.shutdown:
                return 'shutdown'
            if config.tasks.end_game.hibernate:
                return 'hibernate'
            return 'nothing'
        except Exception:
            logger.exception('Failed to read end action')
            return 'nothing'

    endAction = Property(str, _get_end_action, notify=endActionChanged)

    @Slot(str)
    def setEndAction(self, action: str) -> None:
        """写入完成后动作（即时生效）。

        :param action: ``nothing`` / ``shutdown`` / ``hibernate``。
        """
        cs = self._session.config_service
        if cs is None:
            return
        try:
            if action == 'shutdown':
                cs.apply_fields([('tasks.end_game.shutdown', True), ('tasks.end_game.hibernate', False)])
            elif action == 'hibernate':
                cs.apply_fields([('tasks.end_game.shutdown', False), ('tasks.end_game.hibernate', True)])
            else:
                cs.apply_fields([('tasks.end_game.shutdown', False), ('tasks.end_game.hibernate', False)])
            self.endActionChanged.emit()
        except Exception as e:
            logger.exception('Failed to set end action: %s', action)
            from euishell.exceptions import TaskControlError

            raise TaskControlError(str(e)) from e
