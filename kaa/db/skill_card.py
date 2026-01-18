from dataclasses import dataclass
from functools import cached_property, lru_cache
import json
from typing import Any

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

PRODUCE_CARD_SELECT = f"SELECT {PRODUCE_CARD_COLUMNS} FROM ProduceCard"

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

PRODUCE_EXAM_EFFECT_SELECT = f"SELECT {PRODUCE_EXAM_EFFECT_COLUMNS} FROM ProduceExamEffect"

@dataclass
class ProduceExamEffect:
    """
    考试效果

    卡牌发动后的 buff 都存放在此类中，比如好印象、元气、回合追加等所有效果。
    """
    _id: str
    effect_type: str | None
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
    def from_row(cls, row) -> 'ProduceExamEffect':
        data = dict(row)
        return cls(
            str(data.get('id') or ''),
            data.get('effectType'),
            data.get('effectValue1'),
            data.get('effectValue2'),
            data.get('effectCount'),
            data.get('effectTurn'),
            data.get('targetProduceCardId'),
            data.get('targetUpgradeCount'),
            data.get('targetExamEffectType'),
            data.get('produceCardSearchId'),
            data.get('movePositionType'),
            data.get('pickRangeType'),
            data.get('pickCountMin'),
            data.get('pickCountMax'),
            data.get('chainProduceExamEffectId'),
            data.get('produceExamStatusEnchantId'),
            data.get('produceCardStatusEnchantId'),
            data.get('produceCardGrowEffectIds'),
            data.get('effectGroupIds'),
            data.get('produceDescriptions'),
            data.get('customizeProduceDescriptions'),
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
    """需要消耗的元气或体力值（绿色）"""
    force_stamina: int | None
    """需要消耗的体力值（红色）"""
    cost_type: str | None
    cost_value: int | None
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

    @classmethod
    def _from_row(cls, row, effect_map: dict[str, ProduceExamEffect]) -> 'SkillCard':
        play_effects_raw = row['playEffects']
        play_effect_items = _parse_json_list(play_effects_raw)
        play_effects: list[PlayEffect] = []
        for item in play_effect_items:
            if isinstance(item, dict):
                play_effects.append(PlayEffect.from_dict(item, effect_map))

        move_effect_ids = _parse_id_list(row['moveProduceExamEffectIds'])
        move_effects = [effect_map[eid] for eid in move_effect_ids if eid in effect_map]
        return cls(
            row['id'],
            row['upgradeCount'],
            row['name'],
            row['assetId'],
            bool(row['isCharacterAsset']),
            row['rarity'],
            row['planType'],
            row['category'],
            row['stamina'],
            row['forceStamina'],
            row['costType'],
            row['costValue'],
            row['playProduceExamTriggerId'],
            row['playEffects'],
            play_effects,
            row['playMovePositionType'],
            row['moveEffectTriggerType'],
            row['moveProduceExamEffectIds'],
            move_effects,
            bool(row['isEndTurnLost']),
            bool(row['isInitial']),
            bool(row['isRestrict']),
            row['produceCardStatusEnchantId'],
            row['searchTag'],
            bool(row['libraryHidden']),
            bool(row['noDeckDuplication']),
            bool(row['isReward']),
            row['produceDescriptions'],
            row['unlockProducerLevel'],
            row['rentalUnlockProducerLevel'],
            row['evaluation'],
            row['originIdolCardId'],
            row['originSupportCardId'],
            bool(row['isInitialDeckProduceCard']),
            row['effectGroupIds'],
            row['produceCardCustomizeIds'],
            row['maxCustomizeCount'],
            bool(row['isConversion']),
            row['moveProduceExamTriggerIds'],
            row['viewStartTime'],
            bool(row['isLimited']),
            row['order'],
        )

    @classmethod
    def from_asset_id(cls, asset_id: str) -> 'SkillCard | None':
        """
        根据 asset_id 查询 SkillCard。
        """
        row = select(f"{PRODUCE_CARD_SELECT} WHERE assetId = ?;", asset_id)
        if row is None:
            return None
        effect_map = _load_exam_effects_from_rows([row])
        return cls._from_row(row, effect_map)

    @classmethod
    def from_id(cls, card_id: str) -> 'SkillCard | None':
        """根据 id 查询 SkillCard。"""
        row = select(f"{PRODUCE_CARD_SELECT} WHERE id = ?;", card_id)
        if row is None:
            return None
        effect_map = _load_exam_effects_from_rows([row])
        return cls._from_row(row, effect_map)

    @classmethod
    def all(cls) -> list['SkillCard']:
        """获取所有技能卡"""
        rows = select_many(f"{PRODUCE_CARD_SELECT};")
        effect_map = _load_exam_effects_from_rows(rows)
        return [cls._from_row(row, effect_map) for row in rows]


def _parse_json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _parse_id_list(raw: str | None) -> list[str]:
    items = _parse_json_list(raw)
    return [item for item in items if isinstance(item, str) and item]

def _load_exam_effects_from_rows(rows) -> dict[str, ProduceExamEffect]:
    ids: set[str] = set()
    for row in rows:
        ids.update(_parse_id_list(row['moveProduceExamEffectIds']))
        for item in _parse_json_list(row['playEffects']):
            if isinstance(item, dict):
                effect_id = item.get('produceExamEffectId')
                if isinstance(effect_id, str) and effect_id:
                    ids.add(effect_id)
    if not ids:
        return {}
    id_list = sorted(ids)
    placeholders = ','.join('?' for _ in id_list)
    query = f"{PRODUCE_EXAM_EFFECT_SELECT} WHERE id IN ({placeholders});"
    effects = select_many(query, *id_list)
    result: dict[str, ProduceExamEffect] = {}
    for row in effects:
        data = dict(row)
        effect_id = data.get('id')
        if isinstance(effect_id, str) and effect_id:
            result[effect_id] = ProduceExamEffect.from_row(data)
    return result


if __name__ == '__main__':
    from pprint import pprint as print
    c=SkillCard.from_asset_id('img_general_skillcard_ido-3_102')
    print(c)