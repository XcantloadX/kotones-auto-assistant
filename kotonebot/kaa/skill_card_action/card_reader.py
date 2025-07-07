from logging import getLogger
from dataclasses import dataclass

from kotonebot.kaa.db.skill_card import PlayMovePositionType
from kotonebot.kaa.game_ui.skill_card_select import SkillCardElement
from kotonebot.kaa.skill_card.enum_constant import CardPriority
from kotonebot.kaa.skill_card_action.global_idol_setting_action import idol_setting

logger = getLogger(__name__)


@dataclass
class ActualCard:
    skill_card_element: SkillCardElement
    priority: CardPriority

    @staticmethod
    def create_by(card: SkillCardElement) -> 'ActualCard':
        """
        :param card: 读取到的技能卡信息
        :return: cls
        """
        priority = idol_setting.get_card_priority(card.skill_card.id)
        return ActualCard(card, priority)

    def __lt__(self, other):
        return self.priority < other.priority

    def select(self) -> bool:
        """
        选卡时可以选择
        :return: 
        """
        return self.priority != CardPriority.other
    
    def lost(self):
        """
        是否为 除外 卡
        :return: 
        """
        return self.skill_card_element.skill_card.play_move_position_type == PlayMovePositionType.LOST
