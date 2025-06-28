from dataclasses import dataclass
from logging import getLogger

from kotonebot.kaa.db.constants import ExamEffectType
from kotonebot.kaa.skill_card.card_deck_config import DeckConfig, SingleDeckConfig
from kotonebot.kaa.skill_card.enum_constant import CardPriority

logger = getLogger(__name__)


@dataclass
class GlobalIdolSetting:
    def __init__(self):
        # 是否需要刷新全局配置，理论上新开培育、重新培育都需要更新
        self.need_update: bool = True
        self.idol_archetype: ExamEffectType = ExamEffectType.good_impression
        self.card_deck: dict = {}
        self.select_once_card_before_refresh = True

    def new_play(self):
        self.need_update = True
        self.select_once_card_before_refresh = True
        self.card_deck.clear()
        logger.info("New game, wait for update")

    def update_deck(self, idol_archetype: ExamEffectType, config: DeckConfig):
        """
        根据流派选择初始化对应的卡组配置，如果自定义有就使用自定义，没有就使用预设
        :param idol_archetype: 偶像流派
        :param config: 卡组配置
        :return: 
        """
        if not self.need_update:
            return
        self.idol_archetype = idol_archetype
        self.need_update = False
        self.card_deck.clear()
        for single_deck_config in config.custom_deck:
            if single_deck_config.archetype == idol_archetype:
                self.refresh_card_deck(single_deck_config)
                logger.info("Use custom card deck,idol archetype:%s", idol_archetype)
                return
        for single_deck_config in config.pre_built_deck:
            if single_deck_config.archetype == idol_archetype:
                self.refresh_card_deck(single_deck_config)
                logger.info("Use pre built card deck,idol archetype:%s", idol_archetype)
                return
        logger.warning("No deck config for idol archetype: %s", idol_archetype)
        self.need_update = True

    def refresh_card_deck(self, card_deck_config: SingleDeckConfig):
        self.card_deck.update({card: CardPriority.low for card in card_deck_config.low_priority_cards})
        self.card_deck.update({card: CardPriority.medium for card in card_deck_config.medium_priority_cards})
        self.card_deck.update({card: CardPriority.high for card in card_deck_config.high_priority_cards})
        self.card_deck.update({card: CardPriority.core for card in card_deck_config.core_cards})
        self.select_once_card_before_refresh = card_deck_config.select_once_card_before_refresh

    def get_card_priority(self, card_id: str) -> CardPriority:
        """
        根据卡名来查看此卡的选卡优先级
        :param card_id: 卡id
        :return: 优先级，越小越高，不在配置卡组则返回other(99)
        """
        return self.card_deck.get(card_id, CardPriority.other)
