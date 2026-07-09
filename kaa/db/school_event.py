"""
授業（学園活動）数据库实体类。
严格对应 ProduceStepEventDetail / ProduceStepEventSuggestion / ProduceEffect 表结构。
"""
from dataclasses import dataclass
import json
from typing import Any

from .sqlite import select_many


@dataclass
class ProduceEffectRow:
    """ProduceEffect 表"""
    id: str
    produceEffectType: str
    effectValueMin: int | None
    effectValueMax: int | None
    produceResourceType: str | None
    produceRewards: str | None
    produceCardSearchId: str | None
    produceExamStatusEnchantId: str | None
    produceStepEventDetailId: str | None
    pickRangeType: str | None
    pickCountMin: int | None
    pickCountMax: int | None
    isResearch: int | None


@dataclass
class ProduceStepEventSuggestionRow:
    """ProduceStepEventSuggestion 表"""
    id: str
    producePoint: int | None
    stamina: int | None
    produceCardId: str | None
    produceCardUpgradeCount: int | None
    produceEffectIds: str | None
    stepType: str | None
    stepId: str | None
    successProbabilityPermyriad: int | None
    successProduceEffectIds: str | None
    successStepType: str | None
    successStepId: str | None
    failProduceEffectIds: str | None
    failStepType: str | None
    failStepId: str | None
    alwaysSuccessful: int | None
    produceEffectFireStep: int | None
    isCampaign: int | None
    produceDescriptions: str | None

    @property
    def display_name(self) -> str:
        """选项显示名称：produceDescriptions 的第一条 PlainText"""
        return _parse_display_name(self.produceDescriptions)


@dataclass
class ProduceStepEventDetailRow:
    """ProduceStepEventDetail 表。
    仅筛选 eventType = 'ProduceEventType_School' 的记录。
    """
    id: str
    suggestionType: str | None
    produceStoryId: str | None
    produceStoryGroupId: str | None
    produceEffectIds: str | None
    produceStepEventSuggestionIds: str | None
    supportCardId: str | None
    eventType: str | None
    eventCharacterType: str | None
    isBusinessExcellent: int | None
    produceDescriptions: str | None
    # 解析后的便捷字段
    characterId: str | None
    characterName: str | None
    storyTitle: str | None
    suggestions: list['ProduceStepEventSuggestionRow']

    @classmethod
    def all_school_events(cls) -> list['ProduceStepEventDetailRow']:
        """获取所有授業（ProduceEventType_School）事件。"""
        detail_rows = select_many("""
        SELECT *
        FROM ProduceStepEventDetail
        WHERE eventType = 'ProduceEventType_School'
        ORDER BY id;
        """)

        if not detail_rows:
            return []

        # 全表拉取 ProduceStepEventSuggestion
        all_sugg_rows = select_many("SELECT * FROM ProduceStepEventSuggestion;")
        sugg_map: dict[str, Any] = {sr['id']: sr for sr in all_sugg_rows}

        # 全表拉取 ProduceStoryGroup → 建立映射
        all_group_rows = select_many("SELECT * FROM ProduceStoryGroup;")
        story_to_char: dict[str, str] = {}
        for gr in all_group_rows:
            if gr['produceStoryId']:
                story_to_char[gr['produceStoryId']] = gr['characterId']

        # 全表拉取 Character
        all_char_rows = select_many("SELECT * FROM Character;")
        char_names: dict[str, str] = {}
        for cr in all_char_rows:
            char_names[cr['id']] = f"{cr['lastName']}{cr['firstName']}"

        # 全表拉取 ProduceStory
        all_story_rows = select_many("SELECT id, title FROM ProduceStory;")
        story_titles: dict[str, str] = {sr['id']: sr['title'] or '' for sr in all_story_rows}

        # 组装结果
        results: list['ProduceStepEventDetailRow'] = []
        for dr in detail_rows:
            gid = dr['produceStoryGroupId']
            sid = dr['produceStoryId']

            # 确定角色
            char_id = None
            if gid:
                pass  # 共享事件，不绑定单一角色
            elif sid and sid in story_to_char:
                char_id = story_to_char[sid]

            # 剧情标题
            story_title = story_titles.get(sid or '')

            # 解析 suggestions
            sugg_ids = _parse_id_list(dr['produceStepEventSuggestionIds'])
            suggestions = []
            for sid2 in sugg_ids:
                sr = sugg_map.get(sid2)
                if sr:
                    suggestions.append(ProduceStepEventSuggestionRow(
                        id=sr['id'],
                        producePoint=sr['producePoint'],
                        stamina=sr['stamina'],
                        produceCardId=sr['produceCardId'],
                        produceCardUpgradeCount=sr['produceCardUpgradeCount'],
                        produceEffectIds=sr['produceEffectIds'],
                        stepType=sr['stepType'],
                        stepId=sr['stepId'],
                        successProbabilityPermyriad=sr['successProbabilityPermyriad'],
                        successProduceEffectIds=sr['successProduceEffectIds'],
                        successStepType=sr['successStepType'],
                        successStepId=sr['successStepId'],
                        failProduceEffectIds=sr['failProduceEffectIds'],
                        failStepType=sr['failStepType'],
                        failStepId=sr['failStepId'],
                        alwaysSuccessful=sr['alwaysSuccessful'],
                        produceEffectFireStep=sr['produceEffectFireStep'],
                        isCampaign=sr['isCampaign'],
                        produceDescriptions=sr['produceDescriptions'],
                    ))

            results.append(cls(
                id=dr['id'],
                suggestionType=dr['suggestionType'],
                produceStoryId=sid,
                produceStoryGroupId=gid,
                produceEffectIds=dr['produceEffectIds'],
                produceStepEventSuggestionIds=dr['produceStepEventSuggestionIds'],
                supportCardId=dr['supportCardId'],
                eventType=dr['eventType'],
                eventCharacterType=dr['eventCharacterType'],
                isBusinessExcellent=dr['isBusinessExcellent'],
                produceDescriptions=dr['produceDescriptions'],
                characterId=char_id,
                characterName=char_names.get(char_id or ''),
                storyTitle=story_title,
                suggestions=suggestions,
            ))

        return results


def _parse_id_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return [item for item in data if isinstance(item, str) and item]


def _parse_display_name(raw: str | None) -> str:
    """从 produceDescriptions JSON 中提取第一条 PlainText 作为显示名称。"""
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ""
    for item in data:
        if isinstance(item, dict) and item.get('text', '').strip():
            return item['text'].strip()
    return ""


# ─── 业务专用领域类 ─────────────────────────────────────────────

@dataclass
class SchoolEventEffect:
    """授業选项的一个效果"""
    effect_id: str
    effect_type: str
    value_min: int | None
    value_max: int | None
    resource_type: str | None

    @classmethod
    def from_raw(cls, effect_id: str, rows: dict[str, Any]) -> 'SchoolEventEffect | None':
        r = rows.get(effect_id)
        if r is None:
            return None
        return cls(
            effect_id=r['id'],
            effect_type=r['produceEffectType'],
            value_min=r['effectValueMin'],
            value_max=r['effectValueMax'],
            resource_type=r['produceResourceType'],
        )


@dataclass
class SchoolEventOption:
    """授業的单个选项"""
    option_id: str
    name: str
    """选项名称（produceDescriptions 第一条）"""
    stamina: int
    produce_point: int
    step_type: str | None
    """非 Unknown 时表示跳转上课"""
    step_id: str | None
    is_always_successful: bool
    success_probability: int | None
    """成功概率（万分比）"""
    effects: list[SchoolEventEffect]
    """直属效果列表"""
    success_effect_ids: list[str]
    """成功时触发的效果 id"""
    fail_effect_ids: list[str]
    """失败时触发的效果 id"""


@dataclass
class SchoolEvent:
    """授業事件（业务用）"""
    event_id: str
    character_id: str | None
    character_name: str | None
    story_title: str | None
    options: list[SchoolEventOption]

    @staticmethod
    def load_all() -> list['SchoolEvent']:
        """加载所有授業事件，返回业务专用对象。"""
        details = ProduceStepEventDetailRow.all_school_events()

        all_eff_rows = select_many("SELECT * FROM ProduceEffect;")
        eff_map: dict[str, Any] = {er['id']: er for er in all_eff_rows}

        results: list['SchoolEvent'] = []
        for d in details:
            options = []
            for s in d.suggestions:
                eff_ids = _parse_id_list(s.produceEffectIds)
                effects = []
                for eid in eff_ids:
                    eff = SchoolEventEffect.from_raw(eid, eff_map)
                    if eff:
                        effects.append(eff)
                options.append(SchoolEventOption(
                    option_id=s.id,
                    name=s.display_name,
                    stamina=s.stamina or 0,
                    produce_point=s.producePoint or 0,
                    step_type=s.stepType,
                    step_id=s.stepId,
                    is_always_successful=bool(s.alwaysSuccessful),
                    success_probability=s.successProbabilityPermyriad,
                    effects=effects,
                    success_effect_ids=_parse_id_list(s.successProduceEffectIds),
                    fail_effect_ids=_parse_id_list(s.failProduceEffectIds),
                ))
            results.append(SchoolEvent(
                event_id=d.id,
                character_id=d.characterId,
                character_name=d.characterName,
                story_title=d.storyTitle,
                options=options,
            ))

        return results

    @staticmethod
    def for_character(character_id: str) -> list['SchoolEvent']:
        """按角色筛选。"""
        return [e for e in SchoolEvent.load_all() if e.character_id == character_id]
