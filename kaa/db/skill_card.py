from dataclasses import dataclass
from functools import cached_property, lru_cache
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .constants import ProduceExamEffectType
from ._util import (
    load_by_ids,
    log_missing_ids,
    parse_id_list,
    parse_json_list,
    register_cache_clear,
    row_dict,
)
from .sqlite import select, select_many

PRODUCE_CARD_COLUMNS = """
    id,
    upgradeCount,
    name,
    assetId,
    isCharacterAsset,
    rarity,
    planType,
    category,
    stamina,
    forceStamina,
    costType,
    costValue,
    playProduceExamTriggerId,
    playEffects,
    playMovePositionType,
    moveEffectTriggerType,
    moveProduceExamEffectIds,
    isEndTurnLost,
    isInitial,
    isRestrict,
    produceCardStatusEnchantId,
    searchTag,
    libraryHidden,
    noDeckDuplication,
    isReward,
    produceDescriptions,
    unlockProducerLevel,
    rentalUnlockProducerLevel,
    evaluation,
    originIdolCardId,
    originSupportCardId,
    isInitialDeckProduceCard,
    effectGroupIds,
    produceCardCustomizeIds,
    maxCustomizeCount,
    isConversion,
    moveProduceExamTriggerIds,
    viewStartTime,
    isLimited,
    "order"
""".strip()

PRODUCE_CARD_SELECT = f'SELECT {PRODUCE_CARD_COLUMNS} FROM ProduceCard'

PRODUCE_EXAM_EFFECT_COLUMNS = """
    id,
    effectType,
    effectValue1,
    effectValue2,
    effectCount,
    effectTurn,
    targetProduceCardId,
    targetUpgradeCount,
    targetExamEffectType,
    produceCardSearchId,
    movePositionType,
    pickRangeType,
    pickCountMin,
    pickCountMax,
    chainProduceExamEffectId,
    produceExamStatusEnchantId,
    produceCardStatusEnchantId,
    produceCardGrowEffectIds,
    effectGroupIds,
    produceDescriptions,
    customizeProduceDescriptions
""".strip()


class ProduceExamEffectRow(BaseModel):
    """ProduceExamEffect 表行。"""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    """考试效果 ID（ProduceExamEffect.id）。"""
    effect_type: str | None = Field(None, alias='effectType')
    """效果类型（ProduceExamEffect.effectType，ProduceExamEffectType 枚举值）。"""
    effect_value1: int | None = Field(None, alias='effectValue1')
    """效果参数 1。"""
    effect_value2: int | None = Field(None, alias='effectValue2')
    """效果参数 2。"""
    effect_count: int | None = Field(None, alias='effectCount')
    """效果触发次数限制。"""
    effect_turn: int | None = Field(None, alias='effectTurn')
    """效果持续回合数，-1 表示永久。"""
    target_produce_card_id: str | None = Field(None, alias='targetProduceCardId')
    """目标技能卡 ID（ProduceCard.id）。"""
    target_upgrade_count: int | None = Field(None, alias='targetUpgradeCount')
    """目标技能卡强化次数，与 target_produce_card_id 配套。"""
    target_exam_effect_type: str | None = Field(None, alias='targetExamEffectType')
    """目标考试效果类型（ProduceExamEffectType 枚举值）。"""
    produce_card_search_id: str | None = Field(None, alias='produceCardSearchId')
    """卡牌检索范围 ID（ProduceCardSearch.id）。"""
    move_position_type: str | None = Field(None, alias='movePositionType')
    """卡牌移动位置类型（ProduceCardMovePositionType 枚举值）。"""
    pick_range_type: str | None = Field(None, alias='pickRangeType')
    """选牌范围类型枚举值。"""
    pick_count_min: int | None = Field(None, alias='pickCountMin')
    """选牌数量下限。"""
    pick_count_max: int | None = Field(None, alias='pickCountMax')
    """选牌数量上限。"""
    chain_produce_exam_effect_id: str | None = Field(None, alias='chainProduceExamEffectId')
    """链式后续效果 ID（ProduceExamEffect.id）。"""
    produce_exam_status_enchant_id: str | None = Field(None, alias='produceExamStatusEnchantId')
    """考试状态附魔 ID（ProduceExamStatusEnchant.id）。"""
    produce_card_status_enchant_id: str | None = Field(None, alias='produceCardStatusEnchantId')
    """卡牌状态附魔 ID（ProduceCardStatusEnchant.id）。"""
    produce_card_grow_effect_ids: str | None = Field(None, alias='produceCardGrowEffectIds')
    """卡牌成长效果 ID 列表 JSON（元素为 ProduceCardGrowEffect.id）。"""
    effect_group_ids: str | None = Field(None, alias='effectGroupIds')
    """效果组 ID 列表 JSON（元素为 EffectGroup.id）。"""
    produce_descriptions: str | None = Field(None, alias='produceDescriptions')
    """效果描述 JSON（ProduceDescription 数组）。"""
    customize_produce_descriptions: str | None = Field(None, alias='customizeProduceDescriptions')
    """自定义效果描述 JSON（ProduceDescription 数组）。"""


class ProduceCardRow(BaseModel):
    """ProduceCard 表行。"""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    """技能卡 ID（ProduceCard.id）。"""
    upgrade_count: int | None = Field(None, alias='upgradeCount')
    """强化次数（ProduceCard.upgradeCount）。"""
    name: str
    """卡牌名称（ProduceCard.name）。"""
    asset_id: str | None = Field(None, alias='assetId')
    """资源标识（ProduceCard.assetId）。"""
    is_character_asset: bool = Field(False, alias='isCharacterAsset')
    """是否为角色专属资源。"""
    rarity: str | None = None
    """稀有度（ProduceCardRarity 枚举值）。"""
    plan_type: str | None = Field(None, alias='planType')
    """计划类型（ProducePlanType 枚举值）。"""
    category: str | None = None
    """卡牌类别（ProduceCardCategory 枚举值）。"""
    stamina: int | None = None
    """元气/体力消耗（绿色）。"""
    force_stamina: int | None = Field(None, alias='forceStamina')
    """体力消耗（红色）。"""
    cost_type: str | None = Field(None, alias='costType')
    """额外消耗类型（ProduceCardCostType 枚举值）。"""
    cost_value: int | None = Field(None, alias='costValue')
    """额外消耗数值。"""
    play_produce_exam_trigger_id: str | None = Field(None, alias='playProduceExamTriggerId')
    """出牌触发条件 ID（ProduceExamTrigger.id）。"""
    play_effects_raw: str = Field('', alias='playEffects')
    """出牌效果 JSON 数组。"""
    play_move_position_type: str | None = Field(None, alias='playMovePositionType')
    """出牌后卡牌移动位置（ProduceCardMovePositionType 枚举值）。"""
    move_effect_trigger_type: str | None = Field(None, alias='moveEffectTriggerType')
    """移动效果触发类型枚举值。"""
    move_produce_exam_effect_ids_raw: str | None = Field(None, alias='moveProduceExamEffectIds')
    """移动时触发的考试效果 ID 列表 JSON（元素为 ProduceExamEffect.id）。"""
    is_end_turn_lost: bool = Field(False, alias='isEndTurnLost')
    """回合结束时是否失去。"""
    is_initial: bool = Field(False, alias='isInitial')
    """是否为初始卡组卡牌。"""
    is_restrict: bool = Field(False, alias='isRestrict')
    """是否为限制卡。"""
    produce_card_status_enchant_id: str | None = Field(None, alias='produceCardStatusEnchantId')
    """卡牌状态附魔 ID（ProduceCardStatusEnchant.id）。"""
    search_tag: str | None = Field(None, alias='searchTag')
    """检索标签。"""
    library_hidden: bool = Field(False, alias='libraryHidden')
    """是否在图鉴中隐藏。"""
    no_deck_duplication: bool = Field(False, alias='noDeckDuplication')
    """是否禁止卡组重复。"""
    is_reward: bool = Field(False, alias='isReward')
    """是否为奖励卡。"""
    produce_descriptions: str | None = Field(None, alias='produceDescriptions')
    """卡牌描述 JSON。"""
    unlock_producer_level: int | None = Field(None, alias='unlockProducerLevel')
    """解锁所需制作人等级。"""
    rental_unlock_producer_level: int | None = Field(None, alias='rentalUnlockProducerLevel')
    """租赁解锁所需制作人等级。"""
    evaluation: int | None = None
    """卡牌评价分。"""
    origin_idol_card_id: str | None = Field(None, alias='originIdolCardId')
    """来源偶像卡 ID（IdolCard.id）。"""
    origin_support_card_id: str | None = Field(None, alias='originSupportCardId')
    """来源支援卡 ID（SupportCard.id）。"""
    is_initial_deck_produce_card: bool = Field(False, alias='isInitialDeckProduceCard')
    """是否为初始牌组技能卡。"""
    effect_group_ids: str | None = Field(None, alias='effectGroupIds')
    """效果组 ID 列表 JSON（元素为 EffectGroup.id）。"""
    produce_card_customize_ids: str | None = Field(None, alias='produceCardCustomizeIds')
    """自定义项 ID 列表 JSON（元素为 ProduceCardCustomize.id）。"""
    max_customize_count: int | None = Field(None, alias='maxCustomizeCount')
    """最大自定义次数。"""
    is_conversion: bool = Field(False, alias='isConversion')
    """是否为转换卡。"""
    move_produce_exam_trigger_ids: str | None = Field(None, alias='moveProduceExamTriggerIds')
    """移动时触发条件 ID 列表 JSON（元素为 ProduceExamTrigger.id）。"""
    view_start_time: str | None = Field(None, alias='viewStartTime')
    """可见开始时间。"""
    is_limited: bool = Field(False, alias='isLimited')
    """是否为限定卡。"""
    order: str | None = Field(None, alias='order')
    """排序权重。"""


@dataclass
class ProduceExamEffect:
    """考试效果（业务用）。

    卡牌发动后的 buff 都存放在此类中，比如好印象、元气、回合追加等所有效果。
    """
    _id: str
    """考试效果 ID（ProduceExamEffect.id）。"""
    effect_type: ProduceExamEffectType | None
    """效果类型"""
    effect_value1: int | None
    """效果参数 1，具体含义取决于 `effect_type`"""
    effect_value2: int | None
    """效果参数 2，具体含义取决于 `effect_type`"""
    effect_count: int | None
    """TODO 这个是什么？"""
    effect_turn: int | None
    """
    回合参数

    一般逐回合衰减的效果会有这个参数，表示持续回合数。-1 表示永久。
    """
    _target_produce_card_id: str | None
    """目标技能卡 ID（ProduceCard.id）。"""
    target_upgrade_count: int | None
    """目标技能卡强化次数，与 _target_produce_card_id 配套。"""
    target_exam_effect_type: str | None
    """目标考试效果类型（ProduceExamEffectType 枚举值）。"""
    _produce_card_search_id: str | None
    """卡牌检索范围 ID（ProduceCardSearch.id）。"""
    move_position_type: str | None
    """卡牌移动位置类型（ProduceCardMovePositionType 枚举值）。"""
    pick_range_type: str | None
    """选牌范围类型枚举值。"""
    pick_count_min: int | None
    """选牌数量下限。"""
    pick_count_max: int | None
    """选牌数量上限。"""
    _chain_produce_exam_effect_id: str | None
    """链式后续效果 ID（ProduceExamEffect.id）。"""
    _produce_exam_status_enchant_id: str | None
    """考试状态附魔 ID（ProduceExamStatusEnchant.id）。"""
    _produce_card_status_enchant_id: str | None
    """卡牌状态附魔 ID（ProduceCardStatusEnchant.id）。"""
    _produce_card_grow_effect_ids: str | None
    """卡牌成长效果 ID 列表 JSON（元素为 ProduceCardGrowEffect.id）。"""
    _effect_group_ids: str | None
    """效果组 ID 列表 JSON（元素为 EffectGroup.id）。"""
    produce_descriptions: str | None
    """效果描述 JSON（ProduceDescription 数组）。"""
    customize_produce_descriptions: str | None
    """自定义效果描述 JSON（ProduceDescription 数组）。"""

    @classmethod
    def from_row(cls, row: ProduceExamEffectRow) -> 'ProduceExamEffect':
        effect_type = (
            ProduceExamEffectType(row.effect_type)
            if row.effect_type is not None
            else None
        )
        return cls(
            row.id,
            effect_type,
            row.effect_value1,
            row.effect_value2,
            row.effect_count,
            row.effect_turn,
            row.target_produce_card_id,
            row.target_upgrade_count,
            row.target_exam_effect_type,
            row.produce_card_search_id,
            row.move_position_type,
            row.pick_range_type,
            row.pick_count_min,
            row.pick_count_max,
            row.chain_produce_exam_effect_id,
            row.produce_exam_status_enchant_id,
            row.produce_card_status_enchant_id,
            row.produce_card_grow_effect_ids,
            row.effect_group_ids,
            row.produce_descriptions,
            row.customize_produce_descriptions,
        )


@dataclass
class PlayEffect:
    """出牌后触发的考试效果（playEffects JSON 单项解析结果）。"""
    _produce_exam_trigger_id: str
    """触发条件 ID（ProduceExamTrigger.id）。"""
    _produce_exam_effect_id: str
    """考试效果 ID（ProduceExamEffect.id）。"""
    produce_exam_effect: ProduceExamEffect | None
    """关联的考试效果实体。"""
    hide_icon: bool
    """是否隐藏效果图标。"""

    @classmethod
    def from_dict(cls, data: dict, effect_map: dict[str, ProduceExamEffect]) -> 'PlayEffect':
        effect_id = data.get('produceExamEffectId', '')
        return cls(
            data.get('produceExamTriggerId', ''),
            effect_id,
            effect_map.get(effect_id),
            bool(data.get('hideIcon', False)),
        )


@dataclass
class SkillCard:
    """技能卡（业务用）。"""
    _id: str
    """技能卡 ID（ProduceCard.id）。"""
    upgrade_count: int | None
    """强化次数（ProduceCard.upgradeCount）。"""
    name: str
    """卡牌名称（ProduceCard.name）。"""
    _asset_id: str | None
    """资源标识（ProduceCard.assetId）。"""
    is_character_asset: bool
    """是否为角色专属资源。"""
    rarity: str | None
    """稀有度（ProduceCardRarity 枚举值）。"""
    plan_type: str | None
    """计划类型（ProducePlanType 枚举值）。"""
    category: str | None
    """卡牌类别（ProduceCardCategory 枚举值）。"""
    stamina: int | None
    """需要消耗的元气或体力值（绿色）。
    
    对于同一张卡片，stamina 和 force_stamina 只会有一个有值，另一个为 0。
    """
    force_stamina: int | None
    """需要消耗的体力值（红色）
    
    对于同一张卡片，stamina 和 force_stamina 只会有一个有值，另一个为 0。
    """
    cost_type: str | None
    """额外消耗类型（ProduceCardCostType 枚举值）。"""
    cost_value: int | None
    """消耗数值
    
    部分卡片会消耗好印象、集中等非元气或体力值的 buff，即此字段的值。
    """
    _play_produce_exam_trigger_id: str | None
    """出牌触发条件 ID（ProduceExamTrigger.id）。"""
    _play_effects_raw: str
    """出牌效果（JSON 字符串）"""
    play_effects: list[PlayEffect]
    """出牌效果（解析后的实体列表）"""
    play_move_position_type: str | None
    """出牌后卡牌移动位置（ProduceCardMovePositionType 枚举值）。"""
    move_effect_trigger_type: str | None
    """移动效果触发类型枚举值。"""
    _move_produce_exam_effect_ids_raw: str | None
    """移动时触发的考试效果 ID 列表 JSON（元素为 ProduceExamEffect.id）。"""
    move_produce_exam_effects: list[ProduceExamEffect]
    """移动时触发的考试效果实体列表。"""
    is_end_turn_lost: bool
    """回合结束时是否失去。"""
    is_initial: bool
    """是否为初始卡组卡牌。"""
    is_restrict: bool
    """是否为限制卡。"""
    _produce_card_status_enchant_id: str | None
    """卡牌状态附魔 ID（ProduceCardStatusEnchant.id）。"""
    search_tag: str | None
    """检索标签。"""
    library_hidden: bool
    """是否在图鉴中隐藏。"""
    no_deck_duplication: bool
    """是否禁止卡组重复。"""
    is_reward: bool
    """是否为奖励卡。"""
    produce_descriptions: str | None
    """卡牌描述 JSON。"""
    unlock_producer_level: int | None
    """解锁所需制作人等级。"""
    rental_unlock_producer_level: int | None
    """租赁解锁所需制作人等级。"""
    evaluation: int | None
    """卡牌评价分。"""
    _origin_idol_card_id: str | None
    """来源偶像卡 ID（IdolCard.id）。"""
    _origin_support_card_id: str | None
    """来源支援卡 ID（SupportCard.id）。"""
    is_initial_deck_produce_card: bool
    """是否为初始牌组技能卡。"""
    _effect_group_ids: str | None
    """效果组 ID 列表 JSON（元素为 EffectGroup.id）。"""
    _produce_card_customize_ids: str | None
    """自定义项 ID 列表 JSON（元素为 ProduceCardCustomize.id）。"""
    max_customize_count: int | None
    """最大自定义次数。"""
    is_conversion: bool
    """是否为转换卡。"""
    _move_produce_exam_trigger_ids: str | None
    """移动时触发条件 ID 列表 JSON（元素为 ProduceExamTrigger.id）。"""
    view_start_time: str | None
    """可见开始时间。"""
    is_limited: bool
    """是否为限定卡。"""
    order: str | None
    """排序权重。"""

    @cached_property
    def effect_display_text(self) -> str:
        """效果描述文本"""
        texts = []
        for effect in self.play_effects:
            if not effect.produce_exam_effect or not effect.produce_exam_effect.produce_descriptions:
                continue
            data: list[dict[str, Any]] = json.loads(effect.produce_exam_effect.produce_descriptions)
            texts.append(''.join(item.get('text', '') for item in data))
        return '\n'.join(texts).replace('</nobr>', '').replace('<nobr>', '').strip()

    def __repr__(self) -> str:
        return (
            'SkillCard('
            f'id={self._id!r}, '
            f'name={self.name!r}, '
            f'asset_id={self._asset_id!r}, '
            ')'
        )

    @classmethod
    def _from_row(cls, row, effect_map: dict[str, ProduceExamEffect]) -> 'SkillCard':
        card = ProduceCardRow.model_validate(row_dict(row))
        play_effects: list[PlayEffect] = []
        for item in parse_json_list(card.play_effects_raw, context=f'ProduceCard {card.id}.playEffects'):
            if isinstance(item, dict):
                play_effects.append(PlayEffect.from_dict(item, effect_map))
        move_effect_ids = parse_id_list(card.move_produce_exam_effect_ids_raw)
        move_effects = [effect_map[eid] for eid in move_effect_ids if eid in effect_map]
        return cls(
            card.id,
            card.upgrade_count,
            card.name,
            card.asset_id,
            card.is_character_asset,
            card.rarity,
            card.plan_type,
            card.category,
            card.stamina,
            card.force_stamina,
            card.cost_type,
            card.cost_value,
            card.play_produce_exam_trigger_id,
            card.play_effects_raw,
            play_effects,
            card.play_move_position_type,
            card.move_effect_trigger_type,
            card.move_produce_exam_effect_ids_raw,
            move_effects,
            card.is_end_turn_lost,
            card.is_initial,
            card.is_restrict,
            card.produce_card_status_enchant_id,
            card.search_tag,
            card.library_hidden,
            card.no_deck_duplication,
            card.is_reward,
            card.produce_descriptions,
            card.unlock_producer_level,
            card.rental_unlock_producer_level,
            card.evaluation,
            card.origin_idol_card_id,
            card.origin_support_card_id,
            card.is_initial_deck_produce_card,
            card.effect_group_ids,
            card.produce_card_customize_ids,
            card.max_customize_count,
            card.is_conversion,
            card.move_produce_exam_trigger_ids,
            card.view_start_time,
            card.is_limited,
            card.order,
        )

    @classmethod
    def from_asset_id(cls, asset_id: str) -> 'SkillCard | None':
        """
        根据 asset_id 查询 SkillCard。
        """
        row = select(f'{PRODUCE_CARD_SELECT} WHERE assetId = ?;', asset_id)
        if row is None:
            return None
        effect_map = _load_exam_effects_from_rows([row])
        return cls._from_row(row, effect_map)

    @classmethod
    def from_id(cls, card_id: str) -> 'SkillCard | None':
        """根据 id 查询 SkillCard。"""
        row = select(f'{PRODUCE_CARD_SELECT} WHERE id = ?;', card_id)
        if row is None:
            return None
        effect_map = _load_exam_effects_from_rows([row])
        return cls._from_row(row, effect_map)

    @classmethod
    def all(cls) -> list['SkillCard']:
        """获取所有技能卡"""
        return list(_all_cached())


def _collect_exam_effect_ids(rows) -> set[str]:
    ids: set[str] = set()
    for row in rows:
        card_id = row['id']
        ids.update(parse_id_list(
            row['moveProduceExamEffectIds'],
            context=f'ProduceCard {card_id}.moveProduceExamEffectIds',
        ))
        for item in parse_json_list(row['playEffects'], context=f'ProduceCard {card_id}.playEffects'):
            if not isinstance(item, dict):
                continue
            effect_id = item.get('produceExamEffectId')
            if isinstance(effect_id, str) and effect_id:
                ids.add(effect_id)
    return ids


def _load_exam_effects_from_rows(rows) -> dict[str, ProduceExamEffect]:
    ids = _collect_exam_effect_ids(rows)
    if not ids:
        return {}
    effect_rows = load_by_ids('ProduceExamEffect', ids, columns=PRODUCE_EXAM_EFFECT_COLUMNS)
    result: dict[str, ProduceExamEffect] = {}
    for row in effect_rows:
        parsed = ProduceExamEffectRow.model_validate(row_dict(row))
        result[parsed.id] = ProduceExamEffect.from_row(parsed)
    log_missing_ids('ProduceExamEffect for skill cards', ids, result)
    return result


@lru_cache(maxsize=1)
def _all_cached() -> tuple[SkillCard, ...]:
    rows = select_many(f'{PRODUCE_CARD_SELECT};')
    effect_map = _load_exam_effects_from_rows(rows)
    return tuple(SkillCard._from_row(row, effect_map) for row in rows)


register_cache_clear(_all_cached.cache_clear)