from enum import Enum, auto
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from kaa.config.const import ProduceAction
from kotonebot.core import GameObject

if TYPE_CHECKING:
    from kaa.game_ui.commu_event_buttons import EventButton


class SceneType(Enum):
    UNKNOWN = auto()
    IDLE = auto()
    """空闲状态（什么都不做）"""
    LOADING = auto()
    """加载中"""
    ACTION_SELECT = auto()
    """行动选择"""
    PRACTICE = auto()
    """练习打牌"""
    EXAM = auto()
    """考试打牌"""
    STUDY = auto()
    """授業"""
    OUTING = auto()
    """おでかけ"""
    CONSULT = auto()
    """相談"""
    ALLOWANCE = auto()
    """活動支給"""
    HIF_ROUND_INTERVAL = auto()
    """HIF 两轮 Round 之间的中场休息"""


    SELECT_DRINK = auto()
    """选择饮料"""
    SELECT_CARD = auto()
    """选择卡片"""
    SELECT_PITEM = auto()
    """选择 P 道具"""
    SKILL_CARD_ENHANCE = auto()
    """技能卡自选强化"""
    SKILL_CARD_REMOVAL = auto()
    """技能卡自选删除"""
    SKILL_CARD_CHANGE_1 = auto()
    """技能卡自选变更，阶段 1"""
    SKILL_CARD_CHANGE_2 = auto()
    """技能卡自选变更，阶段 2"""

    INITIAL_DRINK_OR_CARD_SELECT = auto()

    PDRINK_MAX = auto()
    """P饮料到达上限弹窗"""

    PDRINK_MAX_CONFIRM = auto()
    """P饮料到达上限确认弹窗"""

    PRODUCE_END = auto()
    """培育结算"""


@dataclass
class Scene:
    type: SceneType

@dataclass
class InitialDrinkOrCardSelectScene(Scene):
    buttons: 'list[EventButton]'

@dataclass
class Drink:
    index: int

@dataclass
class SelectDrinkDialog:
    can_skip: bool
    drinks: list[Drink]

    _skip_button: GameObject | None

@dataclass
class PerformanceMetricsVal:
    current: int
    max: int
    lesson: Literal[ProduceAction.VOCAL, ProduceAction.DANCE, ProduceAction.VISUAL]