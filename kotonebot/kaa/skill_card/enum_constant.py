from enum import IntEnum


# 卡牌抉择优先度，越大优先度越低
class CardPriority(IntEnum):
    core = 0
    high = 1
    medium = 2
    low = 3
    other = 99
