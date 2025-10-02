from enum import IntEnum

倉本千奈_BASE = 0
十王星南_BASE = 100
姫崎莉波_BASE = 200
月村手毬_BASE = 300
有村麻央_BASE = 400
篠泽广_BASE = 500
紫云清夏_BASE = 600
花海佑芽_BASE = 700
花海咲季_BASE = 800
葛城リーリヤ_BASE = 900
藤田ことね_BASE = 1000

class PIdol(IntEnum):
    """P 偶像。（仅用于旧版配置升级。）"""
    倉本千奈_Campusmode = 倉本千奈_BASE + 0
    倉本千奈_WonderScale = 倉本千奈_BASE + 1
    倉本千奈_ようこそ初星温泉 = 倉本千奈_BASE + 2
    倉本千奈_仮装狂騒曲 = 倉本千奈_BASE + 3
    倉本千奈_初心 = 倉本千奈_BASE + 4
    倉本千奈_学園生活 = 倉本千奈_BASE + 5
    倉本千奈_日々_発見的ステップ = 倉本千奈_BASE + 6
    倉本千奈_胸を張って一歩ずつ = 倉本千奈_BASE + 7

    十王星南_Campusmode = 十王星南_BASE + 0
    十王星南_一番星 = 十王星南_BASE + 1
    十王星南_学園生活 = 十王星南_BASE + 2
    十王星南_小さな野望 = 十王星南_BASE + 3

    姫崎莉波_clumsytrick = 姫崎莉波_BASE + 0
    姫崎莉波_私らしさのはじまり = 姫崎莉波_BASE + 1
    姫崎莉波_キミとセミブルー = 姫崎莉波_BASE + 2
    姫崎莉波_Campusmode = 姫崎莉波_BASE + 3
    姫崎莉波_LUV = 姫崎莉波_BASE + 4
    姫崎莉波_ようこそ初星温泉 = 姫崎莉波_BASE + 5
    姫崎莉波_ハッピーミルフィーユ = 姫崎莉波_BASE + 6
    姫崎莉波_初心 = 姫崎莉波_BASE + 7
    姫崎莉波_学園生活 = 姫崎莉波_BASE + 8

    月村手毬_Lunasaymaybe = 月村手毬_BASE + 0
    月村手毬_一匹狼 = 月村手毬_BASE + 1
    月村手毬_Campusmode = 月村手毬_BASE + 2
    月村手毬_アイヴイ = 月村手毬_BASE + 3
    月村手毬_初声 = 月村手毬_BASE + 4
    月村手毬_学園生活 = 月村手毬_BASE + 5
    月村手毬_仮装狂騒曲 = 月村手毬_BASE + 6

    有村麻央_Fluorite = 有村麻央_BASE + 0
    有村麻央_はじまりはカッコよく = 有村麻央_BASE + 1
    有村麻央_Campusmode = 有村麻央_BASE + 2
    有村麻央_FeelJewelDream = 有村麻央_BASE + 3
    有村麻央_キミとセミブルー = 有村麻央_BASE + 4
    有村麻央_初恋 = 有村麻央_BASE + 5
    有村麻央_学園生活 = 有村麻央_BASE + 6

    篠泽广_コントラスト = 篠泽广_BASE + 0
    篠泽广_一番向いていないこと = 篠泽广_BASE + 1
    篠泽广_光景 = 篠泽广_BASE + 2
    篠泽广_Campusmode = 篠泽广_BASE + 3
    篠泽广_仮装狂騒曲 = 篠泽广_BASE + 4
    篠泽广_ハッピーミルフィーユ = 篠泽广_BASE + 5
    篠泽广_初恋 = 篠泽广_BASE + 6
    篠泽广_学園生活 = 篠泽广_BASE + 7

    紫云清夏_TameLieOneStep = 紫云清夏_BASE + 0
    紫云清夏_カクシタワタシ = 紫云清夏_BASE + 1
    紫云清夏_夢へのリスタート = 紫云清夏_BASE + 2
    紫云清夏_Campusmode = 紫云清夏_BASE + 3
    紫云清夏_キミとセミブルー = 紫云清夏_BASE + 4
    紫云清夏_初恋 = 紫云清夏_BASE + 5
    紫云清夏_学園生活 = 紫云清夏_BASE + 6

    花海佑芽_WhiteNightWhiteWish = 花海佑芽_BASE + 0
    花海佑芽_学園生活 = 花海佑芽_BASE + 1
    花海佑芽_Campusmode = 花海佑芽_BASE + 2
    花海佑芽_TheRollingRiceball = 花海佑芽_BASE + 3
    花海佑芽_アイドル_はじめっ = 花海佑芽_BASE + 4

    花海咲季_BoomBoomPow = 花海咲季_BASE + 0
    花海咲季_Campusmode = 花海咲季_BASE + 1
    花海咲季_FightingMyWay = 花海咲季_BASE + 2
    花海咲季_わたしが一番 = 花海咲季_BASE + 3
    花海咲季_冠菊 = 花海咲季_BASE + 4
    花海咲季_初声 = 花海咲季_BASE + 5
    花海咲季_古今東西ちょちょいのちょい = 花海咲季_BASE + 6
    花海咲季_学園生活 = 花海咲季_BASE + 7

    葛城リーリヤ_一つ踏み出した先に = 葛城リーリヤ_BASE + 0
    葛城リーリヤ_白線 = 葛城リーリヤ_BASE + 1
    葛城リーリヤ_Campusmode = 葛城リーリヤ_BASE + 2
    葛城リーリヤ_WhiteNightWhiteWish = 葛城リーリヤ_BASE + 3
    葛城リーリヤ_冠菊 = 葛城リーリヤ_BASE + 4
    葛城リーリヤ_初心 = 葛城リーリヤ_BASE + 5
    葛城リーリヤ_学園生活 = 葛城リーリヤ_BASE + 6

    藤田ことね_カワイイ_はじめました = 藤田ことね_BASE + 0
    藤田ことね_世界一可愛い私 = 藤田ことね_BASE + 1
    藤田ことね_Campusmode = 藤田ことね_BASE + 2
    藤田ことね_YellowBigBang = 藤田ことね_BASE + 3
    藤田ことね_WhiteNightWhiteWish =藤田ことね_BASE + 4
    藤田ことね_冠菊 = 藤田ことね_BASE + 5
    藤田ことね_初声 = 藤田ことね_BASE + 6
    藤田ことね_学園生活 = 藤田ことね_BASE + 7

__all__ = ["PIdol"] 