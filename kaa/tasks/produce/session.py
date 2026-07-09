import logging
from dataclasses import dataclass
from enum import Enum
from typing import Union

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
    scenario: Scenario
    is_resumed: bool

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
