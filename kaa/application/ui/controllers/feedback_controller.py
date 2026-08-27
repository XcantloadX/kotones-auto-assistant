"""FeedbackController — 反馈报告控制器。"""
import logging
import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

if TYPE_CHECKING:
    from kaa.application.ui.kaa_session import KaaSession

logger = logging.getLogger(__name__)


class FeedbackController(QObject):
    """反馈报告控制器。"""

    reportDone = Signal(str)
    reportFailed = Signal(str)

    def __init__(self, session: 'KaaSession', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session

    def _get_version(self) -> str:
        """获取当前应用版本号。"""
        try:
            import importlib.metadata
            return importlib.metadata.version('ksaa')
        except Exception:
            return 'unknown'

    @Slot(str, str, str)
    def submitReport(self, title: str, description: str, output_path: str) -> None:
        """在后台线程中创建反馈报告并保存到用户选择的路径。"""
        def _work() -> None:
            try:
                fs = self._session.feedback_service
                if fs is None:
                    self.reportFailed.emit("会话未初始化")
                    return
                version = self._get_version()
                result = fs.report(
                    title=title,
                    description=description,
                    version=version,
                    output_path=output_path,
                )
                self.reportDone.emit(result.message)
            except Exception as exc:
                logger.exception("Failed to export report")
                self.reportFailed.emit(str(exc))

        threading.Thread(target=_work, daemon=True).start()
