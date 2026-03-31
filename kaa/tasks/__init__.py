from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from kotonebot.backend.context.task_action import TaskFuncProtocol

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

# 任务注册表
# 每次添加新任务时，都需要修改此处代码
TASK_REGISTRY: dict[str, 'TaskFuncProtocol'] = {
    'clear_logs': clear_logs,
    'start_game': start_game,

    'acquire_activity_funds': acquire_activity_funds,
    'acquire_presents': acquire_presents,
    'assignment': assignment,
    'capsule_toys': capsule_toys,
    'club_reward': club_reward,
    'contest': contest,
    'purchase': purchase,
    'upgrade_support_card': upgrade_support_card,
    
    'produce': produce,
    
    'mission_reward': mission_reward,
}
"""任务注册表"""

POST_TASK_REGISTRY: dict[str, 'TaskFuncProtocol'] = {
    'end_game': end_game,
}
"""后置任务注册表"""

TASK_FUNCTIONS: 'list[TaskFuncProtocol]' = list(TASK_REGISTRY.values())
"""任务列表"""