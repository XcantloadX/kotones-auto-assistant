"""v1 -> v2 迁移脚本

1. 将 PIdol 字符串列表转换为整数枚举值。
"""
from __future__ import annotations

import logging
from typing import Any

from ._idol import PIdol

logger = logging.getLogger(__name__)


def migrate(user_config: dict[str, Any]) -> str | None:  # noqa: D401
    """执行 v1→v2 迁移。

    参数 ``user_config`` 为单个用户配置 (dict)，本函数允许就地修改。
    返回提示信息 (str)；若无需提示可返回 ``None``。
    """
    options = user_config.get("options")
    if options is None:
        logger.debug("No 'options' in user_config, skip v1→v2 migration.")
        return None

    msg: str = ""

    # 将旧格式的 idol 描述 (list[str]) 映射到 PIdol 枚举
    def map_idol(idol: list[str]) -> PIdol | None:
        logger.debug("Converting idol spec: %s", idol)
        # 以下内容直接复制自旧实现
        match idol:
            case ["倉本千奈", "Campus mode!!"]:
                return PIdol.倉本千奈_Campusmode
            case ["倉本千奈", "Wonder Scale"]:
                return PIdol.倉本千奈_WonderScale
            case ["倉本千奈", "ようこそ初星温泉"]:
                return PIdol.倉本千奈_ようこそ初星温泉
            case ["倉本千奈", "仮装狂騒曲"]:
                return PIdol.倉本千奈_仮装狂騒曲
            case ["倉本千奈", "初心"]:
                return PIdol.倉本千奈_初心
            case ["倉本千奈", "学園生活"]:
                return PIdol.倉本千奈_学園生活
            case ["倉本千奈", "日々、発見的ステップ！"]:
                return PIdol.倉本千奈_日々_発見的ステップ
            case ["倉本千奈", "胸を張って一歩ずつ"]:
                return PIdol.倉本千奈_胸を張って一歩ずつ
            case ["十王星南", "Campus mode!!"]:
                return PIdol.十王星南_Campusmode
            case ["十王星南", "一番星"]:
                return PIdol.十王星南_一番星
            case ["十王星南", "学園生活"]:
                return PIdol.十王星南_学園生活
            case ["十王星南", "小さな野望"]:
                return PIdol.十王星南_小さな野望
            case ["姫崎莉波", "clumsy trick"]:
                return PIdol.姫崎莉波_clumsytrick
            case ["姫崎莉波", "『私らしさ』のはじまり"]:
                return PIdol.姫崎莉波_私らしさのはじまり
            case ["姫崎莉波", "キミとセミブルー"]:
                return PIdol.姫崎莉波_キミとセミブルー
            case ["姫崎莉波", "Campus mode!!"]:
                return PIdol.姫崎莉波_Campusmode
            case ["姫崎莉波", "L.U.V"]:
                return PIdol.姫崎莉波_LUV
            case ["姫崎莉波", "ようこそ初星温泉"]:
                return PIdol.姫崎莉波_ようこそ初星温泉
            case ["姫崎莉波", "ハッピーミルフィーユ"]:
                return PIdol.姫崎莉波_ハッピーミルフィーユ
            case ["姫崎莉波", "初心"]:
                return PIdol.姫崎莉波_初心
            case ["姫崎莉波", "学園生活"]:
                return PIdol.姫崎莉波_学園生活
            case ["月村手毬", "Luna say maybe"]:
                return PIdol.月村手毬_Lunasaymaybe
            case ["月村手毬", "一匹狼"]:
                return PIdol.月村手毬_一匹狼
            case ["月村手毬", "Campus mode!!"]:
                return PIdol.月村手毬_Campusmode
            case ["月村手毬", "アイヴイ"]:
                return PIdol.月村手毬_アイヴイ
            case ["月村手毬", "初声"]:
                return PIdol.月村手毬_初声
            case ["月村手毬", "学園生活"]:
                return PIdol.月村手毬_学園生活
            case ["月村手毬", "仮装狂騒曲"]:
                return PIdol.月村手毬_仮装狂騒曲
            case ["有村麻央", "Fluorite"]:
                return PIdol.有村麻央_Fluorite
            case ["有村麻央", "はじまりはカッコよく"]:
                return PIdol.有村麻央_はじまりはカッコよく
            case ["有村麻央", "Campus mode!!"]:
                return PIdol.有村麻央_Campusmode
            case ["有村麻央", "Feel Jewel Dream"]:
                return PIdol.有村麻央_FeelJewelDream
            case ["有村麻央", "キミとセミブルー"]:
                return PIdol.有村麻央_キミとセミブルー
            case ["有村麻央", "初恋"]:
                return PIdol.有村麻央_初恋
            case ["有村麻央", "学園生活"]:
                return PIdol.有村麻央_学園生活
            case ["篠泽广", "コントラスト"]:
                return PIdol.篠泽广_コントラスト
            case ["篠泽广", "一番向いていないこと"]:
                return PIdol.篠泽广_一番向いていないこと
            case ["篠泽广", "光景"]:
                return PIdol.篠泽广_光景
            case ["篠泽广", "Campus mode!!"]:
                return PIdol.篠泽广_Campusmode
            case ["篠泽广", "仮装狂騒曲"]:
                return PIdol.篠泽广_仮装狂騒曲
            case ["篠泽广", "ハッピーミルフィーユ"]:
                return PIdol.篠泽广_ハッピーミルフィーユ
            case ["篠泽广", "初恋"]:
                return PIdol.篠泽广_初恋
            case ["篠泽广", "学園生活"]:
                return PIdol.篠泽广_学園生活
            case ["紫云清夏", "Tame Lie One Step"]:
                return PIdol.紫云清夏_TameLieOneStep
            case ["紫云清夏", "カクシタワタシ"]:
                return PIdol.紫云清夏_カクシタワタシ
            case ["紫云清夏", "夢へのリスタート"]:
                return PIdol.紫云清夏_夢へのリスタート
            case ["紫云清夏", "Campus mode!!"]:
                return PIdol.紫云清夏_Campusmode
            case ["紫云清夏", "キミとセミブルー"]:
                return PIdol.紫云清夏_キミとセミブルー
            case ["紫云清夏", "初恋"]:
                return PIdol.紫云清夏_初恋
            case ["紫云清夏", "学園生活"]:
                return PIdol.紫云清夏_学園生活
            case ["花海佑芽", "White Night! White Wish!"]:
                return PIdol.花海佑芽_WhiteNightWhiteWish
            case ["花海佑芽", "学園生活"]:
                return PIdol.花海佑芽_学園生活
            case ["花海佑芽", "Campus mode!!"]:
                return PIdol.花海佑芽_Campusmode
            case ["花海佑芽", "The Rolling Riceball"]:
                return PIdol.花海佑芽_TheRollingRiceball
            case ["花海佑芽", "アイドル、はじめっ！"]:
                return PIdol.花海佑芽_アイドル_はじめっ
            case ["花海咲季", "Boom Boom Pow"]:
                return PIdol.花海咲季_BoomBoomPow
            case ["花海咲季", "Campus mode!!"]:
                return PIdol.花海咲季_Campusmode
            case ["花海咲季", "Fighting My Way"]:
                return PIdol.花海咲季_FightingMyWay
            case ["花海咲季", "わたしが一番！"]:
                return PIdol.花海咲季_わたしが一番
            case ["花海咲季", "冠菊"]:
                return PIdol.花海咲季_冠菊
            case ["花海咲季", "初声"]:
                return PIdol.花海咲季_初声
            case ["花海咲季", "古今東西ちょちょいのちょい"]:
                return PIdol.花海咲季_古今東西ちょちょいのちょい
            case ["花海咲季", "学園生活"]:
                return PIdol.花海咲季_学園生活
            case ["葛城リーリヤ", "一つ踏み出した先に"]:
                return PIdol.葛城リーリヤ_一つ踏み出した先に
            case ["葛城リーリヤ", "白線"]:
                return PIdol.葛城リーリヤ_白線
            case ["葛城リーリヤ", "Campus mode!!"]:
                return PIdol.葛城リーリヤ_Campusmode
            case ["葛城リーリヤ", "White Night! White Wish!"]:
                return PIdol.葛城リーリヤ_WhiteNightWhiteWish
            case ["葛城リーリヤ", "冠菊"]:
                return PIdol.葛城リーリヤ_冠菊
            case ["葛城リーリヤ", "初心"]:
                return PIdol.葛城リーリヤ_初心
            case ["葛城リーリヤ", "学園生活"]:
                return PIdol.葛城リーリヤ_学園生活
            case ["藤田ことね", "カワイイ", "はじめました"]:
                return PIdol.藤田ことね_カワイイ_はじめました
            case ["藤田ことね", "世界一可愛い私"]:
                return PIdol.藤田ことね_世界一可愛い私
            case ["藤田ことね", "Campus mode!!"]:
                return PIdol.藤田ことね_Campusmode
            case ["藤田ことね", "Yellow Big Bang！"]:
                return PIdol.藤田ことね_YellowBigBang
            case ["藤田ことね", "White Night! White Wish!"]:
                return PIdol.藤田ことね_WhiteNightWhiteWish
            case ["藤田ことね", "冠菊"]:
                return PIdol.藤田ことね_冠菊
            case ["藤田ことね", "初声"]:
                return PIdol.藤田ことね_初声
            case ["藤田ことね", "学園生活"]:
                return PIdol.藤田ことね_学園生活
            case _:
                nonlocal msg
                if msg == "":
                    msg = "培育设置中的以下偶像升级失败。请尝试手动添加。\n"
                msg += f"{idol} 未找到\n"
                return None

    produce_conf = options.get("produce", {})
    old_idols = produce_conf.get("idols", [])
    new_idols = list(filter(lambda x: x is not None, map(map_idol, old_idols)))
    produce_conf["idols"] = new_idols
    options["produce"] = produce_conf
    user_config["options"] = options

    return msg or None 