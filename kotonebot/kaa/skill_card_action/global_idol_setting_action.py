import json
import os
from logging import getLogger

from kotonebot.kaa.db import IdolCard
from kotonebot.kaa.skill_card.card_deck_config import DeckConfig
from kotonebot.kaa.skill_card.global_idol_setting import GlobalIdolSetting

logger = getLogger(__name__)


# TODO: 获取默认配置
def get_default_config() -> DeckConfig:
    path = os.path.join(os.path.dirname(__file__), 'default_card_deck_config.json')
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, 'r', encoding='utf-8') as f:
        root = json.load(f)
    return DeckConfig.model_validate(root)


# TODO: 这里应该在游戏开始就初始化，在新培育、继续培育时调用new_play()待更新，在读取偶像信息后调用update_deck()完成更新
idol_setting = GlobalIdolSetting()
# TODO: 这里应该从配置文件中读取
deck_config = get_default_config()


def update_archetype_by_idol_skin_id(idol_skin_id: str):
    """
    根据偶像皮肤id，更新全局偶像信息
    :param idol_skin_id: 
    :return: 
    """
    idol_setting.new_play()
    idol_card = IdolCard.from_skin_id(idol_skin_id)
    if idol_card:
        idol_setting.update_deck(idol_card.exam_effect_type, deck_config)
    else:
        logger.warning(f"Can`t found archetype by skin id: {idol_skin_id}")