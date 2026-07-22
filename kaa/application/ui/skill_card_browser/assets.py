"""UI 静态资产路径 + 合并的查找表。

图片来源：
- kaa/application/ui/assets/skill_card/ui/          — 边框、buff 背景、数字位图、体力/护盾图标
- kaa/application/ui/assets/skill_card/exam_effects/ — 考试效果图标
"""
from functools import lru_cache
from pathlib import Path
from typing import TypeAlias

from kaa.db.constants import ProduceExamEffectType

PEETType: TypeAlias = ProduceExamEffectType
PEET = ProduceExamEffectType

_UI_ASSETS = Path(__file__).resolve().parent.parent / 'assets' / 'skill_card'


def ui_dir() -> Path:
    return _UI_ASSETS / 'ui'


def exam_effects_dir() -> Path:
    return _UI_ASSETS / 'exam_effects'


def _abs(p: Path) -> str:
    return str(p.resolve()).replace('\\', '/')


@lru_cache(maxsize=256)
def ui_path(name: str) -> str:
    return _abs(ui_dir() / name)


@lru_cache(maxsize=256)
def exam_effect_icon_path(effect_name: str) -> str:
    try:
        et = ProduceExamEffectType[effect_name]
    except KeyError:
        return ''
    mapped = _EXTRA_EFFECT_NAME_MAP.get(et, et)
    fname = f'exam_{mapped.name.lower()}.webp'
    p = exam_effects_dir() / fname
    if p.exists():
        return _abs(p)
    return ''


@lru_cache(maxsize=64)
def card_frame(category: str | None, rarity: str | None) -> str:
    cat = (category or '').removeprefix('ProduceCardCategory_')
    rar = (rarity or '').removeprefix('ProduceCardRarity_').lower()

    if cat == 'Trouble':
        return ui_path('card_frame_t.webp')

    prefix = 'card_frame_a' if cat == 'ActiveSkill' else 'card_frame_m'
    if rar == 'legend':
        return ui_path(f'{prefix}_lr.webp')
    if rar == 'ssr':
        return ui_path(f'{prefix}_ssr.webp')
    if rar == 'sr':
        return ui_path(f'{prefix}_sr.webp')
    if rar == 'r':
        return ui_path(f'{prefix}_r.webp')
    return ui_path(f'{prefix}_n.webp')


STAMINA_ICON = ui_path('icon_stamina.webp')
STAMINA_RED_ICON = ui_path('icon_stamina_red.webp')
BLOCK_ICON = ui_path('icon_block.webp')
ENHANCED_ICON = ui_path('icon_enhanced.webp')
NUMBER_MINUS = ui_path('ef_txt_minus.webp')
MULTIPLIER = ui_path('text_multiplier.webp')


def number_digit_path(digit: str) -> str:
    if digit == '-':
        return NUMBER_MINUS
    if digit == 'x':
        return MULTIPLIER
    if digit.isdigit():
        return ui_path(f'ef_txt_special_{digit}_before.webp')
    return ''


_BUFF_BG = {
    'blue': 'buff_bg_blue.webp',
    'yellow': 'buff_bg_yellow.webp',
    'red': 'buff_bg_red.webp',
    'green': 'buff_bg_green.webp',
    'concentration': 'buff_base_concentration.webp',
    'fullpower': 'buff_base_fullpower.webp',
    'preservation': 'buff_base_preservation.webp',
    'overpreservation': 'buff_base_overpreservation.webp',
}


@lru_cache(maxsize=32)
def buff_bg_path(color_key: str) -> str:
    name = _BUFF_BG.get(color_key, 'buff_bg_yellow.webp')
    return ui_path(name)


_BUFF_TYPE_BG: dict[PEETType, str] = {
    PEET.ExamLesson: 'blue',
    PEET.ExamParameterBuff: 'blue',
    PEET.ExamBlock: 'blue',
    PEET.ExamCardDraw: 'blue',
    PEET.ExamStaminaConsumptionDown: 'blue',
    PEET.ExamCardCreateId: 'yellow',
    PEET.ExamStaminaReduceFix: 'red',
    PEET.ExamCardMove: 'yellow',
    PEET.ExamLessonBuff: 'blue',
    PEET.ExamCardUpgrade: 'blue',
    PEET.ExamBlockValueMultiple: 'blue',
    PEET.ExamPlayableValueAdd: 'blue',
    PEET.ExamLessonBuffMultiple: 'blue',
    PEET.ExamBlockRestriction: 'red',
    PEET.ExamLessonDependBlock: 'blue',
    PEET.ExamCardCreateSearch: 'yellow',
    PEET.ExamStatusEnchant: 'yellow',
    PEET.ExamMultipleLessonBuffLesson: 'blue',
    PEET.ExamForcePlayCardSearch: 'blue',
    PEET.ExamStaminaDamage: 'red',
    PEET.ExamStaminaRecoverFix: 'blue',
    PEET.ExamCardDuplicate: 'blue',
    PEET.ExamReview: 'blue',
    PEET.ExamReviewValueMultiple: 'blue',
    PEET.ExamCardSearchEffectPlayCountBuff: 'blue',
    PEET.ExamLessonValueMultiple: 'blue',
    PEET.ExamCardPlayAggressive: 'blue',
    PEET.ExamConcentration: 'concentration',
    PEET.ExamPreservation: 'preservation',
    PEET.ExamFullPower: 'fullpower',
    PEET.ExamStanceReset: 'yellow',
    PEET.ExamFullPowerPoint: 'blue',
    PEET.ExamExtraTurn: 'blue',
    PEET.ExamAntiDebuff: 'blue',
    PEET.ExamStaminaConsumptionAdd: 'red',
    PEET.ExamBlockAddDown: 'red',
    PEET.ExamPanic: 'red',
    PEET.ExamStaminaConsumptionAddFix: 'red',
    PEET.ExamStaminaRecoverRestriction: 'red',
    PEET.ExamHandGraveCountCardDraw: 'yellow',
    PEET.ExamEffectTimer: 'blue',
    PEET.ExamGimmickLessonDebuff: 'red',
    PEET.ExamGimmickParameterDebuff: 'red',
    PEET.ExamGimmickSleepy: 'red',
    PEET.ExamGimmickPlayCardLimit: 'red',
    PEET.ExamGimmickSlump: 'red',
    PEET.ExamGimmickStartTurnCardDrawDown: 'red',
    PEET.ExamStaminaRecoverMultiple: 'blue',
    PEET.ExamBlockFix: 'blue',
    PEET.ExamLessonAddMultipleLessonBuff: 'blue',
    PEET.ExamBlockDown: 'red',
    PEET.ExamLessonDependExamReview: 'blue',
    PEET.ExamLessonDependExamCardPlayAggressive: 'blue',
    PEET.ExamParameterBuffMultiplePerTurn: 'blue',
    PEET.ExamLessonBuffDependParameterBuff: 'blue',
    PEET.ExamLessonDependParameterBuff: 'blue',
    PEET.StanceLock: 'red',
    PEET.ExamBlockAddMultipleAggressive: 'blue',
    PEET.ExamDebuffRecover: 'blue',
    PEET.ExamAggressiveValueMultiple: 'blue',
    PEET.ExamItemFireLimitAdd: 'red',
    PEET.ExamReviewReduce: 'red',
    PEET.ExamAggressiveReduce: 'red',
    PEET.ExamLessonBuffReduce: 'red',
    PEET.ExamParameterBuffReduce: 'red',
    PEET.ExamLessonValueMultipleDown: 'red',
    PEET.ExamAddGrowEffect: 'green',
    PEET.ExamOverPreservation: 'overpreservation',
    PEET.ExamEnthusiasticAdditive: 'blue',
    PEET.ExamEnthusiasticMultiple: 'blue',
    PEET.ExamFullPowerPointAdditive: 'blue',
    PEET.ExamLessonBuffAdditive: 'blue',
    PEET.ExamParameterBuffAdditive: 'blue',
    PEET.ExamAggressiveAdditive: 'blue',
    PEET.ExamReviewAdditive: 'blue',
    PEET.ExamReviewMultiple: 'blue',
    PEET.ExamSearchPlayCardStaminaConsumptionChange: 'blue',
    PEET.ExamStaminaConsumptionDownFix: 'blue',
    PEET.ExamLessonValueMultipleDependReviewOrAggressive: 'blue',
}


@lru_cache(maxsize=256)
def buff_bg_for_effect(effect_name: str) -> str:
    try:
        et = ProduceExamEffectType[effect_name]
    except KeyError:
        return buff_bg_path('yellow')
    key = _BUFF_TYPE_BG.get(et, 'yellow')
    return buff_bg_path(key)


_EXTRA_EFFECT_NAME_MAP: dict[PEETType, PEETType] = {
    PEET.ExamCardDraw: PEET.ExamCardCreateId,
    PEET.ExamStaminaReduceFix: PEET.ExamStaminaRecoverFix,
    PEET.ExamCardUpgrade: PEET.ExamCardCreateId,
    PEET.ExamLessonDependBlock: PEET.ExamLesson,
    PEET.ExamCardCreateSearch: PEET.ExamCardCreateId,
    PEET.ExamMultipleLessonBuffLesson: PEET.ExamLesson,
    PEET.ExamStaminaConsumptionAdd: PEET.ExamStaminaConsumptionDown,
    PEET.ExamHandGraveCountCardDraw: PEET.ExamCardCreateId,
    PEET.ExamBlockFix: PEET.ExamBlock,
    PEET.ExamLessonDependExamReview: PEET.ExamLesson,
    PEET.ExamLessonDependExamCardPlayAggressive: PEET.ExamLesson,
    PEET.ExamLessonDependParameterBuff: PEET.ExamLesson,
    PEET.ExamReviewReduce: PEET.ExamReview,
    PEET.ExamAggressiveReduce: PEET.ExamCardPlayAggressive,
    PEET.ExamLessonBuffReduce: PEET.ExamLessonBuff,
    PEET.ExamParameterBuffReduce: PEET.ExamParameterBuff,
    PEET.ExamCardMove: PEET.ExamCardCreateId,
    PEET.ExamStaminaRecoverMultiple: PEET.ExamStaminaRecoverFix,
    PEET.ExamLessonFullPowerPoint: PEET.ExamLesson,
    PEET.ExamBlockValueMultiple: PEET.ExamBlock,
    PEET.ExamReviewValueMultiple: PEET.ExamReview,
    PEET.ExamLessonValueMultiple: PEET.ExamLesson,
    PEET.ExamAggressiveValueMultiple: PEET.ExamCardPlayAggressive,
    PEET.ExamLessonAddMultipleLessonBuff: PEET.ExamLessonBuff,
    PEET.ExamReviewPerSearchCount: PEET.ExamReview,
    PEET.ExamLessonBuffDependParameterBuff: PEET.ExamLessonBuff,
    PEET.ExamLessonDependStamina: PEET.ExamLesson,
    PEET.ExamLessonDependPlayCardCountSum: PEET.ExamLesson,
}


def static_icons_json() -> dict[str, str]:
    return {
        'stamina': STAMINA_ICON,
        'staminaRed': STAMINA_RED_ICON,
        'block': BLOCK_ICON,
        'enhanced': ENHANCED_ICON,
        'minus': NUMBER_MINUS,
        'multiplier': MULTIPLIER,
        **{f'digit{i}': ui_path(f'ef_txt_special_{i}_before.webp') for i in range(10)},
    }


# ProduceCardGrowEffectType → 对应 ProduceExamEffectType 枚举
_GROW_EFFECT_ICON_MAP: dict[str, PEET] = {
    'LessonAdd': PEET.ExamLesson,
    'LessonReduce': PEET.ExamLesson,
    'LessonCountAdd': PEET.ExamLesson,
    'LessonCountReduce': PEET.ExamLesson,
    'BlockAdd': PEET.ExamBlock,
    'BlockReduce': PEET.ExamBlock,
    'FullPowerPointAdd': PEET.ExamFullPowerPoint,
    'FullPowerPointReduce': PEET.ExamFullPowerPoint,
    'LessonBuffAdd': PEET.ExamLessonBuff,
    'LessonBuffReduce': PEET.ExamLessonBuff,
    'ReviewAdd': PEET.ExamReview,
    'ReviewReduce': PEET.ExamReview,
    'AggressiveAdd': PEET.ExamCardPlayAggressive,
    'AggressiveReduce': PEET.ExamCardPlayAggressive,
    'CardDrawAdd': PEET.ExamCardCreateId,
    'CardDrawReduce': PEET.ExamCardCreateId,
    'LessonDependBlockAdd': PEET.ExamLesson,
    'LessonDependExamCardPlayAggressiveAdd': PEET.ExamLesson,
    'LessonDependExamReviewAdd': PEET.ExamLesson,
}
