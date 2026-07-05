"""RunController — 任务运行状态的 Qt 桥接。

即时写入 + 信号驱动 + TaskEnabledModel。
"""
import json
import logging

from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot

from kaa.application.ui.kaa_session import KaaSession
from kaa.application.ui.models.task_enabled_model import TaskEnabledModel

logger = logging.getLogger(__name__)


class RunController(QObject):
    """任务运行控制器，向 QML 暴露运行状态和控制接口。"""

    stateChanged = Signal()
    tasksChanged = Signal()
    endActionChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, session: KaaSession, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session
        self._task_model: TaskEnabledModel | None = None

        cs = session.config_service
        if cs is not None:
            cs.bus().configChanged.connect(self._on_config_changed)
            self._task_model = TaskEnabledModel(cs)

        # 1s 定时器只刷 task 运行态
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh_state)
        self._timer.start()

    # ── TaskEnabledModel ──────────────────────────────────────

    @Property(QObject, constant=True)
    def taskModel(self):
        return self._task_model

    # ── 状态刷新（定时器）──────────────────────────────────

    def _refresh_state(self) -> None:
        ts = self._session.task_service
        if ts is not None:
            try:
                statuses = dict(ts.get_task_statuses())
                if self._task_model is not None:
                    self._task_model.set_all_running_statuses(statuses)
            except Exception:
                pass
        self.stateChanged.emit()

    def _on_config_changed(self) -> None:
        self.stateChanged.emit()
        self.tasksChanged.emit()
        self.endActionChanged.emit()

    # ── Qt Properties ────────────────────────────────────────

    def _get_running(self) -> bool:
        ts = self._session.task_service
        if ts is None:
            return False
        try:
            return ts.is_running()
        except Exception:
            return False

    def _get_is_stopping(self) -> bool:
        ts = self._session.task_service
        if ts is None:
            return False
        try:
            return ts.is_stopping
        except Exception:
            return False

    def _get_is_paused(self) -> bool:
        ts = self._session.task_service
        if ts is None:
            return False
        try:
            return ts.get_pause_status() is True
        except Exception:
            return False

    def _get_current_task_name(self) -> str:
        ts = self._session.task_service
        if ts is None:
            return ""
        try:
            for _name, status in ts.get_task_statuses():
                if status == 'running':
                    return _name
            return ""
        except Exception:
            return ""

    def _get_end_action(self) -> str:
        cs = self._session.config_service
        if cs is None:
            return "nothing"
        try:
            config = cs.get_config()
            if config.tasks.end_game.shutdown:
                return "shutdown"
            if config.tasks.end_game.hibernate:
                return "hibernate"
            return "nothing"
        except Exception:
            return "nothing"

    running = Property(bool, _get_running, notify=stateChanged)
    isStopping = Property(bool, _get_is_stopping, notify=stateChanged)
    isPaused = Property(bool, _get_is_paused, notify=stateChanged)
    currentTaskName = Property(str, _get_current_task_name, notify=stateChanged)
    endAction = Property(str, _get_end_action, notify=endActionChanged)

    # ── 运行控制 ─────────────────────────────────────────────

    @Slot()
    def start(self) -> None:
        ts = self._session.task_service
        if ts is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            ts.start_all_tasks()
            self.stateChanged.emit()
        except Exception as e:
            logger.exception("Failed to start tasks")
            self.operationFailed.emit(str(e))

    @Slot()
    def stop(self) -> None:
        ts = self._session.task_service
        if ts is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            ts.stop_tasks()
            self.stateChanged.emit()
        except Exception as e:
            logger.exception("Failed to stop tasks")
            self.operationFailed.emit(str(e))

    @Slot()
    def togglePause(self) -> None:
        ts = self._session.task_service
        if ts is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            ts.toggle_pause()
            self.stateChanged.emit()
        except Exception as e:
            logger.exception("Failed to toggle pause")
            self.operationFailed.emit(str(e))

    @Slot(str)
    def runTask(self, name: str) -> None:
        ts = self._session.task_service
        if ts is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            ts.start_single_task(name)
            self.stateChanged.emit()
        except Exception as e:
            logger.exception("Failed to run task '%s'", name)
            self.operationFailed.emit(str(e))

    # ── 数据查询 ──────────────────────────────────────────────

    @Slot(result=str)
    def allTaskNamesJson(self) -> str:
        """返回所有可单独执行的任务名称列表 JSON。"""
        ts = self._session.task_service
        if ts is None:
            return "[]"
        try:
            return json.dumps(ts.get_all_task_names(), ensure_ascii=False)
        except Exception:
            logger.exception("Failed to build allTaskNamesJson")
            return "[]"

    # ── 即时写入 ─────────────────────────────────────────────

    @Slot(str, bool)
    def setTaskEnabled(self, dot_path: str, enabled: bool) -> None:
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            cs.apply_field(dot_path, enabled)
        except Exception as e:
            logger.exception("Failed to set task enabled: %s=%s", dot_path, enabled)
            self.operationFailed.emit(str(e))

    @Slot(str)
    def setEndAction(self, action: str) -> None:
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            if action == "shutdown":
                cs.apply_fields([('tasks.end_game.shutdown', True), ('tasks.end_game.hibernate', False)])
            elif action == "hibernate":
                cs.apply_fields([('tasks.end_game.shutdown', False), ('tasks.end_game.hibernate', True)])
            else:
                cs.apply_fields([('tasks.end_game.shutdown', False), ('tasks.end_game.hibernate', False)])
            self.endActionChanged.emit()
        except Exception as e:
            logger.exception("Failed to set end action: %s", action)
            self.operationFailed.emit(str(e))

    # ── 批量开关 ─────────────────────────────────────────────

    def _batch_set_enabled(self, value: bool, exclude: str | None = None) -> None:
        """批量设置所有任务启用状态，可选排除某个 key。"""
        from kaa.application.ui.models.task_enabled_model import _TASK_CONFIG_PATHS
        items = []
        for key, dot_path in _TASK_CONFIG_PATHS.items():
            if exclude is not None and key == exclude:
                items.append((dot_path, not value))
            else:
                items.append((dot_path, value))
        cs = self._session.config_service
        if cs is not None:
            cs.apply_fields(items)

    @Slot(bool)
    def selectAllTasks(self, value: bool) -> None:
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            self._batch_set_enabled(value)
        except Exception as e:
            logger.exception("Failed to select all tasks: %s", value)
            self.operationFailed.emit(str(e))

    @Slot()
    def selectOnlyProduce(self) -> None:
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            self._batch_set_enabled(False, exclude='produce')
        except Exception as e:
            logger.exception("Failed to select only produce")
            self.operationFailed.emit(str(e))

    @Slot()
    def selectExceptProduce(self) -> None:
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            self._batch_set_enabled(True, exclude='produce')
        except Exception as e:
            logger.exception("Failed to select except produce")
            self.operationFailed.emit(str(e))
