from dataclasses import dataclass

from kotonebot.kaa.skill_card.enum_constant import CardName, PlanType, CardType


@dataclass
class CardTemplate:
    """
    卡牌模板
    理论上应该保存到数据库上，相关属性就不需要识别
    """
    # 卡牌名称
    name: CardName
    # 卡牌职业分类，感性、理性等
    plan_type: PlanType
    # 卡牌作用类型,a卡，m卡等
    card_type: CardType
    # 一回一次
    once: bool = False

    # 以下信息可能在以后会用到，这里先不写了
    # good_condition: bool = False  # 好调
    # focus: bool = False  # 集中
    # 
    # good_impression: bool = False  # 好印象
    # motivation: bool = False  # 干劲
    # 
    # confidence: bool = False  # 强气
    # conservation: bool = False  # 温存
    # full_power: bool = False  # 全力
    # 
    # energy: bool = False  # 护盾


# TODO 从数据库中读取对应的卡牌信息，读取完成后更新 card_template_dict
card_collection = [
    # unidentified 当识别过程无法找到对应的卡时，使用这个而不是眠气卡
    CardTemplate(CardName.unidentified, PlanType.common, CardType.trouble, once=False),

    # common
    CardTemplate(CardName.c_n_0, PlanType.common, CardType.trouble, once=True),
    CardTemplate(CardName.c_n_1, PlanType.common, CardType.active, once=False),
    CardTemplate(CardName.c_n_2, PlanType.common, CardType.active, once=False),
    CardTemplate(CardName.c_n_3, PlanType.common, CardType.mental, once=True),

    CardTemplate(CardName.c_r_1, PlanType.common, CardType.mental, once=False),
    CardTemplate(CardName.c_r_2, PlanType.common, CardType.mental, once=True),

    CardTemplate(CardName.c_sr_1, PlanType.common, CardType.active, once=False),
    CardTemplate(CardName.c_sr_2, PlanType.common, CardType.mental, once=True),
    CardTemplate(CardName.c_sr_3, PlanType.common, CardType.mental, once=True),

    CardTemplate(CardName.c_ssr_1, PlanType.common, CardType.mental, once=True),
    CardTemplate(CardName.c_ssr_2, PlanType.common, CardType.mental, once=True),
    CardTemplate(CardName.c_ssr_3, PlanType.common, CardType.mental, once=True),
    CardTemplate(CardName.c_ssr_4, PlanType.common, CardType.mental, once=True),

    # sense
    CardTemplate(CardName.s_n_1, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_n_2, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_n_3, PlanType.sense, CardType.mental, once=False),
    CardTemplate(CardName.s_n_4, PlanType.sense, CardType.mental, once=False),

    CardTemplate(CardName.s_r_1, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_r_2, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_r_3, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_r_4, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_r_5, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_r_6, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_r_7, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_r_8, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_r_9, PlanType.sense, CardType.mental, once=False),
    CardTemplate(CardName.s_r_10, PlanType.sense, CardType.mental, once=False),
    CardTemplate(CardName.s_r_11, PlanType.sense, CardType.mental, once=False),
    CardTemplate(CardName.s_r_12, PlanType.sense, CardType.mental, once=True),

    CardTemplate(CardName.s_sr_1, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_sr_2, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_sr_3, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_sr_4, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_sr_5, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_sr_6, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_sr_7, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_sr_8, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_sr_9, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_sr_10, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_sr_11, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_sr_12, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_sr_13, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_sr_14, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_sr_15, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_sr_16, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_sr_17, PlanType.sense, CardType.mental, once=False),
    CardTemplate(CardName.s_sr_18, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_sr_19, PlanType.sense, CardType.mental, once=False),

    CardTemplate(CardName.s_ssr_1, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_ssr_2, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_ssr_3, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_ssr_4, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_ssr_5, PlanType.sense, CardType.active, once=True),
    CardTemplate(CardName.s_ssr_6, PlanType.sense, CardType.active, once=False),
    CardTemplate(CardName.s_ssr_7, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_ssr_8, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_ssr_9, PlanType.sense, CardType.mental, once=True),
    CardTemplate(CardName.s_ssr_10, PlanType.sense, CardType.mental, once=True),

    # logic
    CardTemplate(CardName.l_n_1, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_n_2, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_n_3, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_n_4, PlanType.logic, CardType.mental, once=False),

    CardTemplate(CardName.l_r_1, PlanType.logic, CardType.active, once=False),
    CardTemplate(CardName.l_r_2, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_r_3, PlanType.logic, CardType.active, once=False),
    CardTemplate(CardName.l_r_4, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_r_5, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_r_6, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_r_7, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_r_8, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_r_9, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_r_10, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_r_11, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_r_12, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_r_13, PlanType.logic, CardType.mental, once=True),

    CardTemplate(CardName.l_sr_1, PlanType.logic, CardType.active, once=False),
    CardTemplate(CardName.l_sr_2, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_sr_3, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_sr_4, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_sr_5, PlanType.logic, CardType.active, once=False),
    CardTemplate(CardName.l_sr_6, PlanType.logic, CardType.active, once=False),
    CardTemplate(CardName.l_sr_7, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_sr_8, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_sr_9, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_sr_10, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_sr_11, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_sr_12, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_sr_13, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_sr_14, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_sr_15, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_sr_16, PlanType.logic, CardType.mental, once=False),
    CardTemplate(CardName.l_sr_17, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_sr_18, PlanType.logic, CardType.mental, once=False),

    CardTemplate(CardName.l_ssr_1, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_ssr_2, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_ssr_3, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_ssr_4, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_ssr_5, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_ssr_6, PlanType.logic, CardType.active, once=True),
    CardTemplate(CardName.l_ssr_7, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_ssr_8, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_ssr_9, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_ssr_10, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_ssr_11, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_ssr_12, PlanType.logic, CardType.mental, once=True),
    CardTemplate(CardName.l_ssr_13, PlanType.logic, CardType.mental, once=True),

    # anomaly
    CardTemplate(CardName.a_n_1, PlanType.anomaly, CardType.active, once=False),
    CardTemplate(CardName.a_n_2, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_n_3, PlanType.anomaly, CardType.active, once=False),
    CardTemplate(CardName.a_n_4, PlanType.anomaly, CardType.mental, once=False),
    CardTemplate(CardName.a_n_5, PlanType.anomaly, CardType.mental, once=False),

    CardTemplate(CardName.a_r_1, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_r_2, PlanType.anomaly, CardType.active, once=False),
    CardTemplate(CardName.a_r_3, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_r_4, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_r_5, PlanType.anomaly, CardType.active, once=False),
    CardTemplate(CardName.a_r_6, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_r_7, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_r_8, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_r_9, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_r_10, PlanType.anomaly, CardType.mental, once=True),

    CardTemplate(CardName.a_sr_1, PlanType.anomaly, CardType.active, once=False),
    CardTemplate(CardName.a_sr_2, PlanType.anomaly, CardType.active, once=False),
    CardTemplate(CardName.a_sr_3, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_sr_4, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_sr_5, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_sr_6, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_sr_7, PlanType.anomaly, CardType.active, once=False),
    CardTemplate(CardName.a_sr_8, PlanType.anomaly, CardType.active, once=False),
    CardTemplate(CardName.a_sr_9, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_sr_10, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_sr_11, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_sr_12, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_sr_13, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_sr_14, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_sr_15, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_sr_16, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_sr_17, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_sr_18, PlanType.anomaly, CardType.mental, once=False),
    CardTemplate(CardName.a_sr_19, PlanType.anomaly, CardType.mental, once=True),

    CardTemplate(CardName.a_ssr_1, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_ssr_2, PlanType.anomaly, CardType.active, once=False),
    CardTemplate(CardName.a_ssr_3, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_ssr_4, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_ssr_5, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_ssr_6, PlanType.anomaly, CardType.active, once=True),
    CardTemplate(CardName.a_ssr_7, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_ssr_8, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_ssr_9, PlanType.anomaly, CardType.mental, once=True),
    CardTemplate(CardName.a_ssr_10, PlanType.anomaly, CardType.mental, once=True),
]

card_template_dict = {card.name: card for card in card_collection}
