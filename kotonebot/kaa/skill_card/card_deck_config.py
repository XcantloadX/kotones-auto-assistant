from kotonebot.kaa.common import ConfigBaseModel
from kotonebot.kaa.db.constants import ExamEffectType


# TODO: 这个文件应该写在 kotonebot.kaa.common 的 BaseConfig文件中
# TODO：用户可以设置自己的流派卡组，把卡填入下面的设置中，未填入的卡默认不选。
# 单流派卡组设置
class SingleDeckConfig(ConfigBaseModel):
    # 角色流派。目前只考虑ExamEffectType，温存目前分全力温存和强气温存，所以没有温存设置。
    archetype: ExamEffectType
    # 核心卡，在商店页面会购买
    core_cards: list[str] = []
    # 高优先度卡
    high_priority_cards: list[str] = []
    # 中优先度卡
    medium_priority_cards: list[str] = []
    # 低优先度卡
    low_priority_cards: list[str] = []


# 所有卡组设置
class DeckConfig(ConfigBaseModel):
    # 预设卡组
    pre_built_deck: list[SingleDeckConfig]
    # 自定义卡组
    custom_deck: list[SingleDeckConfig]
