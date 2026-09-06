"""KaaSession — KAA 业务会话，实现 EuiShell 的 ShellSession 协议。

每个 profile 对应一个 KaaSession，持有 Kaa 实例和所有服务；
通过 TabApi 接收 shell 侧对象（进度桥接等）并推送任务事件。
"""
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from euishell.session import ShellSession, TabApi

from kaa.application.ui.task_control import KaaTaskControl, KaaTaskToggles

if TYPE_CHECKING:
    from kaa.main.kaa import Kaa

logger = logging.getLogger(__name__)


class KaaSession(ShellSession):
    """管理一个 profile 的 Kaa 实例和所有服务的生命周期。"""

    def __init__(self, profile_name: str) -> None:
        """
        :param profile_name: 配置名称
        """
        self._profile_name = profile_name
        self._kaa: 'Kaa | None' = None
        self._initialized = False

        # Services (created on initialize)
        self._config_service = None
        self._task_service = None
        self._produce_solution_service = None
        self._produce_solutions_model = None
        self._update_service = None
        self._feedback_service = None
        self._instance_service = None

        # EuiShell 侧对象（attach_tab 注入）
        self._tab_api: TabApi | None = None
        self._progress_installed = False
        self._total_tasks = 0
        """本轮运行的任务总数（用于进度百分比）。"""
        self._finished_tasks = 0
        """本轮已完成的任务数。"""

        # 控制器（惰性创建，主线程）
        self._task_control: KaaTaskControl | None = None
        self._task_toggles: KaaTaskToggles | None = None
        self._settings_ctrl = None
        self._produce_ctrl = None
        self._update_ctrl = None
        self._feedback_ctrl = None
        self._control_ctrl = None

    def initialize(self) -> None:
        """创建 Kaa 实例和所有服务。重复调用安全（幂等）。"""
        if self._initialized:
            return

        from kaa.main.kaa import Kaa
        from kaa.application.services.config_service import ConfigService
        from kaa.application.services.task_service import TaskService
        from kaa.application.services.produce_solution_service import ProduceSolutionService
        from kaa.application.services.update_service import UpdateService
        from kaa.application.services.feedback_service import FeedbackService
        from kaa.application.services.instant_service import InstantService

        self._kaa = Kaa(profile_name=self._profile_name)
        self._config_service = ConfigService(name=self._profile_name)
        self._task_service = TaskService(self._kaa)
        self._produce_solution_service = ProduceSolutionService()
        self._update_service = UpdateService()
        self._feedback_service = FeedbackService(kaa_getter=lambda: self._kaa)
        self._instance_service = InstantService()
        self._initialized = True
        logger.info("KaaSession: initialized for '%s'", self._profile_name)

    def destroy(self) -> None:
        """停止 Kaa 并清空引用。重复调用安全（幂等）。"""
        self._uninstall_progress()
        if self._kaa is not None:
            try:
                self._kaa.stop()
            except Exception:
                logger.exception("KaaSession: error stopping Kaa for '%s'", self._profile_name)
        self._kaa = None
        self._config_service = None
        self._task_service = None
        self._produce_solution_service = None
        self._produce_solutions_model = None
        self._update_service = None
        self._feedback_service = None
        self._instance_service = None
        self._initialized = False
        logger.info("KaaSession: destroyed '%s'", self._profile_name)

    # ── ShellSession 协议 ────────────────────────────────────

    @property
    def profile_id(self) -> str:
        return self._profile_name

    @property
    def title(self) -> str:
        return self._profile_name

    @property
    def is_running(self) -> bool:
        """当前是否有任务在运行。"""
        if self._task_service is None:
            return False
        try:
            from kotonebot.errors import ContextNotInitializedError
            return self._task_service.is_running()
        except ContextNotInitializedError:
            return False
        except Exception:
            return False

    def attach_tab(self, api: TabApi) -> None:
        """接收 shell 侧对象并订阅任务事件推送进度。"""
        self._tab_api = api
        self._install_progress(api)

    def task_control(self) -> KaaTaskControl:
        return self._get_or_create('_task_control', KaaTaskControl)

    def task_toggles(self) -> KaaTaskToggles:
        return self._get_or_create('_task_toggles', KaaTaskToggles)

    def settings_controller(self):
        from kaa.application.ui.controllers.settings_controller import SettingsController
        return self._get_or_create('_settings_ctrl', SettingsController)

    def controllers(self) -> dict[str, QObject]:
        from kaa.application.ui.controllers.control_controller import KaaControlController
        from kaa.application.ui.controllers.feedback_controller import FeedbackController
        from kaa.application.ui.controllers.produce_controller import ProduceController
        from kaa.application.ui.controllers.update_controller import UpdateController
        return {
            'control': self._get_or_create('_control_ctrl', KaaControlController),
            'produce': self._get_or_create('_produce_ctrl', ProduceController),
            'update': self._get_or_create('_update_ctrl', UpdateController),
            'feedback': self._get_or_create('_feedback_ctrl', FeedbackController),
        }

    def dirty_guards(self) -> list[QObject]:
        guards: list[QObject] = []
        settings = self.settings_controller()
        if settings is not None:
            guards.append(settings)
        produce = self.controllers().get('produce')
        if produce is not None:
            guards.append(produce)
        return guards

    # ── 进度推送 ─────────────────────────────────────────────

    def _install_progress(self, api: TabApi) -> None:
        """订阅 kaa.events，把任务状态变化推送到 shell 进度桥接。"""
        if self._progress_installed or self._kaa is None:
            return
        try:
            self._kaa.events.task_status_changed += self._on_task_status_changed
            self._kaa.events.stopped += self._on_stopped
            self._progress_installed = True

            # 初始化任务总数用于百分比计算
            ts = self._task_service
            if ts is not None:
                self._total_tasks = len(ts.get_task_statuses())
            api.progress.reset()
        except Exception:
            logger.exception('Failed to install progress callbacks')

    def _uninstall_progress(self) -> None:
        if not self._progress_installed or self._kaa is None:
            return
        try:
            self._kaa.events.task_status_changed -= self._on_task_status_changed
            self._kaa.events.stopped -= self._on_stopped
        except Exception:
            logger.exception('Failed to uninstall progress callbacks')
        self._progress_installed = False

    def _on_task_status_changed(self, task, status: str) -> None:
        """task_status_changed 回调。

        :param task: Task 对象，有 ``.name`` 属性。
        :param status: ``'running'`` 或 ``'finished'``。
        """
        api = self._tab_api
        if api is None:
            return
        try:
            task_name = getattr(task, 'name', str(task))
            if status == 'running':
                api.progress.update_status(f'运行中: {task_name}')
            elif status == 'finished':
                self._finished_tasks += 1
                if self._total_tasks > 0:
                    api.progress.update_progress(int(self._finished_tasks / self._total_tasks * 100))
                api.progress.update_status(f'已完成: {task_name}')
        except Exception:
            logger.exception('Error in KaaSession._on_task_status_changed')

    def _on_stopped(self, reason, exc) -> None:
        """stopped 回调。

        :param reason: BotStopReason 枚举（str, Enum）。
        :param exc: 异常对象或 None。
        """
        api = self._tab_api
        if api is None:
            return
        try:
            reason_name = getattr(reason, 'name', str(reason))
            if reason_name == 'COMPLETED':
                api.progress.update_status('已完成')
                api.progress.update_progress(100)
            elif reason_name == 'USER_REQUEST':
                api.progress.update_status('已停止')
            elif reason_name == 'ERROR' and exc is not None:
                api.progress.set_error(str(exc))
            # 新一轮运行前重置计数
            self._finished_tasks = 0
        except Exception:
            logger.exception('Error in KaaSession._on_stopped')

    # ── 内部工具 ─────────────────────────────────────────────

    def _get_or_create(self, attr: str, factory):
        """惰性创建并缓存控制器。"""
        value = getattr(self, attr)
        if value is None:
            value = factory(self)
            setattr(self, attr, value)
        return value

    # ── 兼容访问器（kaa 内部使用）───────────────────────────

    @property
    def profile_name(self) -> str:
        return self._profile_name

    @property
    def kaa(self) -> 'Kaa | None':
        return self._kaa

    @property
    def config_service(self):
        return self._config_service

    @property
    def task_service(self):
        return self._task_service

    @property
    def produce_solution_service(self):
        return self._produce_solution_service

    @property
    def produce_solutions_model(self):
        return self._produce_solutions_model

    @property
    def update_service(self):
        return self._update_service

    @property
    def feedback_service(self):
        return self._feedback_service

    @property
    def instance_service(self):
        return self._instance_service
