from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from kaa.db.constants import (
    ExamCostType,
    ProduceCardCategory,
    ProduceCardRarity,
    ProduceDescriptionType,
    ProduceExamEffectType,
    ProducePlanType,
)
from kaa.db.skill_card import SkillCard
from kaa.game_data.paths import skill_card_path

from . import assets
from .tokens import Break, Buff, Highlight, Text, Token, serialize


@dataclass
class SkillCardView:
    card: SkillCard

    # ── 描述文本分词 ──────────────────────────────────────────────

    @cached_property
    def effect_display_text(self) -> str:
        return self._segments_to_plain(self.description_segments)

    @cached_property
    def description_segments(self) -> list[Token]:
        raw = self.card.produce_descriptions
        if not raw:
            return []
        try:
            data: list[dict[str, Any]] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
        return self._parse_description_segments(data)

    @staticmethod
    def _clean_desc_text(text: str) -> str:
        return (text or '').replace('</nobr>', '').replace('<nobr>', '')

    @classmethod
    def _segments_to_plain(cls, tokens: list[Token]) -> str:
        parts: list[str] = []
        for t in tokens:
            if isinstance(t, Break):
                parts.append('\n')
            else:
                parts.append(t.text or '')
        return ''.join(parts).strip()

    @classmethod
    def _has_line_content(cls, tokens: list[Token]) -> bool:
        for t in reversed(tokens):
            if isinstance(t, Break):
                return False
            if t.text or isinstance(t, Buff):
                return True
        return False

    @classmethod
    def _append_break(cls, tokens: list[Token]) -> None:
        if tokens and isinstance(tokens[-1], Break):
            return
        tokens.append(Break())

    @classmethod
    def _append_text_tokens(cls, tokens: list[Token], text: str, *, kind: type[Token] | None = None, **extra: Any) -> None:
        if not text:
            return
        if '\n' not in text:
            cls._push_token(tokens, text, kind=kind, **extra)
            return
        for i, part in enumerate(text.split('\n')):
            if i > 0:
                cls._append_break(tokens)
            if part:
                cls._push_token(tokens, part, kind=kind, **extra)

    @classmethod
    def _push_token(cls, tokens: list[Token], text: str, *, kind: type[Token] | None = None, **extra: Any) -> None:
        if kind is Highlight:
            tokens.append(Highlight(text=text, tone=extra.get('tone', 'desc')))
        elif kind is Buff:
            tokens.append(Buff(text=text, **extra))
        else:
            tokens.append(Text(text=text))

    @classmethod
    def _parse_description_segments(cls, data: list[dict[str, Any]]) -> list[Token]:
        tokens: list[Token] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            dtype = str(item.get('produceDescriptionType') or '')
            dtype_short = ProduceDescriptionType.short(dtype)
            text = cls._clean_desc_text(str(item.get('text') or ''))
            change_color = bool(item.get('changeColor'))
            target_id = str(item.get('targetId') or '')

            if dtype_short == 'ProduceDescriptionName' and target_id == 'Label_StyleDot':
                cls._append_break(tokens)
                continue

            if dtype_short == 'ProduceExamEffectType':
                et = str(item.get('examEffectType') or '')
                et_name = ProduceExamEffectType.short(et)
                if et_name and et_name != 'Unknown':
                    icon = assets.exam_effect_icon_path(et_name)
                    bg = assets.buff_bg_for_effect(et_name)
                    tokens.append(Buff(text=text, icon=icon, bg=bg, effectName=et_name))
                    continue
                cls._append_text_tokens(tokens, text)
                continue

            if dtype_short == 'ProduceCardGrowEffectType':
                grow = str(item.get('produceCardGrowEffectType') or '')
                grow_name = grow.removeprefix('ProduceCardGrowEffectType_')
                if grow_name == 'CostAdd':
                    tokens.append(Buff(text=text, icon='', bg='', stamina=True, effectName='CostAdd'))
                    continue
                mapped = assets._GROW_EFFECT_ICON_MAP.get(grow_name)
                if mapped:
                    icon = assets.exam_effect_icon_path(mapped.name)
                    bg = assets.buff_bg_for_effect(mapped.name)
                    tokens.append(Buff(text=text, icon=icon, bg=bg, effectName=mapped.name))
                    continue
                cls._append_text_tokens(tokens, text)
                continue

            if dtype_short == 'ProduceDescription':
                if text and cls._has_line_content(tokens):
                    cls._append_break(tokens)
                cls._append_text_tokens(tokens, text, kind=Highlight, tone='desc')
                continue

            if change_color or dtype_short == 'ProduceCard':
                cls._append_text_tokens(tokens, text, kind=Highlight, tone='card')
                continue

            cls._append_text_tokens(tokens, text)

        while tokens and isinstance(tokens[0], Break):
            tokens.pop(0)
        while tokens and isinstance(tokens[-1], Break):
            tokens.pop()
        return tokens

    # ── 渲染属性 ──────────────────────────────────────────────────

    @staticmethod
    def _effect_name(et: ProduceExamEffectType | str | None) -> str:
        if et is None:
            return ''
        if isinstance(et, ProduceExamEffectType):
            return et.name
        return ProduceExamEffectType.short(str(et))

    def asset_path(self, character: str | None = None) -> str:
        card = self.card
        char = character
        if char is None and card.is_character_asset:
            char = 'kllj'
        return skill_card_path(card._asset_id or '', character=char)

    @property
    def frame_path(self) -> str:
        return assets.card_frame(self.card.category, self.card.rarity)

    @cached_property
    def block_value(self) -> int | None:
        for ef in self.card.play_effects:
            if not ef.produce_exam_effect:
                continue
            et = ef.produce_exam_effect.effect_type
            if et in (ProduceExamEffectType.ExamBlock,
                      ProduceExamEffectType.ExamBlockAddMultipleAggressive):
                return ef.produce_exam_effect.effect_value1
        return None

    @cached_property
    def lesson_value(self) -> int | None:
        for ef in self.card.play_effects:
            if not ef.produce_exam_effect:
                continue
            if ef.produce_exam_effect.effect_type == ProduceExamEffectType.ExamLesson \
               and not ef._produce_exam_trigger_id:
                return ef.produce_exam_effect.effect_value1
        return None

    @cached_property
    def lesson_multiplier(self) -> int | None:
        for ef in self.card.play_effects:
            if not ef.produce_exam_effect:
                continue
            if ef.produce_exam_effect.effect_type == ProduceExamEffectType.ExamLesson \
               and not ef._produce_exam_trigger_id:
                c = ef.produce_exam_effect.effect_count
                return c if c and c > 1 else None
        return None

    @cached_property
    def cost_stamina(self) -> int | None:
        if self.card.force_stamina:
            return self.card.force_stamina
        return self.card.stamina

    @cached_property
    def is_red_stamina(self) -> bool:
        return bool(self.card.force_stamina)

    @cached_property
    def cost_type_effect_name(self) -> str:
        ct = self.card.cost_type or ''
        if not ct or ct.endswith('_Unknown') or ct == 'Unknown':
            return ''
        return ExamCostType.short(ct)

    @cached_property
    def display_effect_types(self) -> list[str]:
        result: list[str] = []
        block_count = 0
        for ef in self.card.play_effects:
            if not ef.produce_exam_effect:
                continue
            if ef.hide_icon:
                continue
            et = ef.produce_exam_effect.effect_type
            if not et:
                continue
            et_name = self._effect_name(et)
            if et == ProduceExamEffectType.ExamLesson:
                if not ef._produce_exam_trigger_id:
                    continue
            elif et == ProduceExamEffectType.ExamBlock:
                block_count += 1
                if block_count < 2:
                    continue
            elif et in (
                ProduceExamEffectType.ExamBlockPerUseCardCount,
                ProduceExamEffectType.ExamBlockAddMultipleAggressive,
            ):
                continue
            result.append(et_name)
        if self.card._produce_card_status_enchant_id:
            result.append('ExamAddGrowEffect')
        return list(reversed(result))

    def to_index_dict(self) -> dict:
        return {
            'id': self.card._id,
            'name': self.card.name,
            'rarity': ProduceCardRarity.short(self.card.rarity),
            'category': ProduceCardCategory.short(self.card.category),
            'planType': ProducePlanType.short(self.card.plan_type),
            'upgradeCount': self.card.upgrade_count or 0,
            'effectText': self.effect_display_text,
            'evaluation': self.card.evaluation or 0,
            'evaluationLabel': self.card.evaluation_label,
            'unlockLevel': self.card.unlock_producer_level or 0,
            'libraryHidden': self.card.library_hidden,
        }

    def to_render_dict(self) -> dict:
        effect_icons = []
        for name in self.display_effect_types:
            icon = assets.exam_effect_icon_path(name)
            bg = assets.buff_bg_for_effect(name)
            if icon:
                effect_icons.append({'name': name, 'icon': icon, 'bg': bg})

        cost_type_name = self.cost_type_effect_name
        cost_type_icon = ''
        cost_type_bg = ''
        if cost_type_name:
            cost_type_icon = assets.exam_effect_icon_path(cost_type_name)
            cost_type_bg = assets.buff_bg_for_effect(cost_type_name)

        return {
            'id': self.card._id,
            'name': self.card.name,
            'rarity': ProduceCardRarity.short(self.card.rarity),
            'category': ProduceCardCategory.short(self.card.category),
            'planType': ProducePlanType.short(self.card.plan_type),
            'assetPath': self.asset_path(),
            'isCharacterAsset': self.card.is_character_asset,
            'framePath': self.frame_path,
            'costStamina': self.cost_stamina or 0,
            'isRedStamina': self.is_red_stamina,
            'costTypeName': cost_type_name,
            'costTypeIcon': cost_type_icon,
            'costTypeBg': cost_type_bg,
            'costValue': self.card.cost_value or 0,
            'lessonValue': self.lesson_value or 0,
            'lessonMultiplier': self.lesson_multiplier or 0,
            'blockValue': self.block_value if self.block_value is not None else -1,
            'upgradeCount': self.card.upgrade_count or 0,
            'effectIcons': effect_icons,
            'effectText': self.effect_display_text,
            'descriptionSegments': serialize(self.description_segments),
            'evaluation': self.card.evaluation or 0,
            'evaluationLabel': self.card.evaluation_label,
            'unlockLevel': self.card.unlock_producer_level or 0,
            'originIdol': self.card._origin_idol_card_id or '',
            'originSupport': self.card._origin_support_card_id or '',
            'libraryHidden': self.card.library_hidden,
        }
