"""
授業（学園活動）数据库实体类。
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field

from ._util import (
    collect_ids,
    load_row_map,
    log_missing_ids,
    parse_id_list,
    parse_json_list,
    parse_rows,
    register_cache_clear,
)
from .produce_enums import ProduceEffectType, ProduceResourceType, ProduceStepType
from .sqlite import select_many

_SCHOOL_EVENT_DETAIL_SELECT = """
SELECT
    d.id,
    d.produceStoryId,
    d.produceStoryGroupId,
    d.produceStepEventSuggestionIds,
    ps.title AS storyTitle,
    c.id AS characterId,
    c.lastName || ' ' || c.firstName AS characterName
FROM ProduceStepEventDetail d
LEFT JOIN ProduceStory ps ON ps.id = d.produceStoryId
LEFT JOIN ProduceStoryGroup psg
       ON psg.produceStoryId = d.produceStoryId
      AND d.produceStoryGroupId = ''
LEFT JOIN Character c ON c.id = psg.characterId
WHERE d.eventType = 'ProduceEventType_School'
ORDER BY d.id
""".strip()


class ProduceEffectRow(BaseModel):
    """ProduceEffect 表行。"""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    """培育效果 ID（ProduceEffect.id）。"""
    produce_effect_type: ProduceEffectType = Field(alias='produceEffectType')
    """培育效果类型（ProduceEffect.produceEffectType）。"""
    effect_value_min: int | None = Field(None, alias='effectValueMin')
    """效果数值下限（ProduceEffect.effectValueMin）。"""
    effect_value_max: int | None = Field(None, alias='effectValueMax')
    """效果数值上限（ProduceEffect.effectValueMax）。"""
    produce_resource_type: ProduceResourceType | None = Field(None, alias='produceResourceType')
    """奖励资源类型（ProduceEffect.produceResourceType），用于 ProduceReward 系效果。"""


class ProduceStepEventSuggestionRow(BaseModel):
    """ProduceStepEventSuggestion 表行。"""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    """选项 ID（ProduceStepEventSuggestion.id）。"""
    produce_point: int | None = Field(None, alias='producePoint')
    """制作 P 变动值。"""
    stamina: int | None = None
    """体力变动值。"""
    produce_card_id: str | None = Field(None, alias='produceCardId')
    """关联技能卡 ID（ProduceCard.id）。"""
    produce_card_upgrade_count: int | None = Field(None, alias='produceCardUpgradeCount')
    """关联技能卡强化次数，与 produce_card_id 配套。"""
    produce_effect_ids_raw: str | None = Field(None, alias='produceEffectIds')
    """主效果 ID 列表 JSON（元素为 ProduceEffect.id）。"""
    step_type: ProduceStepType | None = Field(None, alias='stepType')
    """选项确认后跳转的步骤类型（ProduceStepEventSuggestion.stepType）。"""
    step_id: str | None = Field(None, alias='stepId')
    """跳转目标 ID，含义随 step_type 变化：EventActivity 时为 ProduceStepEventDetail.id；授课类为考试步骤标识（如 exam-produce-*），不一定对应单一 DB 表主键。"""
    success_probability_permyriad: int | None = Field(None, alias='successProbabilityPermyriad')
    """成功概率（万分比，10000 = 100%）。"""
    success_produce_effect_ids_raw: str | None = Field(None, alias='successProduceEffectIds')
    """成功时效果 ID 列表 JSON（元素为 ProduceEffect.id）。"""
    success_step_type: ProduceStepType | None = Field(None, alias='successStepType')
    """成功时跳转步骤类型。"""
    success_step_id: str | None = Field(None, alias='successStepId')
    """成功时跳转目标 ID，含义同 step_id。"""
    fail_produce_effect_ids_raw: str | None = Field(None, alias='failProduceEffectIds')
    """失败时效果 ID 列表 JSON（元素为 ProduceEffect.id）。"""
    fail_step_type: ProduceStepType | None = Field(None, alias='failStepType')
    """失败时跳转步骤类型。"""
    fail_step_id: str | None = Field(None, alias='failStepId')
    """失败时跳转目标 ID，含义同 step_id。"""
    always_successful: int | None = Field(None, alias='alwaysSuccessful')
    """是否必定成功（1/0）。"""
    produce_effect_fire_step: int | None = Field(None, alias='produceEffectFireStep')
    """效果触发的培育周数偏移。"""
    is_campaign: int | None = Field(None, alias='isCampaign')
    """是否为活动选项（1/0）。"""
    produce_descriptions: str | None = Field(None, alias='produceDescriptions')
    """选项展示文案 JSON（ProduceDescription 数组）。"""

    @property
    def display_name(self) -> str:
        return _parse_display_name(self.produce_descriptions)

    def main_effect_ids(self) -> list[str]:
        return parse_id_list(
            self.produce_effect_ids_raw,
            context=f'ProduceStepEventSuggestion {self.id}.produceEffectIds',
        )

    def success_effect_ids(self) -> list[str]:
        return parse_id_list(
            self.success_produce_effect_ids_raw,
            context=f'ProduceStepEventSuggestion {self.id}.successProduceEffectIds',
        )

    def fail_effect_ids(self) -> list[str]:
        return parse_id_list(
            self.fail_produce_effect_ids_raw,
            context=f'ProduceStepEventSuggestion {self.id}.failProduceEffectIds',
        )

    def all_effect_ids(self) -> set[str]:
        return set(self.main_effect_ids()) | set(self.success_effect_ids()) | set(self.fail_effect_ids())


class SchoolEventDetailRow(BaseModel):
    """ProduceStepEventDetail 联结查询行（含 ProduceStory / Character）。"""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    """授業事件 ID（ProduceStepEventDetail.id）。"""
    produce_story_id: str | None = Field(None, alias='produceStoryId')
    """关联剧情 ID（ProduceStory.id）。"""
    produce_story_group_id: str | None = Field(None, alias='produceStoryGroupId')
    """关联剧情组 ID（ProduceStoryGroup.id）；非空时不解析角色信息。"""
    produce_step_event_suggestion_ids_raw: str | None = Field(None, alias='produceStepEventSuggestionIds')
    """选项 ID 列表 JSON（元素为 ProduceStepEventSuggestion.id）。"""
    story_title: str | None = Field(None, alias='storyTitle')
    """剧情标题（ProduceStory.title）。"""
    character_id: str | None = Field(None, alias='characterId')
    """角色 ID（Character.id），经 ProduceStoryGroup 联结解析。"""
    character_name: str | None = Field(None, alias='characterName')
    """角色姓名（Character 表拼接）。"""

    def suggestion_ids(self) -> list[str]:
        return parse_id_list(
            self.produce_step_event_suggestion_ids_raw,
            context=f'ProduceStepEventDetail {self.id}.produceStepEventSuggestionIds',
        )

    @property
    def resolved_character_id(self) -> str | None:
        if self.produce_story_group_id:
            return None
        return self.character_id

    @property
    def resolved_character_name(self) -> str | None:
        if self.produce_story_group_id:
            return None
        return self.character_name or None


def _parse_display_name(raw: str | None) -> str:
    if not raw:
        return ''
    for item in parse_json_list(raw):
        if isinstance(item, dict) and item.get('text', '').strip():
            return item['text'].strip()
    return ''


def _resolve_effects(
    effect_ids: list[str],
    effect_map: dict[str, ProduceEffectRow],
    *,
    context: str,
) -> list[ProduceEffectRow]:
    log_missing_ids(context, effect_ids, effect_map)
    return [effect_map[effect_id] for effect_id in effect_ids if effect_id in effect_map]


@dataclass
class SchoolEventOption:
    """授業的单个选项（业务用）。"""
    option_id: str
    """选项 ID（ProduceStepEventSuggestion.id）。"""
    name: str
    """选项展示名称。"""
    stamina: int
    """体力变动值。"""
    produce_point: int
    """制作 P 变动值。"""
    step_type: ProduceStepType | None
    """选项确认后跳转的步骤类型。"""
    step_id: str | None
    """跳转目标 ID，含义随 step_type 变化（见 ProduceStepEventSuggestionRow.step_id）。"""
    is_always_successful: bool
    """是否必定成功。"""
    success_probability: int | None
    """成功概率（万分比）。"""
    effects: list[ProduceEffectRow]
    """主效果列表（ProduceEffect）。"""
    success_effects: list[ProduceEffectRow]
    """成功时效果列表（ProduceEffect）。"""
    fail_effects: list[ProduceEffectRow]
    """失败时效果列表（ProduceEffect）。"""
    success_effect_ids: list[str]
    """成功时效果 ID 列表（ProduceEffect.id）。"""
    fail_effect_ids: list[str]
    """失败时效果 ID 列表（ProduceEffect.id）。"""

    @classmethod
    def from_suggestion(
        cls,
        suggestion: ProduceStepEventSuggestionRow,
        effect_map: dict[str, ProduceEffectRow],
    ) -> 'SchoolEventOption':
        return cls(
            option_id=suggestion.id,
            name=suggestion.display_name,
            stamina=suggestion.stamina or 0,
            produce_point=suggestion.produce_point or 0,
            step_type=suggestion.step_type,
            step_id=suggestion.step_id,
            is_always_successful=bool(suggestion.always_successful),
            success_probability=suggestion.success_probability_permyriad,
            effects=_resolve_effects(
                suggestion.main_effect_ids(),
                effect_map,
                context=f'school event option {suggestion.id} main effects',
            ),
            success_effects=_resolve_effects(
                suggestion.success_effect_ids(),
                effect_map,
                context=f'school event option {suggestion.id} success effects',
            ),
            fail_effects=_resolve_effects(
                suggestion.fail_effect_ids(),
                effect_map,
                context=f'school event option {suggestion.id} fail effects',
            ),
            success_effect_ids=suggestion.success_effect_ids(),
            fail_effect_ids=suggestion.fail_effect_ids(),
        )


@dataclass
class SchoolEvent:
    """授業事件（业务用）。"""
    event_id: str
    """事件 ID（ProduceStepEventDetail.id）。"""
    character_id: str | None
    """角色 ID（Character.id）。"""
    character_name: str | None
    """角色姓名。"""
    story_title: str | None
    """剧情标题（ProduceStory.title）。"""
    options: list[SchoolEventOption]
    """事件选项列表。"""

    @classmethod
    def from_detail(
        cls,
        detail: SchoolEventDetailRow,
        sugg_map: dict[str, ProduceStepEventSuggestionRow],
        effect_map: dict[str, ProduceEffectRow],
    ) -> 'SchoolEvent':
        suggestion_ids = detail.suggestion_ids()
        log_missing_ids(
            f'school event {detail.id} suggestions',
            suggestion_ids,
            sugg_map,
        )
        options = [
            SchoolEventOption.from_suggestion(sugg_map[sugg_id], effect_map)
            for sugg_id in suggestion_ids
            if sugg_id in sugg_map
        ]
        return cls(
            event_id=detail.id,
            character_id=detail.resolved_character_id,
            character_name=detail.resolved_character_name,
            story_title=detail.story_title or None,
            options=options,
        )

    @staticmethod
    def load_all() -> list['SchoolEvent']:
        events, _ = _load_cached()
        return list(events)

    @staticmethod
    def get(event_id: str) -> 'SchoolEvent | None':
        _, index = _load_cached()
        return index.get(event_id)

    @staticmethod
    def for_character(character_id: str) -> list['SchoolEvent']:
        events, _ = _load_cached()
        return [e for e in events if e.character_id == character_id]


def _build_all() -> tuple[tuple[SchoolEvent, ...], dict[str, SchoolEvent]]:
    detail_rows = select_many(f'{_SCHOOL_EVENT_DETAIL_SELECT};')
    if not detail_rows:
        return (), {}

    details = parse_rows(detail_rows, SchoolEventDetailRow)
    sugg_map = load_row_map(
        'ProduceStepEventSuggestion',
        collect_ids(detail_rows, 'produceStepEventSuggestionIds'),
        ProduceStepEventSuggestionRow,
    )
    effect_ids = {effect_id for suggestion in sugg_map.values() for effect_id in suggestion.all_effect_ids()}
    effect_map = load_row_map('ProduceEffect', effect_ids, ProduceEffectRow)

    events = tuple(SchoolEvent.from_detail(detail, sugg_map, effect_map) for detail in details)
    return events, {event.event_id: event for event in events}


@lru_cache(maxsize=1)
def _load_cached() -> tuple[tuple[SchoolEvent, ...], dict[str, SchoolEvent]]:
    return _build_all()


register_cache_clear(_load_cached.cache_clear)