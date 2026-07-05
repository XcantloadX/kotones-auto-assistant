"""KaaSession — Kaa 实例 + 服务容器的生命周期管理。

每个 profile 对应一个 KaaSession，持有 Kaa 实例和所有服务。
"""
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kaa.main.kaa import Kaa

logger = logging.getLogger(__name__)


class KaaSession:
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
        self._feedback_service = FeedbackService()
        self._instance_service = InstantService()
        self._initialized = True
        logger.info("KaaSession: initialized for '%s'", self._profile_name)

    def destroy(self) -> None:
        """停止 Kaa 并清空引用。重复调用安全（幂等）。"""
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
