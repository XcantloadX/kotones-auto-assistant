"""KaaTaskControl / KaaTaskToggles — KAA 任务系统对 EuiShell 协议的适配。"""
import logging
from typing import TYPE_CHECKING

from euishell.exceptions import TaskControlError
from euishell.session import TaskBulkAction, TaskControl, TaskToggle, TaskTogglesSource

if TYPE_CHECKING:
    from kaa.application.ui.kaa_session import KaaSession

logger = logging.getLogger(__name__)

# ── 任务 key → config dot path 映射 ──────────────────────────────
TASK_CONFIG_PATHS: dict[str, str] = {
    'acquire_activity_funds': 'tasks.activity_funds.enabled',
    'acquire_presents':       'tasks.presents.enabled',
    'assignment':             'tasks.assignment.enabled',
    'capsule_toys':           'tasks.capsule_toys.enabled',
    'club_reward':            'tasks.club_reward.enabled',
    'contest':                'tasks.contest.enabled',
    'purchase':               'tasks.purchase.enabled',
    'upgrade_support_card':   'tasks.upgrade_support_card.enabled',
    'produce':                'tasks.produce.enabled',
    'mission_reward':         'tasks.mission_reward.enabled',
}

# ── 快速设置短标签 ────────────────────────────────────────────────
TASK_SHORT_NAMES: dict[str, str] = {
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


class KaaTaskControl(TaskControl):
    """将 KaaSession 的任务服务适配为 EuiShell 任务控制协议。"""

    def __init__(self, session: 'KaaSession') -> None:
        self._session = session

    def _task_service(self):
        ts = self._session.task_service
        if ts is None:
            raise TaskControlError('会话尚未初始化')
        return ts

    @property
    def running(self) -> bool:
        try:
            return self._session.is_running
        except Exception as e:
            logger.exception('Failed to read running state')
            raise TaskControlError(str(e)) from e

    @property
    def stopping(self) -> bool:
        try:
            ts = self._session.task_service
            return ts is not None and ts.is_stopping
        except Exception as e:
            logger.exception('Failed to read stopping state')
            raise TaskControlError(str(e)) from e

    @property
    def paused(self) -> bool:
        try:
            ts = self._session.task_service
            return ts is not None and ts.get_pause_status() is True
        except Exception as e:
            logger.exception('Failed to read paused state')
            raise TaskControlError(str(e)) from e

    @property
    def current_task_name(self) -> str:
        try:
            ts = self._session.task_service
            if ts is None:
                return ''
            for name, status in ts.get_task_statuses():
                if status == 'running':
                    return name
            return ''
        except Exception as e:
            logger.exception('Failed to read current task name')
            raise TaskControlError(str(e)) from e

    def start(self) -> None:
        try:
            self._task_service().start_all_tasks()
        except TaskControlError:
            raise
        except Exception as e:
            logger.exception('Failed to start tasks')
            raise TaskControlError(str(e)) from e

    def stop(self) -> None:
        try:
            self._task_service().stop_tasks()
        except TaskControlError:
            raise
        except Exception as e:
            logger.exception('Failed to stop tasks')
            raise TaskControlError(str(e)) from e

    def toggle_pause(self) -> None:
        try:
            self._task_service().toggle_pause()
        except TaskControlError:
            raise
        except Exception as e:
            logger.exception('Failed to toggle pause')
            raise TaskControlError(str(e)) from e

    def run_single(self, name: str) -> None:
        try:
            self._task_service().start_single_task(name)
        except TaskControlError:
            raise
        except Exception as e:
            logger.exception("Failed to run task '%s'", name)
            raise TaskControlError(str(e)) from e

    def task_names(self) -> list[str]:
        try:
            ts = self._session.task_service
            if ts is None:
                return []
            return list(ts.get_all_task_names())
        except Exception as e:
            logger.exception('Failed to list task names')
            raise TaskControlError(str(e)) from e


class KaaTaskToggles(TaskTogglesSource):
    """将 Kaa 配置服务适配为 EuiShell 快速开关数据源。"""

    def __init__(self, session: 'KaaSession') -> None:
        super().__init__()
        self._session = session
        cs = session.config_service
        if cs is not None:
            cs.bus().configChanged.connect(lambda: self.togglesChanged.emit())

    def _config_service(self):
        cs = self._session.config_service
        if cs is None:
            raise TaskControlError('会话尚未初始化')
        return cs

    def toggles(self) -> list[TaskToggle]:
        cs = self._session.config_service
        if cs is None:
            return []
        try:
            config = cs.get_config()
            result: list[TaskToggle] = []
            for key, dot_path in TASK_CONFIG_PATHS.items():
                obj = config
                for part in dot_path.split('.'):
                    obj = getattr(obj, part)
                enabled = bool(obj)
                result.append(TaskToggle(
                    key=key,
                    label=TASK_SHORT_NAMES.get(key, key),
                    enabled=enabled,
                ))
            return result
        except Exception:
            logger.exception('Failed to read task toggles')
            return []

    def set_enabled(self, key: str, enabled: bool) -> None:
        dot_path = TASK_CONFIG_PATHS.get(key)
        if dot_path is None:
            raise TaskControlError(f'未知任务: {key}')
        try:
            self._config_service().apply_field(dot_path, enabled)
        except Exception as e:
            logger.exception('Failed to set task enabled: %s=%s', key, enabled)
            raise TaskControlError(str(e)) from e

    def bulk_actions(self) -> list[TaskBulkAction]:
        return [
            TaskBulkAction(label='全选', callback=lambda: self._batch_set(True)),
            TaskBulkAction(label='清空', callback=lambda: self._batch_set(False)),
            TaskBulkAction(label='只选培育', callback=lambda: self._batch_set(True, exclude='produce')),
            TaskBulkAction(label='只不选培育', callback=lambda: self._batch_set(False, exclude='produce')),
        ]

    def _batch_set(self, value: bool, exclude: str | None = None) -> None:
        """批量设置任务启用状态，可选排除某个 key（取反）。"""
        try:
            items: list[tuple[str, bool]] = []
            for key, dot_path in TASK_CONFIG_PATHS.items():
                if exclude is not None and key == exclude:
                    items.append((dot_path, not value))
                else:
                    items.append((dot_path, value))
            self._config_service().apply_fields(items)
        except Exception as e:
            logger.exception('Failed to batch set task enabled (value=%s)', value)
            raise TaskControlError(str(e)) from e
