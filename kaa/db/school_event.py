"""
提取所有授業（学園活動）事件数据。
"""
from dataclasses import dataclass
import json
from typing import Any

from .sqlite import select_many


@dataclass
class SchoolEventEffect:
    """授業选项的效果"""
    id: str
    effect_type: str
    effect_value_min: int | None
    effect_value_max: int | None
    resource_type: str | None
    rewards: list[Any]

    @classmethod
    def from_row(cls, row) -> 'SchoolEventEffect':
        rewards_raw = row['produceRewards']
        rewards = json.loads(rewards_raw) if rewards_raw else []
        return cls(
            id=row['id'],
            effect_type=row['produceEffectType'],
            effect_value_min=row['effectValueMin'],
            effect_value_max=row['effectValueMax'],
            resource_type=row['produceResourceType'],
            rewards=rewards,
        )


@dataclass
class SchoolEventOption:
    """授業中的单个选项"""
    id: str
    stamina: int
    produce_point: int
    produce_card_id: str | None
    step_type: str | None
    """选中后跳转到的 step 类型。非 Unknown 表示这是跳转课选项。"""
    step_id: str | None
    """选中后跳转到的 step id"""
    descriptions: list[str]
    """选项文本描述"""
    effects: list[SchoolEventEffect]
    """选项的直接效果列表"""
    always_successful: bool
    success_probability: int | None
    """成功概率（万分比），仅 always_successful=False 时有意义"""
    success_effects: list[str]
    """成功时的效果 id 列表"""
    fail_effects: list[str]
    """失败时的效果 id 列表"""


@dataclass
class SchoolEvent:
    """授業（学園活動）事件"""
    id: str
    story_id: str | None
    """关联的剧情 id (ProduceStory.id)，部分事件直接写群组 id"""
    story_title: str | None
    """剧情标题"""
    story_group_id: str | None
    """关联的剧情群组 id"""
    character_id: str | None
    """所属角色 id"""
    character_name: str | None
    """所属角色全名"""
    options: list[SchoolEventOption]
    """三个选项"""

    @classmethod
    def all(cls) -> list['SchoolEvent']:
        """
        获取所有授業（ProduceEventType_School）事件。
        按 character_id 排序以便分组查看。
        """
        # 1. 加载所有 School event detail
        detail_rows = select_many("""
        SELECT *
        FROM ProduceStepEventDetail
        WHERE eventType = 'ProduceEventType_School'
        ORDER BY id;
        """)

        # 2. 收集所有关联的 suggestion id 和 effect id
        all_sugg_ids: list[str] = []
        all_eff_ids: set[str] = set()
        for dr in detail_rows:
            sids = _parse_id_list(dr['produceStepEventSuggestionIds'])
            all_sugg_ids.extend(sids)
            for eid in _parse_id_list(dr['produceEffectIds']):
                all_eff_ids.add(eid)

        if not all_sugg_ids:
            return []

        # 3. 批量加载 suggestions
        sugg_placeholders = ','.join('?' for _ in all_sugg_ids)
        sugg_rows = select_many(
            f"SELECT * FROM ProduceStepEventSuggestion WHERE id IN ({sugg_placeholders});",
            *all_sugg_ids,
        )
        sugg_map: dict[str, Any] = {}
        for sr in sugg_rows:
            sugg_map[sr['id']] = sr
            for eid in _parse_id_list(sr['produceEffectIds']):
                all_eff_ids.add(eid)
            for eid in _parse_id_list(sr['successProduceEffectIds']):
                all_eff_ids.add(eid)
            for eid in _parse_id_list(sr['failProduceEffectIds']):
                all_eff_ids.add(eid)

        # 4. 批量加载 effects
        eff_map: dict[str, Any] = {}
        if all_eff_ids:
            eff_placeholders = ','.join('?' for _ in all_eff_ids)
            eff_rows = select_many(
                f"SELECT * FROM ProduceEffect WHERE id IN ({eff_placeholders});",
                *all_eff_ids,
            )
            for er in eff_rows:
                eff_map[er['id']] = er

        # 5. 收集 story id 和 character id
        story_ids: set[str] = set()
        char_ids: set[str] = set()
        for dr in detail_rows:
            sid = dr['produceStoryId']
            if sid:
                story_ids.add(sid)
            gid = dr['produceStoryGroupId']
            if gid:
                g_rows = select_many(
                    "SELECT * FROM ProduceStoryGroup WHERE id = ?;", gid
                )
                for gr in g_rows:
                    if gr['produceStoryId']:
                        story_ids.add(gr['produceStoryId'])
                    if gr['characterId']:
                        char_ids.add(gr['characterId'])

        # 6. 批量加载 story groups → 预缓存角色列表
        group_char_map: dict[str, list[str]] = {}
        group_story_map: dict[str, str] = {}  # groupId -> produceStoryId (any)
        story_to_char_map: dict[str, str] = {}  # produceStoryId -> characterId
        all_gids = list({dr['produceStoryGroupId'] for dr in detail_rows if dr['produceStoryGroupId']})
        if all_gids:
            g_placeholders = ','.join('?' for _ in all_gids)
            g_rows = select_many(
                f"SELECT * FROM ProduceStoryGroup WHERE id IN ({g_placeholders});",
                *all_gids,
            )
            for gr in g_rows:
                gid = gr['id']
                if gid not in group_char_map:
                    group_char_map[gid] = []
                group_char_map[gid].append(gr['characterId'])
                if gr['produceStoryId']:
                    group_story_map[gid] = gr['produceStoryId']
                    story_to_char_map[gr['produceStoryId']] = gr['characterId']
                if gr['characterId']:
                    char_ids.add(gr['characterId'])
                if gr['produceStoryId']:
                    story_ids.add(gr['produceStoryId'])

        # 对没有 storyGroupId 但 produceStoryId 的事件，反查角色
        story_ids_no_group = [
            dr['produceStoryId'] for dr in detail_rows
            if dr['produceStoryId'] and not dr['produceStoryGroupId']
            and dr['produceStoryId'] not in story_to_char_map
        ]
        if story_ids_no_group:
            s_placeholders = ','.join('?' for _ in story_ids_no_group)
            g2_rows = select_many(
                f"SELECT * FROM ProduceStoryGroup WHERE produceStoryId IN ({s_placeholders});",
                *story_ids_no_group,
            )
            for gr in g2_rows:
                if gr['produceStoryId']:
                    story_to_char_map[gr['produceStoryId']] = gr['characterId']
                if gr['characterId']:
                    char_ids.add(gr['characterId'])

        # 7. 批量加载 stories
        story_map: dict[str, Any] = {}
        if story_ids:
            s_placeholders = ','.join('?' for _ in story_ids)
            s_rows = select_many(
                f"SELECT * FROM ProduceStory WHERE id IN ({s_placeholders});",
                *story_ids,
            )
            for sr in s_rows:
                story_map[sr['id']] = sr

        # 8. 批量加载 characters
        char_map: dict[str, Any] = {}
        if char_ids:
            c_placeholders = ','.join('?' for _ in char_ids)
            c_rows = select_many(
                f"SELECT * FROM Character WHERE id IN ({c_placeholders});",
                *char_ids,
            )
            for cr in c_rows:
                char_map[cr['id']] = cr

        # 9. 组装
        results: list['SchoolEvent'] = []
        for dr in detail_rows:
            # 确定角色信息
            char_id: str | None = None
            char_name: str | None = None

            gid = dr['produceStoryGroupId']
            if gid:
                # 共享事件（通过 storyGroup 引用多个角色）
                chars = group_char_map.get(gid, [])
                if len(chars) >= 2:
                    # 不绑定到单一角色；保持 char_id=None
                    pass
                elif len(chars) == 1:
                    char_id = chars[0]
            else:
                # 通过 produceStoryId 反查角色
                sid = dr['produceStoryId']
                if sid and sid in story_to_char_map:
                    char_id = story_to_char_map[sid]

            if char_id and char_id in char_map:
                cr = char_map[char_id]
                char_name = f"{cr['lastName']}{cr['firstName']}"

            # 剧情标题
            story_id = dr['produceStoryId']
            story_title: str | None = None
            if story_id and story_id in story_map:
                story_title = story_map[story_id]['title']
            if not story_title and gid and gid in group_story_map:
                psid = group_story_map[gid]
                if psid in story_map:
                    story_title = story_map[psid]['title']

            # 选项
            sugg_ids = _parse_id_list(dr['produceStepEventSuggestionIds'])
            options: list[SchoolEventOption] = []
            for sid in sugg_ids:
                sr = sugg_map.get(sid)
                if sr is None:
                    continue

                descs = _parse_desc_list(sr['produceDescriptions'])
                eff_ids = _parse_id_list(sr['produceEffectIds'])
                effects = [SchoolEventEffect.from_row(eff_map[eid]) for eid in eff_ids if eid in eff_map]

                options.append(SchoolEventOption(
                    id=sr['id'],
                    stamina=sr['stamina'] or 0,
                    produce_point=sr['producePoint'] or 0,
                    produce_card_id=sr['produceCardId'],
                    step_type=sr['stepType'],
                    step_id=sr['stepId'],
                    descriptions=descs,
                    effects=effects,
                    always_successful=bool(sr['alwaysSuccessful']),
                    success_probability=sr['successProbabilityPermyriad'],
                    success_effects=_parse_id_list(sr['successProduceEffectIds']),
                    fail_effects=_parse_id_list(sr['failProduceEffectIds']),
                ))

            results.append(cls(
                id=dr['id'],
                story_id=story_id,
                story_title=story_title,
                story_group_id=gid,
                character_id=char_id,
                character_name=char_name,
                options=options,
            ))

        return results

    @classmethod
    def for_character(cls, character_id: str) -> list['SchoolEvent']:
        """
        获取指定角色的授業事件。
        """
        return [e for e in cls.all() if e.character_id == character_id]


def _parse_id_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return [item for item in data if isinstance(item, str) and item]


def _parse_desc_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    texts = []
    for item in data:
        if isinstance(item, dict):
            t = item.get('text', '')
            if t:
                texts.append(t.strip())
    return texts


if __name__ == '__main__':
    from pprint import pprint as print
    events = SchoolEvent.all()
    print(f"Total: {len(events)}")

    # 显示第一个事件
    e = events[0]
    print(f"\n=== {e.id} ===")
    print(f"  character: {e.character_name} ({e.character_id})")
    print(f"  story: {e.story_title} ({e.story_id})")
    for i, opt in enumerate(e.options, 1):
        print(f"  [{i}] {opt.id}")
        if opt.descriptions:
            print(f"       desc: {' / '.join(opt.descriptions)}")
        if opt.step_type and opt.step_type != 'ProduceStepType_Unknown':
            print(f"       jump: {opt.step_type} -> {opt.step_id}")
        for eff in opt.effects:
            print(f"       effect: {eff.effect_type}({eff.effect_value_min}~{eff.effect_value_max})")
    print(f"Total: {len(events)}")

    # 显示第一个事件
    e = events[0]
    print(f"\n=== {e.id} ===")
    print(f"  character: {e.character_name} ({e.character_id})")
    print(f"  story: {e.story_title} ({e.story_id})")
    for i, opt in enumerate(e.options, 1):
        print(f"  [{i}] {opt.id}")
        if opt.descriptions:
            print(f"       desc: {' / '.join(opt.descriptions)}")
        if opt.step_type and opt.step_type != 'ProduceStepType_Unknown':
            print(f"       jump: {opt.step_type} -> {opt.step_id}")
        for eff in opt.effects:
            print(f"       effect: {eff.effect_type}({eff.effect_value_min}~{eff.effect_value_max})")
