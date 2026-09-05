from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from kotonebot.backend.context.task_action import TaskFuncProtocol
    from kaa.config.schema import KaaConfig

from .clear_logs import clear_logs
from .start_game import start_game
from .end_game import end_game

from .daily.acquire_activity_funds import acquire_activity_funds
from .daily.acquire_presents import acquire_presents
from .daily.assignment import assignment
from .daily.capsule_toys import capsule_toys
from .daily.club_reward import club_reward
from .daily.contest import contest
from .daily.mission_reward import mission_reward
from .daily.purchase import purchase
from .daily.upgrade_support_card import upgrade_support_card

from .produce.produce import produce


@dataclass(frozen=True)
class TaskInfo:
    """任务元信息。集中描述一个任务的运行与启用规则。

    ``config_name`` 为 ``config.tasks`` 下控制该任务启用状态的字段名（例如
    ``'activity_funds'``）。为 ``None`` 表示该任务没有启用开关，始终参与调度
    （如 ``start_game``、``clear_logs``）。
    """
    task_id: str
    """唯一任务标识符。"""
    func: 'TaskFuncProtocol'
    """实际的 kotonebot 任务函数。"""
    config_name: str | None = None
    """``config.tasks`` 下控制该任务启用状态的字段名；为 None 表示始终启用。"""

    @property
    def display_name(self) -> str:
        """任务的展示名称（取自任务函数）。"""
        return self.func.task.name

    def get_enabled(self, config: 'KaaConfig') -> bool:
        """判断任务在当前配置下是否启用。集中在此处判断，任务自身不再自行判断。"""
        if self.config_name is None:
            return True
        return config.tasks.is_enabled(self.config_name)


# 任务注册表
# 每次添加新任务时，都需要修改此处代码
TASK_REGISTRY: dict[str, TaskInfo] = {
    'clear_logs': TaskInfo('clear_logs', clear_logs),
    'start_game': TaskInfo('start_game', start_game),

    'acquire_activity_funds': TaskInfo(
        'acquire_activity_funds', acquire_activity_funds,
        config_name='activity_funds',
    ),
    'acquire_presents': TaskInfo(
        'acquire_presents', acquire_presents,
        config_name='presents',
    ),
    'assignment': TaskInfo(
        'assignment', assignment,
        config_name='assignment',
    ),
    'capsule_toys': TaskInfo(
        'capsule_toys', capsule_toys,
        config_name='capsule_toys',
    ),
    'club_reward': TaskInfo(
        'club_reward', club_reward,
        config_name='club_reward',
    ),
    'contest': TaskInfo(
        'contest', contest,
        config_name='contest',
    ),
    'purchase': TaskInfo(
        'purchase', purchase,
        config_name='purchase',
    ),
    'upgrade_support_card': TaskInfo(
        'upgrade_support_card', upgrade_support_card,
        config_name='upgrade_support_card',
    ),

    'produce': TaskInfo(
        'produce', produce,
        config_name='produce',
    ),

    'mission_reward': TaskInfo(
        'mission_reward', mission_reward,
        config_name='mission_reward',
    ),
}
"""任务注册表"""


POST_TASK_REGISTRY: dict[str, TaskInfo] = {
    'end_game': TaskInfo('end_game', end_game),
}
"""后置任务注册表"""


def list_enabled_tasks(config: 'KaaConfig') -> list[TaskInfo]:
    """返回按注册顺序排列的、当前配置下启用的常规任务。
    """
    return [info for info in TASK_REGISTRY.values() if info.get_enabled(config)]
