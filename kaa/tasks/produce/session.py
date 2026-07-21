import logging
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import Union

from kaa.config.deck import CardDeck
from kaa.db.idol_card import IdolCard
from kaa.db.constants import ProduceExamEffectType, ShowExamEffectType

logger = logging.getLogger(__name__)

class HajimeScenario(Enum):
    REGULAR = 'hajime_regular'
    PRO = 'hajime_pro'
    MASTER = 'hajime_master'

# Future:
# class NiaScenario(Enum):
#     PRO = 'nia_pro'
#     MASTER = 'nia_master'
# class HifScenario(Enum):
#     REGULAR = 'hif'

Scenario = Union[HajimeScenario]

@dataclass
class ProduceSession:
    idol_card: str
    """偶像卡 skin_id。"""
    scenario: Scenario
    """培育方案类型。"""
    is_resumed: bool
    """是否为继续培育。"""
    deck: CardDeck | None = None
    """该次培育使用的卡组。为空时表示无卡组（不使用优先级选卡）。"""

    _card: IdolCard | None = field(default=None, init=False, repr=False)

    @cached_property
    def archetype(self) -> ProduceExamEffectType | None:
        if self._card is None:
            self._card = IdolCard.from_skin_id(self.idol_card)
        return self._card.exam_effect_type if self._card else None

    @cached_property
    def show_archetype(self) -> ShowExamEffectType | None:
        if self._card is None:
            self._card = IdolCard.from_skin_id(self.idol_card)
        return self._card.show_exam_effect_type if self._card else None


def resolve_deck(skin_id: str, card_deck_id: str | None) -> CardDeck | None:
    """根据偶像卡 skin_id 和可选的卡组 ID 解析出 CardDeck。"""
    from kaa.config.deck import CardDeckManager
    from kaa.config.deck_defaults import get_default_deck

    card = IdolCard.from_skin_id(skin_id)
    archetype = card.exam_effect_type if card else None
    if archetype is None:
        return None

    if card_deck_id:
        try:
            return CardDeckManager().read(card_deck_id)
        except Exception:
            logger.exception('Failed to read card deck %s, falling back to default deck.', card_deck_id)
            return get_default_deck(archetype)
    else:
        logger.warning('No card deck ID provided, using default deck for archetype %s.', archetype)
        return get_default_deck(archetype)

def identify_idol_card(card_img):
    """从偶像卡截图识别 skin_id。"""
    if card_img is None:
        return None
    from kaa.game_ui.idols_overview import idols_db
    db = idols_db()
    match = db.match(card_img, 20)
    if match is None:
        logger.warning('Failed to match idol card image.')
        return None
    skin_id = match.key.rsplit('_', 1)[0]
    logger.info('Identified idol card: %s (key=%s)', skin_id, match.key)
    return skin_id
