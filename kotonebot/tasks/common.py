from enum import IntEnum, Enum
from typing import Literal

from pydantic import BaseModel

from kotonebot import config

class Priority(IntEnum):
    START_GAME = 1
    DEFAULT = 0
    CLAIM_MISSION_REWARD = -1


class APShopItems(IntEnum):
    PRODUCE_PT_UP = 0
    """获取支援强化 Pt 提升"""
    PRODUCE_NOTE_UP = 1
    """获取笔记数提升"""
    RECHALLENGE = 2
    """再挑战券"""
    REGENERATE_MEMORY = 3
    """回忆再生成券"""


class PIdols(Enum):
    pass

    
class PurchaseConfig(BaseModel):
    enabled: bool = False
    """是否启用商店购买"""
    money_enabled: bool = False
    """是否启用金币购买"""
    ap_enabled: bool = False
    """是否启用AP购买"""
    ap_items: list[Literal[0, 1, 2, 3]] = []
    """AP商店要购买的物品"""


class ActivityFundsConfig(BaseModel):
    enabled: bool = False
    """是否启用收取活动费"""


class PresentsConfig(BaseModel):
    enabled: bool = False
    """是否启用收取礼物"""


class AssignmentConfig(BaseModel):
    enabled: bool = False
    """是否启用工作"""

    mini_live_reassign_enabled: bool = False
    """是否启用重新分配 MiniLive"""
    mini_live_duration: Literal[4, 6, 12] = 12
    """MiniLive 工作时长"""

    online_live_reassign_enabled: bool = False
    """是否启用重新分配 OnlineLive"""
    online_live_duration: Literal[4, 6, 12] = 12
    """OnlineLive 工作时长"""


class ContestConfig(BaseModel):
    enabled: bool = False
    """是否启用竞赛"""


class ProduceConfig(BaseModel):
    enabled: bool = False
    """是否启用培育"""
    mode: Literal['regular'] = 'regular'
    """培育模式。"""
    produce_count: int = 1
    """培育的次数。"""
    idols: list[str] = []
    """要培育的偶像。将会按顺序循环选择培育。"""
    memory_sets: list[int] = []
    """要使用的回忆编成编号，从 1 开始。将会按顺序循环选择使用。"""
    support_card_sets: list[int] = []
    """要使用的支援卡编成编号，从 1 开始。将会按顺序循环选择使用。"""
    auto_set_memory: bool = False
    """是否自动编成回忆。此选项优先级高于回忆编成编号。"""
    auto_set_support_card: bool = False
    """是否自动编成支援卡。此选项优先级高于支援卡编成编号。"""
    use_pt_boost: bool = False
    """是否使用支援强化 Pt 提升。"""
    use_note_boost: bool = False
    """是否使用笔记数提升。"""
    follow_producer: bool = False
    """是否关注租借了支援卡的制作人。"""


class MissionRewardConfig(BaseModel):
    enabled: bool = False
    """是否启用领取任务奖励"""


class BaseConfig(BaseModel):
    purchase: PurchaseConfig = PurchaseConfig()
    """商店购买配置"""

    activity_funds: ActivityFundsConfig = ActivityFundsConfig()
    """活动费配置"""

    presents: PresentsConfig = PresentsConfig()
    """收取礼物配置"""

    assignment: AssignmentConfig = AssignmentConfig()
    """工作配置"""

    contest: ContestConfig = ContestConfig()
    """竞赛配置"""

    produce: ProduceConfig = ProduceConfig()
    """培育配置"""

    mission_reward: MissionRewardConfig = MissionRewardConfig()
    """领取任务奖励配置"""



def conf() -> BaseConfig:
    """获取当前配置数据"""
    c = config.to(BaseConfig).current
    return c.options
