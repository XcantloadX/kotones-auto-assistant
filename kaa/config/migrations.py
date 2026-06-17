# ruff: noqa: E701
"""配置迁移步骤。

每个 MigrationStep 子类对应一次 schema 版本升级。
所有步骤操作 conf/config.json（单文件多 user_config 格式）。
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

from .migration import MigrationChain, MigrationContext, MigrationMessage, MigrationStep, add_deferred_messages

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _read_config(config_dir: Path) -> tuple[Path, dict] | tuple[None, None]:  # noqa: E501
    """读取 conf/config.json，若不存在返回 (None, None)。"""
    path = config_dir / 'config.json'
    if not path.exists():
        return None, None
    return path, json.loads(path.read_text(encoding='utf-8'))


def _write_config(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding='utf-8')


# ---------------------------------------------------------------------------
# V1 → V2：PIdol 字符串列表 → 整数枚举
# ---------------------------------------------------------------------------

class ProfileV1ToV2(MigrationStep):
    """将 produce.idols 从字符串列表转换为 PIdol 整数枚举。"""

    def check_needed(self, ctx: MigrationContext) -> bool:
        _, data = _read_config(ctx.config_dir)
        return data is not None and data.get('version', 1) < 2

    def apply(self, ctx: MigrationContext) -> None:
        from ._idol import PIdol  # noqa: PLC0415

        def map_idol(idol: list[str]) -> PIdol | None:
            match idol:
                case ["倉本千奈", "Campus mode!!"]: return PIdol.倉本千奈_Campusmode
                case ["倉本千奈", "Wonder Scale"]: return PIdol.倉本千奈_WonderScale
                case ["倉本千奈", "ようこそ初星温泉"]: return PIdol.倉本千奈_ようこそ初星温泉
                case ["倉本千奈", "仮装狂騒曲"]: return PIdol.倉本千奈_仮装狂騒曲
                case ["倉本千奈", "初心"]: return PIdol.倉本千奈_初心
                case ["倉本千奈", "学園生活"]: return PIdol.倉本千奈_学園生活
                case ["倉本千奈", "日々、発見的ステップ！"]: return PIdol.倉本千奈_日々_発見的ステップ
                case ["倉本千奈", "胸を張って一歩ずつ"]: return PIdol.倉本千奈_胸を張って一歩ずつ
                case ["十王星南", "Campus mode!!"]: return PIdol.十王星南_Campusmode
                case ["十王星南", "一番星"]: return PIdol.十王星南_一番星
                case ["十王星南", "学園生活"]: return PIdol.十王星南_学園生活
                case ["十王星南", "小さな野望"]: return PIdol.十王星南_小さな野望
                case ["姫崎莉波", "clumsy trick"]: return PIdol.姫崎莉波_clumsytrick
                case ["姫崎莉波", "『私らしさ』のはじまり"]: return PIdol.姫崎莉波_私らしさのはじまり
                case ["姫崎莉波", "キミとセミブルー"]: return PIdol.姫崎莉波_キミとセミブルー
                case ["姫崎莉波", "Campus mode!!"]: return PIdol.姫崎莉波_Campusmode
                case ["姫崎莉波", "L.U.V"]: return PIdol.姫崎莉波_LUV
                case ["姫崎莉波", "ようこそ初星温泉"]: return PIdol.姫崎莉波_ようこそ初星温泉
                case ["姫崎莉波", "ハッピーミルフィーユ"]: return PIdol.姫崎莉波_ハッピーミルフィーユ
                case ["姫崎莉波", "初心"]: return PIdol.姫崎莉波_初心
                case ["姫崎莉波", "学園生活"]: return PIdol.姫崎莉波_学園生活
                case ["月村手毬", "Luna say maybe"]: return PIdol.月村手毬_Lunasaymaybe
                case ["月村手毬", "一匹狼"]: return PIdol.月村手毬_一匹狼
                case ["月村手毬", "Campus mode!!"]: return PIdol.月村手毬_Campusmode
                case ["月村手毬", "アイヴイ"]: return PIdol.月村手毬_アイヴイ
                case ["月村手毬", "初声"]: return PIdol.月村手毬_初声
                case ["月村手毬", "学園生活"]: return PIdol.月村手毬_学園生活
                case ["月村手毬", "仮装狂騒曲"]: return PIdol.月村手毬_仮装狂騒曲
                case ["有村麻央", "Fluorite"]: return PIdol.有村麻央_Fluorite
                case ["有村麻央", "はじまりはカッコよく"]: return PIdol.有村麻央_はじまりはカッコよく
                case ["有村麻央", "Campus mode!!"]: return PIdol.有村麻央_Campusmode
                case ["有村麻央", "Feel Jewel Dream"]: return PIdol.有村麻央_FeelJewelDream
                case ["有村麻央", "キミとセミブルー"]: return PIdol.有村麻央_キミとセミブルー
                case ["有村麻央", "初恋"]: return PIdol.有村麻央_初恋
                case ["有村麻央", "学園生活"]: return PIdol.有村麻央_学園生活
                case ["篠泽广", "コントラスト"]: return PIdol.篠泽广_コントラスト
                case ["篠泽广", "一番向いていないこと"]: return PIdol.篠泽广_一番向いていないこと
                case ["篠泽广", "光景"]: return PIdol.篠泽广_光景
                case ["篠泽广", "Campus mode!!"]: return PIdol.篠泽广_Campusmode
                case ["篠泽广", "仮装狂騒曲"]: return PIdol.篠泽广_仮装狂騒曲
                case ["篠泽广", "ハッピーミルフィーユ"]: return PIdol.篠泽广_ハッピーミルフィーユ
                case ["篠泽广", "初恋"]: return PIdol.篠泽广_初恋
                case ["篠泽广", "学園生活"]: return PIdol.篠泽广_学園生活
                case ["紫云清夏", "Tame Lie One Step"]: return PIdol.紫云清夏_TameLieOneStep
                case ["紫云清夏", "カクシタワタシ"]: return PIdol.紫云清夏_カクシタワタシ
                case ["紫云清夏", "夢へのリスタート"]: return PIdol.紫云清夏_夢へのリスタート
                case ["紫云清夏", "Campus mode!!"]: return PIdol.紫云清夏_Campusmode
                case ["紫云清夏", "キミとセミブルー"]: return PIdol.紫云清夏_キミとセミブルー
                case ["紫云清夏", "初恋"]: return PIdol.紫云清夏_初恋
                case ["紫云清夏", "学園生活"]: return PIdol.紫云清夏_学園生活
                case ["花海佑芽", "White Night! White Wish!"]: return PIdol.花海佑芽_WhiteNightWhiteWish
                case ["花海佑芽", "学園生活"]: return PIdol.花海佑芽_学園生活
                case ["花海佑芽", "Campus mode!!"]: return PIdol.花海佑芽_Campusmode
                case ["花海佑芽", "The Rolling Riceball"]: return PIdol.花海佑芽_TheRollingRiceball
                case ["花海佑芽", "アイドル、はじめっ！"]: return PIdol.花海佑芽_アイドル_はじめっ
                case ["花海咲季", "Boom Boom Pow"]: return PIdol.花海咲季_BoomBoomPow
                case ["花海咲季", "Campus mode!!"]: return PIdol.花海咲季_Campusmode
                case ["花海咲季", "Fighting My Way"]: return PIdol.花海咲季_FightingMyWay
                case ["花海咲季", "わたしが一番！"]: return PIdol.花海咲季_わたしが一番
                case ["花海咲季", "冠菊"]: return PIdol.花海咲季_冠菊
                case ["花海咲季", "初声"]: return PIdol.花海咲季_初声
                case ["花海咲季", "古今東西ちょちょいのちょい"]: return PIdol.花海咲季_古今東西ちょちょいのちょい
                case ["花海咲季", "学園生活"]: return PIdol.花海咲季_学園生活
                case ["葛城リーリヤ", "一つ踏み出した先に"]: return PIdol.葛城リーリヤ_一つ踏み出した先に
                case ["葛城リーリヤ", "白線"]: return PIdol.葛城リーリヤ_白線
                case ["葛城リーリヤ", "Campus mode!!"]: return PIdol.葛城リーリヤ_Campusmode
                case ["葛城リーリヤ", "White Night! White Wish!"]: return PIdol.葛城リーリヤ_WhiteNightWhiteWish
                case ["葛城リーリヤ", "冠菊"]: return PIdol.葛城リーリヤ_冠菊
                case ["葛城リーリヤ", "初心"]: return PIdol.葛城リーリヤ_初心
                case ["葛城リーリヤ", "学園生活"]: return PIdol.葛城リーリヤ_学園生活
                case ["藤田ことね", "カワイイ", "はじめました"]: return PIdol.藤田ことね_カワイイ_はじめました
                case ["藤田ことね", "世界一可愛い私"]: return PIdol.藤田ことね_世界一可愛い私
                case ["藤田ことね", "Campus mode!!"]: return PIdol.藤田ことね_Campusmode
                case ["藤田ことね", "Yellow Big Bang！"]: return PIdol.藤田ことね_YellowBigBang
                case ["藤田ことね", "White Night! White Wish!"]: return PIdol.藤田ことね_WhiteNightWhiteWish
                case ["藤田ことね", "冠菊"]: return PIdol.藤田ことね_冠菊
                case ["藤田ことね", "初声"]: return PIdol.藤田ことね_初声
                case ["藤田ことね", "学園生活"]: return PIdol.藤田ことね_学園生活
                case _: return None

        path, data = _read_config(ctx.config_dir)
        if data is None or path is None or data.get('version', 1) >= 2:
            return

        failed_idols: list[str] = []
        for user_cfg in data.get('user_configs', []):
            try:
                options = user_cfg.get('options') or {}
                produce_conf = options.get('produce', {})
                old_idols = produce_conf.get('idols', [])
                new_idols = []
                for idol in old_idols:
                    result = map_idol(idol)
                    if result is not None:
                        new_idols.append(result)
                    else:
                        failed_idols.append(str(idol))
                produce_conf['idols'] = new_idols
                options['produce'] = produce_conf
                user_cfg['options'] = options
            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {user_cfg.get('name', '?')} 时出错: {e}",
                    level='warning',
                ))
                logger.exception("Error in V1→V2 for user_config %s", user_cfg.get('name'))

        data['version'] = 2
        _write_config(path, data)

        if failed_idols:
            ctx.messages.append(MigrationMessage(
                text="培育设置中的以下偶像升级失败，请尝试手动添加：\n" + "\n".join(failed_idols),
                level='warning',
                old_version='v1',
                new_version='v2',
            ))
        else:
            ctx.messages.append(MigrationMessage(
                text="培育偶像配置已升级",
                old_version='v1',
                new_version='v2',
            ))


# ---------------------------------------------------------------------------
# V2 → V3：PIdol 枚举整数 → skin_id 字符串
# ---------------------------------------------------------------------------

class ProfileV2ToV3(MigrationStep):
    """将 produce.idols 从 PIdol 整数枚举转换为 skin_id 字符串。"""

    def check_needed(self, ctx: MigrationContext) -> bool:
        _, data = _read_config(ctx.config_dir)
        return data is not None and data.get('version', 1) < 3

    def apply(self, ctx: MigrationContext) -> None:
        from ._idol import PIdol  # noqa: PLC0415

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

        path, data = _read_config(ctx.config_dir)
        if data is None or path is None or data.get('version', 1) >= 3:
            return

        warnings: list[str] = []
        for user_cfg in data.get('user_configs', []):
            try:
                options = user_cfg.get('options') or {}
                produce_conf = options.get('produce', {})
                old_idols = produce_conf.get('idols', [])
                new_idols: list[str] = []
                for idol in old_idols:
                    if isinstance(idol, int):
                        try:
                            new_idols.append(_PIDOL_TO_SKIN[PIdol(idol)])
                        except (ValueError, KeyError):
                            warnings.append(f"未知 PIdol: {idol}")
                    else:
                        warnings.append(f"旧 idol 数据格式异常: {idol}")
                produce_conf['idols'] = new_idols
                options['produce'] = produce_conf
                user_cfg['options'] = options
            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {user_cfg.get('name', '?')} 时出错: {e}",
                    level='warning',
                ))
                logger.exception("Error in V2→V3 for user_config %s", user_cfg.get('name'))

        data['version'] = 3
        _write_config(path, data)

        if warnings:
            ctx.messages.append(MigrationMessage(
                text="部分偶像 skin_id 迁移失败：\n" + "\n".join(warnings),
                level='warning',
                old_version='v2',
                new_version='v3',
            ))
        else:
            ctx.messages.append(MigrationMessage(
                text="培育偶像 skin_id 迁移完成",
                old_version='v2',
                new_version='v3',
            ))


# ---------------------------------------------------------------------------
# V3 → V4：修正错误的游戏包名
# ---------------------------------------------------------------------------

class ProfileV3ToV4(MigrationStep):
    """修正错误的游戏包名 com.bandinamcoent → com.bandainamcoent。"""

    def check_needed(self, ctx: MigrationContext) -> bool:
        _, data = _read_config(ctx.config_dir)
        return data is not None and data.get('version', 1) < 4

    def apply(self, ctx: MigrationContext) -> None:
        path, data = _read_config(ctx.config_dir)
        if data is None or path is None or data.get('version', 1) >= 4:
            return

        for user_cfg in data.get('user_configs', []):
            try:
                options = user_cfg.get('options') or {}
                start_conf = options.get('start_game', {})
                if start_conf.get('game_package_name') == 'com.bandinamcoent.idolmaster_gakuen':
                    start_conf['game_package_name'] = 'com.bandainamcoent.idolmaster_gakuen'
                    options['start_game'] = start_conf
                    user_cfg['options'] = options
                    logger.info("Corrected game package name in %s", user_cfg.get('name'))
            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {user_cfg.get('name', '?')} 时出错: {e}",
                    level='warning',
                ))
                logger.exception("Error in V3→V4 for user_config %s", user_cfg.get('name'))

        data['version'] = 4
        _write_config(path, data)


# ---------------------------------------------------------------------------
# V4 → V5：Windows 截图方式对应 backend.type = 'dmm'
# ---------------------------------------------------------------------------

class ProfileV4ToV5(MigrationStep):
    """当截图方式为 windows/remote_windows 时，将 backend.type 设为 'dmm'。"""

    def check_needed(self, ctx: MigrationContext) -> bool:
        _, data = _read_config(ctx.config_dir)
        return data is not None and data.get('version', 1) < 5

    def apply(self, ctx: MigrationContext) -> None:
        path, data = _read_config(ctx.config_dir)
        if data is None or path is None or data.get('version', 1) >= 5:
            return

        for user_cfg in data.get('user_configs', []):
            try:
                backend = user_cfg.get('backend', {})
                if backend.get('screenshot_impl') in {'windows', 'remote_windows'}:
                    backend['type'] = 'dmm'
                    user_cfg['backend'] = backend
                    logger.info("Set backend type to dmm for %s", user_cfg.get('name'))
            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {user_cfg.get('name', '?')} 时出错: {e}",
                    level='warning',
                ))
                logger.exception("Error in V4→V5 for user_config %s", user_cfg.get('name'))

        data['version'] = 5
        _write_config(path, data)


# ---------------------------------------------------------------------------
# V5 → V6：重构培育配置为 ProduceSolution 结构
# ---------------------------------------------------------------------------

def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', name)


class ProfileV5ToV6(MigrationStep):
    """将 ProduceConfig 中的培育参数迁移到 ProduceSolution 独立文件。"""

    def check_needed(self, ctx: MigrationContext) -> bool:
        _, data = _read_config(ctx.config_dir)
        return data is not None and data.get('version', 1) < 6

    def apply(self, ctx: MigrationContext) -> None:
        path, data = _read_config(ctx.config_dir)
        if data is None or path is None or data.get('version', 1) >= 6:
            return

        solutions_dir = ctx.config_dir / 'produce'
        solutions_dir.mkdir(parents=True, exist_ok=True)

        migrated: list[str] = []
        for user_cfg in data.get('user_configs', []):
            try:
                options = user_cfg.get('options') or {}
                produce_conf = options.get('produce', {})
                if not produce_conf or 'selected_solution_id' in produce_conf:
                    continue

                solution_id = uuid.uuid4().hex
                produce_data: dict[str, Any] = {
                    'mode': produce_conf.get('mode', 'regular'),
                    'idol': (produce_conf.get('idols') or [None])[0],
                    'memory_set': (produce_conf.get('memory_sets') or [None])[0],
                    'support_card_set': (produce_conf.get('support_card_sets') or [None])[0],
                    'auto_set_memory': produce_conf.get('auto_set_memory', False),
                    'auto_set_support_card': produce_conf.get('auto_set_support_card', False),
                    'use_pt_boost': produce_conf.get('use_pt_boost', False),
                    'use_note_boost': produce_conf.get('use_note_boost', False),
                    'follow_producer': produce_conf.get('follow_producer', False),
                    'self_study_lesson': produce_conf.get('self_study_lesson', 'dance'),
                    'prefer_lesson_ap': produce_conf.get('prefer_lesson_ap', False),
                    'actions_order': produce_conf.get('actions_order', [
                        'recommended', 'visual', 'vocal', 'dance',
                        'allowance', 'outing', 'study', 'consult', 'rest',
                    ]),
                    'recommend_card_detection_mode': produce_conf.get('recommend_card_detection_mode', 'normal'),
                    'use_ap_drink': produce_conf.get('use_ap_drink', False),
                    'skip_commu': produce_conf.get('skip_commu', True),
                }
                solution = {
                    'type': 'produce_solution',
                    'id': solution_id,
                    'name': '默认方案',
                    'description': '从旧配置迁移的默认培育方案',
                    'data': produce_data,
                }
                safe_name = _sanitize_filename(solution['name'])
                solution_path = solutions_dir / f'{safe_name}.json'
                solution_path.write_text(
                    json.dumps(solution, ensure_ascii=False, indent=4),
                    encoding='utf-8',
                )

                options['produce'] = {
                    'enabled': produce_conf.get('enabled', False),
                    'selected_solution_id': solution_id,
                    'produce_count': produce_conf.get('produce_count', 1),
                }
                user_cfg['options'] = options
                migrated.append(user_cfg.get('name', '?'))

            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {user_cfg.get('name', '?')} 培育方案时出错: {e}",
                    level='warning',
                ))
                logger.exception("Error in V5→V6 for user_config %s", user_cfg.get('name'))

        data['version'] = 6
        _write_config(path, data)

        if migrated:
            ctx.messages.append(MigrationMessage(
                text=f"已将以下配置的培育参数迁移到方案系统：{', '.join(migrated)}",
                old_version='v5',
                new_version='v6',
            ))


# ---------------------------------------------------------------------------
# V6 → V7：adb_raw 截图方式升级为 adb
# ---------------------------------------------------------------------------

class ProfileV6ToV7(MigrationStep):
    """将已废弃的 adb_raw 截图方式替换为 adb。"""

    def check_needed(self, ctx: MigrationContext) -> bool:
        _, data = _read_config(ctx.config_dir)
        return data is not None and data.get('version', 1) < 7

    def apply(self, ctx: MigrationContext) -> None:
        path, data = _read_config(ctx.config_dir)
        if data is None or path is None or data.get('version', 1) >= 7:
            return

        upgraded: list[str] = []
        for user_cfg in data.get('user_configs', []):
            try:
                backend = user_cfg.get('backend')
                if isinstance(backend, dict) and backend.get('screenshot_impl') == 'adb_raw':
                    backend['screenshot_impl'] = 'adb'
                    user_cfg['backend'] = backend
                    upgraded.append(user_cfg.get('name', '?'))
            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {user_cfg.get('name', '?')} 时出错: {e}",
                    level='warning',
                ))
                logger.exception("Error in V6→V7 for user_config %s", user_cfg.get('name'))

        data['version'] = 7
        _write_config(path, data)

        if upgraded:
            ctx.messages.append(MigrationMessage(
                text=f"已将以下配置的 adb_raw 截图方式升级为 adb：{', '.join(upgraded)}",
                old_version='v6',
                new_version='v7',
            ))


# ---------------------------------------------------------------------------
# V7 → V8：单文件 config.json 拆分为多文件格式
# ---------------------------------------------------------------------------

class ProfileV7ToV8(MigrationStep):
    """将旧的单文件 config.json 拆分为多个 {name}.json + _shared.json。

    同时处理两种旧路径：./config.json（根目录）和 conf/config.json。
    """

    def _find_legacy_path(self, ctx: MigrationContext) -> Path | None:
        conf_path = ctx.config_dir / 'config.json'
        if conf_path.exists():
            return conf_path
        root_path = ctx.config_dir.parent / 'config.json'
        if root_path.exists():
            return root_path
        return None

    def check_needed(self, ctx: MigrationContext) -> bool:
        return self._find_legacy_path(ctx) is not None

    def apply(self, ctx: MigrationContext) -> None:
        path = self._find_legacy_path(ctx)
        assert path is not None
        ctx.config_dir.mkdir(parents=True, exist_ok=True)
        profiles_dir = ctx.config_dir / 'profiles'
        profiles_dir.mkdir(parents=True, exist_ok=True)
        data = json.loads(path.read_text(encoding='utf-8'))
        user_configs: list[dict] = data.get('user_configs', [])

        # 从第一个 user_config 提取 misc → _shared.misc
        misc_data: dict = {}
        if user_configs:
            misc_data = (user_configs[0].get('options') or {}).get('misc', {})

        shared_file = ctx.config_dir / '_shared.json'
        if not shared_file.exists():
            shared_data = {
                'version': 1,
                'profiles': {'last_used': None, 'open_tabs': []},
                'misc': misc_data,
            }
            shared_file.write_text(
                json.dumps(shared_data, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )

        # 逐个写出 profile 文件到 conf/profiles/
        name_counts: dict[str, int] = {}
        for user_cfg in user_configs:
            raw_name: str = user_cfg.get('name', 'default')
            safe_name = re.sub(r'[\\/:*?"<>|]', '_', raw_name)

            # 处理同名冲突
            if safe_name in name_counts:
                name_counts[safe_name] += 1
                safe_name = f'{safe_name}_{name_counts[safe_name]}'
            else:
                name_counts[safe_name] = 0

            options: dict = dict(user_cfg.get('options') or {})
            options.pop('misc', None)  # misc 已移入 _shared

            profile_data: dict = {
                'version': 8,
                'name': raw_name,
                'description': user_cfg.get('description', ''),
                'backend': user_cfg.get('backend', {}),
                'keep_screenshots': user_cfg.get('keep_screenshots', False),
                **options,
            }

            profile_file = profiles_dir / f'{safe_name}.json'
            if not profile_file.exists():
                profile_file.write_text(
                    json.dumps(profile_data, indent=2, ensure_ascii=False),
                    encoding='utf-8',
                )

        # 将原文件重命名为 .bak
        path.rename(ctx.config_dir / 'config.json.bak')

        ctx.messages.append(MigrationMessage(
            text=f"配置已迁移为多文件格式，共迁移 {len(user_configs)} 个 profile",
            old_version='v2026.05b1 (v7)',
            new_version='v2025.06b1 (v8)',
        ))
        logger.info("Migrated %d user_config(s) to multi-file format.", len(user_configs))


# ---------------------------------------------------------------------------
# Shared V1 → V2：conf/telemetry 文件迁移到 _shared.json
# ---------------------------------------------------------------------------

class SharedV1ToV2(MigrationStep):
    """将 conf/telemetry 文件的值迁移到 _shared.json 的 telemetry.sentry 字段。"""

    def check_needed(self, ctx: MigrationContext) -> bool:
        return (ctx.config_dir / 'telemetry').exists()

    def apply(self, ctx: MigrationContext) -> None:
        telemetry_file = ctx.config_dir / 'telemetry'
        enabled = telemetry_file.read_text(encoding='utf-8').strip() != '0'

        shared_file = ctx.config_dir / '_shared.json'
        data = json.loads(shared_file.read_text(encoding='utf-8')) if shared_file.exists() else {}
        data.setdefault('telemetry', {})['sentry'] = enabled
        shared_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

        telemetry_file.unlink()
        ctx.messages.append(MigrationMessage(
            text="已将匿名错误报告设置迁移到 _shared.json。",
            old_version='v2026.06b1',
            new_version='v2025.06b2',
        ))


# ---------------------------------------------------------------------------
# V8 → V9：backend 平铺字段 → lifecycle/connection 嵌套；任务配置收拢到 tasks
# ---------------------------------------------------------------------------

_TASK_KEYS = [
    'purchase', 'activity_funds', 'presents', 'assignment',
    'contest', 'produce', 'mission_reward', 'club_reward',
    'upgrade_support_card', 'capsule_toys', 'start_game', 'end_game',
]


class ProfileV8ToV9(MigrationStep):
    """
    1. backend 从平铺字段迁移到 lifecycle + connection 嵌套结构（check_emulator → check_and_start）。
    2. 所有任务配置字段收拢到 tasks 键下。
    """

    def check_needed(self, ctx: MigrationContext) -> bool:
        profiles_dir = ctx.config_dir / 'profiles'
        if not profiles_dir.exists():
            return False
        for f in profiles_dir.glob('*.json'):
            data = json.loads(f.read_text(encoding='utf-8'))
            if data.get('version', 0) < 9:
                return True
        return False

    def apply(self, ctx: MigrationContext) -> None:
        profiles_dir = ctx.config_dir / 'profiles'
        if not profiles_dir.exists():
            return
        migrated: list[str] = []
        for f in profiles_dir.glob('*.json'):
            data = json.loads(f.read_text(encoding='utf-8'))
            if data.get('version', 0) >= 9:
                continue

            # ── 1. 迁移 backend ──────────────────────────────────────────────
            backend = data.get('backend', {})
            if 'type' in backend:
                old_type = backend.get('type', 'custom')
                instance_id = backend.get('instance_id')
                adb_ip = backend.get('adb_ip', '127.0.0.1')
                adb_port = backend.get('adb_port', 5555)
                check_emulator = backend.get('check_emulator', False)
                emulator_path = backend.get('emulator_path')
                emulator_args = backend.get('emulator_args', '')
                adb_emulator_name = backend.get('adb_emulator_name')
                mumu_background_mode = backend.get('mumu_background_mode', False)
                cursor_wait_speed = backend.get('cursor_wait_speed', -1)
                windows_window_title = backend.get('windows_window_title', 'gakumas')
                windows_ahk_path = backend.get('windows_ahk_path')
                screenshot_impl = backend.get('screenshot_impl', 'adb')
                target_screenshot_interval = backend.get('target_screenshot_interval')

                if old_type in ('mumu12', 'mumu12v5'):
                    lifecycle: dict = {
                        'type': old_type,
                        'instance_id': instance_id,
                        'mumu_background_mode': mumu_background_mode,
                        'check_and_start': check_emulator,
                    }
                    connection: dict = {'type': 'auto'}
                elif old_type == 'leidian':
                    lifecycle = {
                        'type': 'leidian',
                        'instance_id': instance_id,
                        'adb_emulator_name': adb_emulator_name,
                        'check_and_start': check_emulator,
                    }
                    connection = {'type': 'tcp', 'ip': adb_ip, 'port': adb_port}
                elif old_type == 'dmm':
                    lifecycle = {
                        'type': 'dmm',
                        'check_and_start': check_emulator,
                        'emulator_path': emulator_path,
                        'emulator_args': emulator_args,
                        'cursor_wait_speed': cursor_wait_speed,
                        'windows_window_title': windows_window_title,
                        'windows_ahk_path': windows_ahk_path,
                    }
                    connection = {'type': 'tcp', 'ip': adb_ip, 'port': adb_port}
                elif old_type == 'playcover':
                    lifecycle = {'type': 'playcover'}
                    connection = {'type': 'tcp', 'ip': adb_ip, 'port': adb_port}
                else:  # custom
                    lifecycle = {
                        'type': 'custom',
                        'check_and_start': check_emulator,
                        'emulator_path': emulator_path,
                        'emulator_args': emulator_args,
                    }
                    connection = {'type': 'tcp', 'ip': adb_ip, 'port': adb_port}

                data['backend'] = {
                    'lifecycle': lifecycle,
                    'connection': connection,
                    'screenshot_impl': screenshot_impl,
                    'target_screenshot_interval': target_screenshot_interval,
                }

            # ── 2. 迁移 tasks ────────────────────────────────────────────────
            tasks: dict = data.get('tasks', {})
            for key in _TASK_KEYS:
                if key in data:
                    tasks[key] = data.pop(key)
            if tasks:
                data['tasks'] = tasks

            data['version'] = 9
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            migrated.append(f.stem)

        if migrated:
            ctx.messages.append(MigrationMessage(
                text="设备设置与任务设置规范化",
                old_version='v2026.06b1',
                new_version='v2026.06b2',
            ))


# ---------------------------------------------------------------------------
# V9 → V10：DMM 截图方式 windows → windows_native
# ---------------------------------------------------------------------------

class ProfileV9ToV10(MigrationStep):
    """将 backend.screenshot_impl 为 'windows'（依赖 AHK 的旧实现）的 profile

    自动切换到不依赖 AHK 的新实现 'windows_native'。
    """

    def check_needed(self, ctx: MigrationContext) -> bool:
        profiles_dir = ctx.config_dir / 'profiles'
        if not profiles_dir.exists():
            return False
        for f in profiles_dir.glob('*.json'):
            data = json.loads(f.read_text(encoding='utf-8'))
            if data.get('version', 0) < 10:
                return True
        return False

    def apply(self, ctx: MigrationContext) -> None:
        profiles_dir = ctx.config_dir / 'profiles'
        if not profiles_dir.exists():
            return
        migrated: list[str] = []
        for f in profiles_dir.glob('*.json'):
            data = json.loads(f.read_text(encoding='utf-8'))
            if data.get('version', 0) >= 10:
                continue

            backend = data.get('backend', {})
            if backend.get('screenshot_impl') == 'windows':
                backend['screenshot_impl'] = 'windows_native'
                data['backend'] = backend
                migrated.append(f.stem)

            data['version'] = 10
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

        if migrated:
            ctx.messages.append(MigrationMessage(
                text="DMM 截图方式（windows）已自动切换到新的截图方式（windows_native）。如出现问题可手动切换回原选项。",
                old_version='v2026.06b2',
                new_version='v2026.06b3',
            ))


# ---------------------------------------------------------------------------
# 迁移链
# ---------------------------------------------------------------------------

LATEST_VERSION: int = 10

profile_migration_chain = MigrationChain(steps=[
    ProfileV1ToV2(),
    ProfileV2ToV3(),
    ProfileV3ToV4(),
    ProfileV4ToV5(),
    ProfileV5ToV6(),
    ProfileV6ToV7(),
    ProfileV7ToV8(),
    SharedV1ToV2(),
    ProfileV8ToV9(),
    ProfileV9ToV10(),
])


def upgrade_config(config_dir: str | Path = 'conf') -> None:
    """检查并升级配置到最新版本。

    迁移消息通过延迟消息机制传递，GUI 启动后可通过 get_deferred_messages() 获取。
    """
    messages = profile_migration_chain.run(Path(config_dir))
    if messages:
        add_deferred_messages(messages)
        logger.info("Config migration completed with %d message(s).", len(messages))
