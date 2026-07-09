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
    model_config = ConfigDict(populate_by_name=True)

    id: str
    effect_type: str | None = Field(None, alias='effectType')
    effect_value1: int | None = Field(None, alias='effectValue1')
    effect_value2: int | None = Field(None, alias='effectValue2')
    effect_count: int | None = Field(None, alias='effectCount')
    effect_turn: int | None = Field(None, alias='effectTurn')
    target_produce_card_id: str | None = Field(None, alias='targetProduceCardId')
    target_upgrade_count: int | None = Field(None, alias='targetUpgradeCount')
    target_exam_effect_type: str | None = Field(None, alias='targetExamEffectType')
    produce_card_search_id: str | None = Field(None, alias='produceCardSearchId')
    move_position_type: str | None = Field(None, alias='movePositionType')
    pick_range_type: str | None = Field(None, alias='pickRangeType')
    pick_count_min: int | None = Field(None, alias='pickCountMin')
    pick_count_max: int | None = Field(None, alias='pickCountMax')
    chain_produce_exam_effect_id: str | None = Field(None, alias='chainProduceExamEffectId')
    produce_exam_status_enchant_id: str | None = Field(None, alias='produceExamStatusEnchantId')
    produce_card_status_enchant_id: str | None = Field(None, alias='produceCardStatusEnchantId')
    produce_card_grow_effect_ids: str | None = Field(None, alias='produceCardGrowEffectIds')
    effect_group_ids: str | None = Field(None, alias='effectGroupIds')
    produce_descriptions: str | None = Field(None, alias='produceDescriptions')
    customize_produce_descriptions: str | None = Field(None, alias='customizeProduceDescriptions')


class ProduceCardRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    upgrade_count: int | None = Field(None, alias='upgradeCount')
    name: str
    asset_id: str | None = Field(None, alias='assetId')
    is_character_asset: bool = Field(False, alias='isCharacterAsset')
    rarity: str | None = None
    plan_type: str | None = Field(None, alias='planType')
    category: str | None = None
    stamina: int | None = None
    force_stamina: int | None = Field(None, alias='forceStamina')
    cost_type: str | None = Field(None, alias='costType')
    cost_value: int | None = Field(None, alias='costValue')
    play_produce_exam_trigger_id: str | None = Field(None, alias='playProduceExamTriggerId')
    play_effects_raw: str = Field('', alias='playEffects')
    play_move_position_type: str | None = Field(None, alias='playMovePositionType')
    move_effect_trigger_type: str | None = Field(None, alias='moveEffectTriggerType')
    move_produce_exam_effect_ids_raw: str | None = Field(None, alias='moveProduceExamEffectIds')
    is_end_turn_lost: bool = Field(False, alias='isEndTurnLost')
    is_initial: bool = Field(False, alias='isInitial')
    is_restrict: bool = Field(False, alias='isRestrict')
    produce_card_status_enchant_id: str | None = Field(None, alias='produceCardStatusEnchantId')
    search_tag: str | None = Field(None, alias='searchTag')
    library_hidden: bool = Field(False, alias='libraryHidden')
    no_deck_duplication: bool = Field(False, alias='noDeckDuplication')
    is_reward: bool = Field(False, alias='isReward')
    produce_descriptions: str | None = Field(None, alias='produceDescriptions')
    unlock_producer_level: int | None = Field(None, alias='unlockProducerLevel')
    rental_unlock_producer_level: int | None = Field(None, alias='rentalUnlockProducerLevel')
    evaluation: int | None = None
    origin_idol_card_id: str | None = Field(None, alias='originIdolCardId')
    origin_support_card_id: str | None = Field(None, alias='originSupportCardId')
    is_initial_deck_produce_card: bool = Field(False, alias='isInitialDeckProduceCard')
    effect_group_ids: str | None = Field(None, alias='effectGroupIds')
    produce_card_customize_ids: str | None = Field(None, alias='produceCardCustomizeIds')
    max_customize_count: int | None = Field(None, alias='maxCustomizeCount')
    is_conversion: bool = Field(False, alias='isConversion')
    move_produce_exam_trigger_ids: str | None = Field(None, alias='moveProduceExamTriggerIds')
    view_start_time: str | None = Field(None, alias='viewStartTime')
    is_limited: bool = Field(False, alias='isLimited')
    order: str | None = Field(None, alias='order')


@dataclass
class ProduceExamEffect:
    """
    考试效果

    卡牌发动后的 buff 都存放在此类中，比如好印象、元气、回合追加等所有效果。
    """
    _id: str
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
    target_upgrade_count: int | None
    target_exam_effect_type: str | None
    _produce_card_search_id: str | None
    move_position_type: str | None
    pick_range_type: str | None
    pick_count_min: int | None
    pick_count_max: int | None
    _chain_produce_exam_effect_id: str | None
    _produce_exam_status_enchant_id: str | None
    _produce_card_status_enchant_id: str | None
    _produce_card_grow_effect_ids: str | None
    _effect_group_ids: str | None
    produce_descriptions: str | None
    customize_produce_descriptions: str | None

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
    """出牌后触发的考试效果"""
    _produce_exam_trigger_id: str
    _produce_exam_effect_id: str
    produce_exam_effect: ProduceExamEffect | None
    hide_icon: bool

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
    """技能卡"""
    _id: str
    upgrade_count: int | None
    name: str
    _asset_id: str | None
    is_character_asset: bool
    rarity: str | None
    plan_type: str | None
    category: str | None
    stamina: int | None
    """需要消耗的元气或体力值（绿色）。
    
    对于同一张卡片，stamina 和 force_stamina 只会有一个有值，另一个为 0。
    """
    force_stamina: int | None
    """需要消耗的体力值（红色）
    
    对于同一张卡片，stamina 和 force_stamina 只会有一个有值，另一个为 0。
    """
    cost_type: str | None
    cost_value: int | None
    """消耗数值
    
    部分卡片会消耗好印象、集中等非元气或体力值的 buff，即此字段的值。
    """
    _play_produce_exam_trigger_id: str | None
    _play_effects_raw: str
    """出牌效果（JSON 字符串）"""
    play_effects: list[PlayEffect]
    """出牌效果（解析后的实体列表）"""
    play_move_position_type: str | None
    move_effect_trigger_type: str | None
    _move_produce_exam_effect_ids_raw: str | None
    move_produce_exam_effects: list[ProduceExamEffect]
    is_end_turn_lost: bool
    is_initial: bool
    is_restrict: bool
    _produce_card_status_enchant_id: str | None
    search_tag: str | None
    library_hidden: bool
    no_deck_duplication: bool
    is_reward: bool
    produce_descriptions: str | None
    unlock_producer_level: int | None
    rental_unlock_producer_level: int | None
    evaluation: int | None
    _origin_idol_card_id: str | None
    _origin_support_card_id: str | None
    is_initial_deck_produce_card: bool
    _effect_group_ids: str | None
    _produce_card_customize_ids: str | None
    max_customize_count: int | None
    is_conversion: bool
    _move_produce_exam_trigger_ids: str | None
    view_start_time: str | None
    is_limited: bool
    order: str | None

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