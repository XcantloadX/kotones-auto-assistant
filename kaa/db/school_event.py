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
    model_config = ConfigDict(populate_by_name=True)

    id: str
    produce_effect_type: str = Field(alias='produceEffectType')
    effect_value_min: int | None = Field(None, alias='effectValueMin')
    effect_value_max: int | None = Field(None, alias='effectValueMax')
    produce_resource_type: str | None = Field(None, alias='produceResourceType')


class ProduceStepEventSuggestionRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    produce_point: int | None = Field(None, alias='producePoint')
    stamina: int | None = None
    produce_card_id: str | None = Field(None, alias='produceCardId')
    produce_card_upgrade_count: int | None = Field(None, alias='produceCardUpgradeCount')
    produce_effect_ids_raw: str | None = Field(None, alias='produceEffectIds')
    step_type: str | None = Field(None, alias='stepType')
    step_id: str | None = Field(None, alias='stepId')
    success_probability_permyriad: int | None = Field(None, alias='successProbabilityPermyriad')
    success_produce_effect_ids_raw: str | None = Field(None, alias='successProduceEffectIds')
    success_step_type: str | None = Field(None, alias='successStepType')
    success_step_id: str | None = Field(None, alias='successStepId')
    fail_produce_effect_ids_raw: str | None = Field(None, alias='failProduceEffectIds')
    fail_step_type: str | None = Field(None, alias='failStepType')
    fail_step_id: str | None = Field(None, alias='failStepId')
    always_successful: int | None = Field(None, alias='alwaysSuccessful')
    produce_effect_fire_step: int | None = Field(None, alias='produceEffectFireStep')
    is_campaign: int | None = Field(None, alias='isCampaign')
    produce_descriptions: str | None = Field(None, alias='produceDescriptions')

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
    model_config = ConfigDict(populate_by_name=True)

    id: str
    produce_story_id: str | None = Field(None, alias='produceStoryId')
    produce_story_group_id: str | None = Field(None, alias='produceStoryGroupId')
    produce_step_event_suggestion_ids_raw: str | None = Field(None, alias='produceStepEventSuggestionIds')
    story_title: str | None = Field(None, alias='storyTitle')
    character_id: str | None = Field(None, alias='characterId')
    character_name: str | None = Field(None, alias='characterName')

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
    """授業的单个选项"""
    option_id: str
    name: str
    stamina: int
    produce_point: int
    step_type: str | None
    step_id: str | None
    is_always_successful: bool
    success_probability: int | None
    effects: list[ProduceEffectRow]
    success_effects: list[ProduceEffectRow]
    fail_effects: list[ProduceEffectRow]
    success_effect_ids: list[str]
    fail_effect_ids: list[str]

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
    """授業事件（业务用）"""
    event_id: str
    character_id: str | None
    character_name: str | None
    story_title: str | None
    options: list[SchoolEventOption]

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