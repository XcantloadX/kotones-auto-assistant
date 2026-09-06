"""RunController — 任务运行控制的 Qt 桥接。"""
import json
import logging

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from euishell.controllers.task_toggles_model import TaskTogglesModel
from euishell.exceptions import TaskControlError
from euishell.session import TaskControl, TaskTogglesSource

logger = logging.getLogger(__name__)


class RunController(QObject):
    """任务运行控制器，向 QML 暴露运行状态、快速开关模型与批量操作。"""

    stateChanged = Signal()
    tasksChanged = Signal()
    bulkActionsChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(
        self,
        control: TaskControl | None,
        toggles: TaskTogglesSource | None,
        parent: QObject | None = None,
    ) -> None:
        """
        :param control: 任务运行控制数据源；会话未提供时为 None
        :param toggles: 快速开关数据源；不需要时为 None
        :param parent: Qt 父对象
        """
        super().__init__(parent)
        self._control = control
        self._task_model: TaskTogglesModel | None = None

        if toggles is not None:
            self._toggles = toggles
            self._task_model = TaskTogglesModel(toggles, self)
            toggles.togglesChanged.connect(self._on_toggles_changed)
        else:
            self._toggles = None

        # 1s 定时器轮询任务运行态（TaskControl 为轮询式协议）
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh_state)
        self._timer.start()

    def _refresh_state(self) -> None:
        self.stateChanged.emit()

    def _on_toggles_changed(self) -> None:
        if self._task_model is not None:
            self._task_model.refresh()
        self.tasksChanged.emit()

    # ── Qt Properties ────────────────────────────────────────

    @Property(QObject, constant=True)
    def taskModel(self) -> QObject | None:
        return self._task_model

    def _get_running(self) -> bool:
        if self._control is None:
            return False
        try:
            return self._control.running
        except Exception:
            logger.exception('Failed to read running state')
            return False

    def _get_is_stopping(self) -> bool:
        if self._control is None:
            return False
        try:
            return self._control.stopping
        except Exception:
            logger.exception('Failed to read stopping state')
            return False

    def _get_is_paused(self) -> bool:
        if self._control is None:
            return False
        try:
            return self._control.paused
        except Exception:
            logger.exception('Failed to read paused state')
            return False

    def _get_current_task_name(self) -> str:
        if self._control is None:
            return ''
        try:
            return self._control.current_task_name
        except Exception:
            logger.exception('Failed to read current task name')
            return ''

    running = Property(bool, _get_running, notify=stateChanged)
    isStopping = Property(bool, _get_is_stopping, notify=stateChanged)
    isPaused = Property(bool, _get_is_paused, notify=stateChanged)
    currentTaskName = Property(str, _get_current_task_name, notify=stateChanged)

    # ── 运行控制 ─────────────────────────────────────────────

    @Slot()
    def start(self) -> None:
        """启动全部任务。"""
        if self._control is None:
            self.operationFailed.emit('会话尚未初始化')
            return
        try:
            self._control.start()
            self.stateChanged.emit()
        except TaskControlError as e:
            logger.exception('Failed to start tasks')
            self.operationFailed.emit(str(e))

    @Slot()
    def stop(self) -> None:
        """停止任务。"""
        if self._control is None:
            self.operationFailed.emit('会话尚未初始化')
            return
        try:
            self._control.stop()
            self.stateChanged.emit()
        except TaskControlError as e:
            logger.exception('Failed to stop tasks')
            self.operationFailed.emit(str(e))

    @Slot()
    def togglePause(self) -> None:
        """切换暂停/恢复。"""
        if self._control is None:
            self.operationFailed.emit('会话尚未初始化')
            return
        try:
            self._control.toggle_pause()
            self.stateChanged.emit()
        except TaskControlError as e:
            logger.exception('Failed to toggle pause')
            self.operationFailed.emit(str(e))

    @Slot(str)
    def runTask(self, name: str) -> None:
        """单独运行指定任务。

        :param name: 任务名。
        """
        if self._control is None:
            self.operationFailed.emit('会话尚未初始化')
            return
        try:
            self._control.run_single(name)
            self.stateChanged.emit()
        except TaskControlError as e:
            logger.exception("Failed to run task '%s'", name)
            self.operationFailed.emit(str(e))

    # ── 数据查询 ──────────────────────────────────────────────

    @Slot(result=str)
    def allTaskNamesJson(self) -> str:
        """返回所有可单独执行的任务名称列表 JSON。"""
        if self._control is None:
            return '[]'
        try:
            return json.dumps(self._control.task_names(), ensure_ascii=False)
        except Exception:
            logger.exception('Failed to build allTaskNamesJson')
            return '[]'

    @Slot(result=str)
    def bulkActionsJson(self) -> str:
        """返回快速开关批量操作按钮列表 JSON（[{label}]）。"""
        if self._toggles is None:
            return '[]'
        try:
            return json.dumps(
                [{'label': a.label} for a in self._toggles.bulk_actions()],
                ensure_ascii=False,
            )
        except Exception:
            logger.exception('Failed to build bulkActionsJson')
            return '[]'

    @Slot(int)
    def invokeBulkAction(self, index: int) -> None:
        """触发第 index 个批量操作。

        :param index: bulkActionsJson 列表中的下标。
        """
        if self._toggles is None:
            return
        try:
            actions = self._toggles.bulk_actions()
        except Exception:
            logger.exception('Failed to list bulk actions')
            return
        if not (0 <= index < len(actions)):
            logger.warning('Bulk action index out of range: %d', index)
            return
        try:
            actions[index].callback()
        except Exception as e:
            logger.exception('Bulk action failed: %s', actions[index].label)
            self.operationFailed.emit(str(e))

    @Slot(str, bool)
    def setTaskEnabled(self, key: str, enabled: bool) -> None:
        """写入单个快速开关状态。

        :param key: 开关唯一标识。
        :param enabled: 目标状态。
        """
        if self._toggles is None:
            self.operationFailed.emit('会话尚未初始化')
            return
        try:
            self._toggles.set_enabled(key, enabled)
        except Exception as e:
            logger.exception('Failed to set task enabled: %s=%s', key, enabled)
            self.operationFailed.emit(str(e))
