"""v2 → v3 迁移脚本

引入游戏解包数据后，`produce.idols` 不再使用 `PIdol` 枚举，而是直接使用
游戏内的 idol skin id (字符串)。这里负责完成枚举到字符串的转换。
"""

from __future__ import annotations

import logging
from typing import Any

from ._idol import PIdol

logger = logging.getLogger(__name__)


# 枚举 → skin_id 映射表（复制自旧实现）。
_PIDOL_TO_SKIN: dict[PIdol, str] = {
    PIdol.倉本千奈_Campusmode: "i_card-skin-kcna-3-007",
    PIdol.倉本千奈_WonderScale: "i_card-skin-kcna-3-000",
    PIdol.倉本千奈_ようこそ初星温泉: "i_card-skin-kcna-3-005",
    PIdol.倉本千奈_仮装狂騒曲: "i_card-skin-kcna-3-002",
    PIdol.倉本千奈_初心: "i_card-skin-kcna-1-001",
    PIdol.倉本千奈_学園生活: "i_card-skin-kcna-1-000",
    PIdol.倉本千奈_日々_発見的ステップ: "i_card-skin-kcna-3-001",
    PIdol.倉本千奈_胸を張って一歩ずつ: "i_card-skin-kcna-2-000",
    PIdol.十王星南_Campusmode: "i_card-skin-jsna-3-002",
    PIdol.十王星南_一番星: "i_card-skin-jsna-2-000",
    PIdol.十王星南_学園生活: "i_card-skin-jsna-1-000",
    PIdol.十王星南_小さな野望: "i_card-skin-jsna-3-000",
    PIdol.姫崎莉波_clumsytrick: "i_card-skin-hrnm-3-000",
    PIdol.姫崎莉波_私らしさのはじまり: "i_card-skin-hrnm-2-000",
    PIdol.姫崎莉波_キミとセミブルー: "i_card-skin-hrnm-3-001",
    PIdol.姫崎莉波_Campusmode: "i_card-skin-hrnm-3-007",
    PIdol.姫崎莉波_LUV: "i_card-skin-hrnm-3-002",
    PIdol.姫崎莉波_ようこそ初星温泉: "i_card-skin-hrnm-3-004",
    PIdol.姫崎莉波_ハッピーミルフィーユ: "i_card-skin-hrnm-3-008",
    PIdol.姫崎莉波_初心: "i_card-skin-hrnm-1-001",
    PIdol.姫崎莉波_学園生活: "i_card-skin-hrnm-1-000",
    PIdol.月村手毬_Lunasaymaybe: "i_card-skin-ttmr-3-000",
    PIdol.月村手毬_一匹狼: "i_card-skin-ttmr-2-000",
    PIdol.月村手毬_Campusmode: "i_card-skin-ttmr-3-007",
    PIdol.月村手毬_アイヴイ: "i_card-skin-ttmr-3-001",
    PIdol.月村手毬_初声: "i_card-skin-ttmr-1-001",
    PIdol.月村手毬_学園生活: "i_card-skin-ttmr-1-000",
    PIdol.月村手毬_仮装狂騒曲: "i_card-skin-ttmr-3-002",
    PIdol.有村麻央_Fluorite: "i_card-skin-amao-3-000",
    PIdol.有村麻央_はじまりはカッコよく: "i_card-skin-amao-2-000",
    PIdol.有村麻央_Campusmode: "i_card-skin-amao-3-007",
    PIdol.有村麻央_FeelJewelDream: "i_card-skin-amao-3-002",
    PIdol.有村麻央_キミとセミブルー: "i_card-skin-amao-3-001",
    PIdol.有村麻央_初恋: "i_card-skin-amao-1-001",
    PIdol.有村麻央_学園生活: "i_card-skin-amao-1-000",
    PIdol.篠泽广_コントラスト: "i_card-skin-shro-3-001",
    PIdol.篠泽广_一番向いていないこと: "i_card-skin-shro-2-000",
    PIdol.篠泽广_光景: "i_card-skin-shro-3-000",
    PIdol.篠泽广_Campusmode: "i_card-skin-shro-3-007",
    PIdol.篠泽广_仮装狂騒曲: "i_card-skin-shro-3-002",
    PIdol.篠泽广_ハッピーミルフィーユ: "i_card-skin-shro-3-008",
    PIdol.篠泽广_初恋: "i_card-skin-shro-1-001",
    PIdol.篠泽广_学園生活: "i_card-skin-shro-1-000",
    PIdol.紫云清夏_TameLieOneStep: "i_card-skin-ssmk-3-000",
    PIdol.紫云清夏_カクシタワタシ: "i_card-skin-ssmk-3-002",
    PIdol.紫云清夏_夢へのリスタート: "i_card-skin-ssmk-2-000",
    PIdol.紫云清夏_Campusmode: "i_card-skin-ssmk-3-007",
    PIdol.紫云清夏_キミとセミブルー: "i_card-skin-ssmk-3-001",
    PIdol.紫云清夏_初恋: "i_card-skin-ssmk-1-001",
    PIdol.紫云清夏_学園生活: "i_card-skin-ssmk-1-000",
    PIdol.花海佑芽_WhiteNightWhiteWish: "i_card-skin-hume-3-005",
    PIdol.花海佑芽_学園生活: "i_card-skin-hume-1-000",
    PIdol.花海佑芽_Campusmode: "i_card-skin-hume-3-006",
    PIdol.花海佑芽_TheRollingRiceball: "i_card-skin-hume-3-000",
    PIdol.花海佑芽_アイドル_はじめっ: "i_card-skin-hume-2-000",
    PIdol.花海咲季_BoomBoomPow: "i_card-skin-hski-3-001",
    PIdol.花海咲季_Campusmode: "i_card-skin-hski-3-008",
    PIdol.花海咲季_FightingMyWay: "i_card-skin-hski-3-000",
    PIdol.花海咲季_わたしが一番: "i_card-skin-hski-2-000",
    PIdol.花海咲季_冠菊: "i_card-skin-hski-3-001",
    PIdol.花海咲季_初声: "i_card-skin-hski-1-001",
    PIdol.花海咲季_古今東西ちょちょいのちょい: "i_card-skin-hski-3-006",
    PIdol.花海咲季_学園生活: "i_card-skin-hski-1-000",
    PIdol.葛城リーリヤ_一つ踏み出した先に: "i_card-skin-kllj-2-000",
    PIdol.葛城リーリヤ_白線: "i_card-skin-kllj-3-000",
    PIdol.葛城リーリヤ_Campusmode: "i_card-skin-kllj-3-006",
    PIdol.葛城リーリヤ_WhiteNightWhiteWish: "i_card-skin-kllj-3-005",
    PIdol.葛城リーリヤ_冠菊: "i_card-skin-kllj-3-001",
    PIdol.葛城リーリヤ_初心: "i_card-skin-kllj-1-001",
    PIdol.葛城リーリヤ_学園生活: "i_card-skin-kllj-1-000",
    PIdol.藤田ことね_カワイイ_はじめました: "i_card-skin-fktn-2-000",
    PIdol.藤田ことね_世界一可愛い私: "i_card-skin-fktn-3-000",
    PIdol.藤田ことね_Campusmode: "i_card-skin-fktn-3-007",
    PIdol.藤田ことね_YellowBigBang: "i_card-skin-fktn-3-001",
    PIdol.藤田ことね_WhiteNightWhiteWish: "i_card-skin-fktn-3-006",
    PIdol.藤田ことね_冠菊: "i_card-skin-fktn-3-002",
    PIdol.藤田ことね_初声: "i_card-skin-fktn-1-001",
    PIdol.藤田ことね_学園生活: "i_card-skin-fktn-1-000",
}


def migrate(user_config: dict[str, Any]) -> str | None:  # noqa: D401
    """执行 v2→v3 迁移。"""
    options = user_config.get("options")
    if options is None:
        logger.debug("No 'options' in user_config, skip v2→v3 migration.")
        return None

    produce_conf = options.get("produce", {})
    old_idols = produce_conf.get("idols", [])
    msg = ""

    new_idols: list[str] = []
    for idol in old_idols:
        if isinstance(idol, int):  # 原本已是 int(PIdol)
            try:
                skin = _PIDOL_TO_SKIN[PIdol(idol)]
                new_idols.append(skin)
            except (ValueError, KeyError):
                msg += f"未知 PIdol: {idol}\n"
        else:
            msg += f"旧 idol 数据格式异常: {idol}\n"

    produce_conf["idols"] = new_idols
    options["produce"] = produce_conf
    user_config["options"] = options

    return msg or None 