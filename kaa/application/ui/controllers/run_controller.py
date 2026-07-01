"""RunController — 任务运行状态的 Qt 桥接。

用 QObject 包装 ``task_service``，通过 300ms QTimer 轮询
驱动 QML 属性刷新。
"""
import json
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot

from kaa.application.ui.kaa_session import KaaSession
from kaa.tasks import TASK_REGISTRY

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── 任务 key → config dot path 映射 ──────────────────────────────
_TASK_CONFIG_PATHS: dict[str, str] = {
    'start_game':           'tasks.start_game.enabled',
    'acquire_activity_funds': 'tasks.activity_funds.enabled',
    'acquire_presents':     'tasks.presents.enabled',
    'assignment':           'tasks.assignment.enabled',
    'capsule_toys':         'tasks.capsule_toys.enabled',
    'club_reward':          'tasks.club_reward.enabled',
    'contest':              'tasks.contest.enabled',
    'purchase':             'tasks.purchase.enabled',
    'upgrade_support_card': 'tasks.upgrade_support_card.enabled',
    'produce':              'tasks.produce.enabled',
    'mission_reward':       'tasks.mission_reward.enabled',
}

# ── 快速设置短标签（对应 _TASK_CONFIG_PATHS 的 key）────────────────
_TASK_SHORT_NAMES: dict[str, str] = {
    'start_game':             '启动游戏',
    'acquire_activity_funds': '活动费',
    'acquire_presents':       '礼物',
    'assignment':             '工作',
    'capsule_toys':           '扭蛋',
    'club_reward':            '社团',
    'contest':                '竞赛',
    'purchase':               '商店',
    'upgrade_support_card':   '支援卡',
    'produce':                '培育',
    'mission_reward':         '任务',
}


def _get_dot_path(obj, dot_path: str):
    """按 dot path 读取嵌套属性。"""
    parts = dot_path.split('.')
    for part in parts:
        obj = getattr(obj, part)
    return obj


def _set_dot_path(obj, dot_path: str, value) -> None:
    """按 dot path 设置嵌套属性。"""
    parts = dot_path.split('.')
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)


class RunController(QObject):
    """任务运行控制器，向 QML 暴露运行状态和控制接口。"""

    stateChanged = Signal()
    tasksChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, session: KaaSession, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session

        # 300ms 轮询定时器，驱动 stateChanged → QML 属性刷新
        self._timer = QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._refresh_state)
        self._timer.start()

    def _refresh_state(self) -> None:
        self.stateChanged.emit()

    # ── Qt Properties（由 stateChanged 驱动）──────────────────────

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
    endAction = Property(str, _get_end_action, notify=stateChanged)

    # ── 运行控制 ──────────────────────────────────────────────────

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
        """启动单个任务。"""
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

    # ── 数据查询 ──────────────────────────────────────────────────

    @Slot(result=str)
    def allTaskNamesJson(self) -> str:
        """返回所有可单独执行的任务名称列表 JSON（与 task_registry 键一致）。"""
        ts = self._session.task_service
        if ts is None:
            return "[]"
        try:
            return json.dumps(ts.get_all_task_names(), ensure_ascii=False)
        except Exception:
            logger.exception("Failed to build allTaskNamesJson")
            return "[]"

    @Slot(result=str)
    def tasksJson(self) -> str:
        """返回任务列表 JSON。

        结构：[{"name": "商店购买", "path": "tasks.purchase.enabled",
               "enabled": true, "status": "pending"}, ...]
        status ∈ {"pending", "running", "done", "error"}
        """
        cs = self._session.config_service
        ts = self._session.task_service
        if cs is None or ts is None:
            return "[]"
        try:
            config = cs.get_config()
            status_map = dict(ts.get_task_statuses())
            result = []
            for key, func in TASK_REGISTRY.items():
                dot_path = _TASK_CONFIG_PATHS.get(key)
                if dot_path is None:
                    continue
                task_obj = func.task
                name = task_obj.name
                enabled = bool(_get_dot_path(config, dot_path))
                status = status_map.get(name, 'pending')
                result.append({
                    'name': name,
                    'shortName': _TASK_SHORT_NAMES.get(key, name),
                    'path': dot_path,
                    'enabled': enabled,
                    'status': status,
                })
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            logger.exception("Failed to build tasksJson")
            return "[]"

    # ── 批量开关 ──────────────────────────────────────────────────

    @Slot(str, bool)
    def setTaskEnabled(self, dot_path: str, enabled: bool) -> None:
        """按 dot_path 启用/禁用单个任务。"""
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            config = cs.get_config()
            _set_dot_path(config, dot_path, enabled)
            cs.save()
            self.tasksChanged.emit()
        except Exception as e:
            logger.exception("Failed to set task enabled: %s=%s", dot_path, enabled)
            self.operationFailed.emit(str(e))

    @Slot(bool)
    def selectAllTasks(self, value: bool) -> None:
        """全选/清空所有任务。"""
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            config = cs.get_config()
            for dot_path in _TASK_CONFIG_PATHS.values():
                _set_dot_path(config, dot_path, value)
            cs.save()
            self.tasksChanged.emit()
        except Exception as e:
            logger.exception("Failed to select all tasks: %s", value)
            self.operationFailed.emit(str(e))

    @Slot()
    def selectOnlyProduce(self) -> None:
        """只选培育任务。"""
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            config = cs.get_config()
            for dot_path in _TASK_CONFIG_PATHS.values():
                _set_dot_path(config, dot_path, False)
            config.tasks.produce.enabled = True
            cs.save()
            self.tasksChanged.emit()
        except Exception as e:
            logger.exception("Failed to select only produce")
            self.operationFailed.emit(str(e))

    @Slot()
    def selectExceptProduce(self) -> None:
        """只不选培育任务（其余全选）。"""
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            config = cs.get_config()
            for dot_path in _TASK_CONFIG_PATHS.values():
                _set_dot_path(config, dot_path, True)
            config.tasks.produce.enabled = False
            cs.save()
            self.tasksChanged.emit()
        except Exception as e:
            logger.exception("Failed to select except produce")
            self.operationFailed.emit(str(e))

    # ── 完成后动作 ────────────────────────────────────────────────

    @Slot(str)
    def setEndAction(self, action: str) -> None:
        """设置完成后动作。action ∈ {"nothing", "shutdown", "hibernate"}"""
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            config = cs.get_config()
            if action == "shutdown":
                config.tasks.end_game.shutdown = True
                config.tasks.end_game.hibernate = False
            elif action == "hibernate":
                config.tasks.end_game.shutdown = False
                config.tasks.end_game.hibernate = True
            else:
                config.tasks.end_game.shutdown = False
                config.tasks.end_game.hibernate = False
            cs.save()
            self.stateChanged.emit()
        except Exception as e:
            logger.exception("Failed to set end action: %s", action)
            self.operationFailed.emit(str(e))
