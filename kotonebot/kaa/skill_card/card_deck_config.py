
from kotonebot.kaa.common import ConfigBaseModel

from kotonebot.kaa.skill_card.enum_constant import Archetype, CardName


# TODO: 这个文件应该写在 kotonebot.kaa.common 的 BaseConfig文件中
# TODO：用户可以设置自己的流派卡组，把卡填入下面的设置中，未填入的卡默认不选。
# 单流派卡组设置
class SingleDeckConfig(ConfigBaseModel):
    # 角色流派
    archetype: Archetype
    # 当可选卡不在设置中，是否优先选择其中的一次性卡？false会直接进行刷新
    select_once_card_before_refresh: bool = True
    # 核心卡，在商店页面会购买
    core_cards: list[CardName] = []
    # 高优先度卡
    high_priority_cards: list[CardName] = []
    # 中优先度卡
    medium_priority_cards: list[CardName] = []
    # 低优先度卡
    low_priority_cards: list[CardName] = []


# 所有卡组设置
class DeckConfig(ConfigBaseModel):
    # 预设卡组
    pre_built_deck: list[SingleDeckConfig]
    # 自定义卡组
    custom_deck: list[SingleDeckConfig]
