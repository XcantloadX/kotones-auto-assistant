"""ProgressBridge — 事件驱动的任务进度推送。

替代 Gradio 的 gr.Timer 状态轮询，通过注册 kaa.events 回调实现实时推送。
"""
import logging

from PySide6.QtCore import QObject, Property, Signal, QTimer
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kaa.application.ui.kaa_session import KaaSession

logger = logging.getLogger(__name__)


class ProgressBridge(QObject):
    """向 QML 推送任务进度信息。

    通过注册 ``kaa.events.task_status_changed`` 和 ``kaa.events.stopped``
    回调，在任务状态变化时更新并推送 ``statusText`` / ``progressPercent``
    / ``lastErrorText``。

    回调在 KotoneBot 运行线程触发，通过 Qt 信号机制自动切换到主线程。
    """

    changed = Signal()

    def __init__(self, session: 'KaaSession', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session
        self._status_text = ""
        self._progress_percent = 0
        self._last_error_text = ""
        self._total_tasks = 0
        self._finished_tasks = 0
        self._installed = False

        # 若 session 尚未初始化，用定时器重试
        self._install_timer = QTimer(self)
        self._install_timer.setSingleShot(True)
        self._install_timer.setInterval(500)
        self._install_timer.timeout.connect(self._try_install)
        self._try_install()

    # ── 安装 / 卸载 ──────────────────────────────────────

    def _try_install(self) -> None:
        """尝试向 kaa.events 注册回调。"""
        if self._installed:
            return
        kaa = self._session.kaa
        if kaa is None:
            self._install_timer.start()
            return
        try:
            kaa.events.task_status_changed += self._on_task_status_changed
            kaa.events.stopped += self._on_stopped
            self._installed = True

            # 初始化任务总数
            ts = self._session.task_service
            if ts is not None:
                statuses = ts.get_task_statuses()
                self._total_tasks = len(statuses)
        except Exception:
            logger.exception("Failed to install ProgressBridge callbacks")

    def uninstall(self) -> None:
        """从 kaa.events 注销回调。"""
        if not self._installed:
            return
        kaa = self._session.kaa
        if kaa is not None:
            try:
                kaa.events.task_status_changed -= self._on_task_status_changed
                kaa.events.stopped -= self._on_stopped
            except Exception:
                logger.exception("Failed to uninstall ProgressBridge callbacks")
        self._installed = False

    # ── 事件回调（子线程触发）──────────────────────────────

    def _on_task_status_changed(self, task, status: str) -> None:
        """task_status_changed 回调。

        :param task: Task 对象，有 ``.name`` 属性。
        :param status: ``'running'`` 或 ``'finished'``。
        """
        try:
            task_name = getattr(task, 'name', str(task))
            if status == 'running':
                self._status_text = f"运行中: {task_name}"
            elif status == 'finished':
                self._finished_tasks += 1
                if self._total_tasks > 0:
                    self._progress_percent = int(
                        self._finished_tasks / self._total_tasks * 100
                    )
                self._status_text = f"已完成: {task_name}"
            # changed 信号跨线程自动 QueuedConnection
            self.changed.emit()
        except Exception:
            logger.exception("Error in ProgressBridge._on_task_status_changed")

    def _on_stopped(self, reason, exc) -> None:
        """stopped 回调。

        :param reason: BotStopReason 枚举（str, Enum）。
        :param exc: 异常对象或 None。
        """
        try:
            reason_name = getattr(reason, 'name', str(reason))
            if reason_name == 'COMPLETED':
                self._status_text = "已完成"
                self._progress_percent = 100
            elif reason_name == 'USER_REQUEST':
                self._status_text = "已停止"
            elif reason_name == 'ERROR' and exc is not None:
                self._last_error_text = str(exc)
                self._status_text = "出错"
            self.changed.emit()
        except Exception:
            logger.exception("Error in ProgressBridge._on_stopped")

    def reset(self) -> None:
        """重置进度状态（新一轮运行前调用）。"""
        self._status_text = ""
        self._progress_percent = 0
        self._finished_tasks = 0
        self._last_error_text = ""
        self.changed.emit()

    # ── Qt Properties ─────────────────────────────────────

    def _get_status_text(self) -> str:
        return self._status_text

    def _get_progress_percent(self) -> int:
        return self._progress_percent

    def _get_last_error_text(self) -> str:
        return self._last_error_text

    statusText = Property(str, _get_status_text, notify=changed)
    progressPercent = Property(int, _get_progress_percent, notify=changed)
    lastErrorText = Property(str, _get_last_error_text, notify=changed)
