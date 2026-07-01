"""FeedbackController — 反馈报告控制器。

后台线程创建报告并上传，通过信号推送进度到 QML。
"""
import logging
import os
import threading
import zipfile
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

if TYPE_CHECKING:
    from kaa.application.ui.kaa_session import KaaSession

logger = logging.getLogger(__name__)


class FeedbackController(QObject):
    """反馈报告控制器。"""

    reportProgress = Signal(str, float)
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

    # ── 提交报告 ─────────────────────────────────────────

    @Slot(str, str, bool)
    def submitReport(self, title: str, description: str, upload: bool) -> None:
        """在后台线程中创建并上传反馈报告。

        :param title: 报告标题。
        :param description: 问题描述。
        :param upload: 是否上传到服务器。
        """
        def _on_progress(info: dict) -> None:
            """反馈服务的进度回调（子线程触发）。"""
            try:
                step = info.get('step', 0)
                total = info.get('total_steps', 1)
                item = info.get('item', '')
                fraction = step / total if total > 0 else 0.0
                self.reportProgress.emit(item, fraction)
            except Exception:
                pass

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
                    upload=upload,
                    on_progress=_on_progress,
                )
                self.reportDone.emit(result.message)
            except Exception as exc:
                logger.exception("Failed to submit report")
                self.reportFailed.emit(str(exc))

        threading.Thread(target=_work, daemon=True).start()

    # ── 导出日志 ─────────────────────────────────────────

    @Slot(result=str)
    def exportLogsZip(self) -> str:
        if not os.path.exists('logs'):
            return "logs 文件夹不存在"
        try:
            timestamp = datetime.now().strftime('%y-%m-%d-%H-%M-%S')
            zip_filename = f'logs-{timestamp}.zip'
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                for root, _, files in os.walk('logs'):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, 'logs')
                        zipf.write(file_path, arcname)
            return f"已导出到 {zip_filename}"
        except Exception as exc:
            logger.exception("Failed to export logs")
            return f"导出失败：{exc}"
