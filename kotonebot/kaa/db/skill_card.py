from enum import Enum
from typing import Literal
from dataclasses import dataclass

from kotonebot.kaa.db.idol_card import IdolCard

from .sqlite import select, select_many
from .constants import CharacterId


class CardType(Enum):
    """卡牌作用类型"""
    MENTAL = "ProduceCardCategory_MentalSkill"
    """M 卡"""
    ACTIVE = "ProduceCardCategory_ActiveSkill"
    """A 卡"""
    TROUBLE = "ProduceCardCategory_Trouble"
    """T 卡"""


class PlanType(Enum):
    """卡牌职业分类"""
    COMMON = "ProducePlanType_Common"
    """通用"""
    SENSE = "ProducePlanType_Plan1"
    """感性"""
    LOGIC = "ProducePlanType_Plan2"
    """理性"""
    ANOMALY = "ProducePlanType_Plan3"
    """非凡"""

class PlayMovePositionType(Enum):
    """卡牌打出后 除外 还是 进入弃牌堆"""
    LOST = "ProduceCardMovePositionType_Lost"
    """除外，洗牌后无法抽到"""
    GRAVE = "ProduceCardMovePositionType_Grave"
    """进入弃牌堆，洗牌后仍能抽到"""


@dataclass
class SkillCard:
    """技能卡"""
    id: str
    asset_id: str
    """资源 ID。"""
    plan_type: PlanType
    """卡牌职业分类。"""
    card_type: CardType
    """卡牌作用类型。"""
    name: str
    """卡牌名称。"""
    once: bool
    """此卡牌在考试或课程中是否只会出现一次。"""
    play_move_position_type: PlayMovePositionType
    """此卡牌在考试或课程中使用后除外还是进入弃牌堆。"""
    origin_idol_card: str | None
    """此卡牌所属的偶像卡。"""
    origin_support_card: str | None
    """此卡牌所属的支援卡。"""
    is_character_asset: bool
    """
    此卡牌的资源图片是否会随偶像变化。
    
    若为 True，则 `asset_id` 有多个。
    实际资源 ID 为 `[f'{self.asset_id}-{ii}' for ii in idol_ids]`
    """

    @property
    def is_from_idol_card(self) -> bool:
        """此卡牌是否来自偶像卡。"""
        return self.origin_idol_card is not None

    @property
    def is_from_support_card(self) -> bool:
        """此卡牌是否来自支援卡。"""
        return self.origin_support_card is not None

    @property
    def asset_ids(self) -> list[str]:
        """
        此卡牌的所有资源 ID，包括 `is_character_asset` 为 True 的情况。
        """
        if not self.is_character_asset:
            return [self.asset_id]
        return [f'{self.asset_id}-{ii.value}' for ii in CharacterId]

    @classmethod
    def all(cls) -> list['SkillCard']:
        """获取所有技能卡"""
        rows = select_many("""
        SELECT
            id,
            assetId,
            planType,
            category AS cardType,
            name,
            noDeckDuplication AS once,
            playMovePositionType,
            originIdolCardId AS idolCardId,
            originSupportCardId AS supportCardId,
            isCharacterAsset
        FROM ProduceCard;
        """)
        results = []
        for row in rows:
            results.append(cls(
                id=row["id"],
                asset_id=row["assetId"],
                plan_type=PlanType(row["planType"]),
                card_type=CardType(row["cardType"]),
                name=row["name"],
                once=bool(row["once"]),
                play_move_position_type=PlayMovePositionType(row["playMovePositionType"]),
                origin_idol_card=row["idolCardId"],
                origin_support_card=row["supportCardId"],
                is_character_asset=bool(row["isCharacterAsset"])
            ))
        return results

    @classmethod
    def from_asset_id(cls, asset_id: str) -> 'SkillCard | None':
        """根据资源 ID 查询 SkillCard。"""
        for ci in CharacterId:
            if asset_id.endswith(ci.value):
                asset_id = asset_id[:-len(ci.value) - 1]
                break
        row = select("""
        SELECT
            id,
            assetId,
            planType,
            category AS cardType,
            name,
            noDeckDuplication AS once,
            playMovePositionType,
            originIdolCardId AS idolCardId,
            originSupportCardId AS supportCardId,
            isCharacterAsset
        FROM ProduceCard
        WHERE assetId = ?;
        """, asset_id)
        if row is None:
            return None
        return cls(
            id=row["id"],
            asset_id=row["assetId"],
            plan_type=PlanType(row["planType"]),
            card_type=CardType(row["cardType"]),
            name=row["name"],
            once=bool(row["once"]),
            play_move_position_type=PlayMovePositionType(row["playMovePositionType"]),
            origin_idol_card=row["idolCardId"],
            origin_support_card=row["supportCardId"],
            is_character_asset=bool(row["isCharacterAsset"])
        )
    
if __name__ == '__main__':
    from pprint import pprint as print
    print(SkillCard.from_asset_id('img_general_skillcard_men-2_077-hski'))
