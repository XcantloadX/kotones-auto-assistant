"""DebugInspectorController — QB 桥接，供 QML 查看游戏数据库原始数据。"""

import json
import logging
import threading

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)


class DebugInspectorController(QObject):
    schoolEventListReady = Signal(str)
    schoolEventDetailReady = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    # ── SchoolEvent ───────────────────────────────────────────────

    @Slot()
    def loadSchoolEventListAsync(self) -> None:
        threading.Thread(target=self._load_school_event_list, daemon=True).start()

    def _load_school_event_list(self) -> None:
        try:
            from kaa.db.school_event import SchoolEvent
            events = SchoolEvent.load_all()
            data = [
                {
                    'id': e.event_id,
                    'story_title': e.story_title,
                    'character_name': e.character_name,
                    'character_id': e.character_id,
                    'option_count': len(e.options),
                }
                for e in events
            ]
            self.schoolEventListReady.emit(json.dumps(data, ensure_ascii=False))
        except Exception:
            logger.exception("Failed to load school event list")
            self.schoolEventListReady.emit(json.dumps({'error': '加载失败，请查看日志'}, ensure_ascii=False))

    @Slot(str)
    def loadSchoolEventDetailAsync(self, event_id: str) -> None:
        threading.Thread(target=self._load_school_event_detail, args=(event_id,), daemon=True).start()

    def _load_school_event_detail(self, event_id: str) -> None:
        try:
            from kaa.db.school_event import SchoolEvent
            event = SchoolEvent.get(event_id)
            if event is None:
                self.schoolEventDetailReady.emit(json.dumps({'error': f'未找到事件: {event_id}'}, ensure_ascii=False))
                return
            data = _event_to_dict(event)
            self.schoolEventDetailReady.emit(json.dumps(data, ensure_ascii=False))
        except Exception:
            logger.exception("Failed to load school event detail")
            self.schoolEventDetailReady.emit(json.dumps({'error': '加载详情失败，请查看日志'}, ensure_ascii=False))


def _event_to_dict(e) -> dict:
    return {
        'id': e.event_id,
        'story_title': e.story_title,
        'character_id': e.character_id,
        'character_name': e.character_name,
        'options': [_option_to_dict(o) for o in e.options],
    }


def _option_to_dict(o) -> dict:
    return {
        'id': o.option_id,
        'name': o.name,
        'stamina': o.stamina,
        'produce_point': o.produce_point,
        'step_type': o.step_type,
        'step_id': o.step_id,
        'is_always_successful': o.is_always_successful,
        'success_probability': o.success_probability,
        'success_effect_ids': o.success_effect_ids,
        'fail_effect_ids': o.fail_effect_ids,
        'effects': [_effect_to_dict(ef) for ef in o.effects],
        'success_effects': [_effect_to_dict(ef) for ef in o.success_effects],
        'fail_effects': [_effect_to_dict(ef) for ef in o.fail_effects],
    }


_EFFECT_TYPE_LABELS: dict[str, str] = {
    'VocalAddition': 'Vo',
    'DanceAddition': 'Da',
    'VisualAddition': 'Vi',
    'VocalGrowthRateAddition': 'Vo成长率',
    'DanceGrowthRateAddition': 'Da成长率',
    'VisualGrowthRateAddition': 'Vi成长率',
    'StarAddition': '星',
    'StarPermilUp': '星出现率',
    'ParameterLimitUp': '参数上限',
    'HighScoreGoldAddition': '金',
    'StaminaRecoverFix': '体力回复',
    'StaminaRecoverMultiple': '体力回复',
    'StaminaReduceFix': '体力减少',
    'MaxStaminaAddition': '最大体力',
    'MaxStaminaReduceFix': '最大体力',
    'BeforeAuditionRefreshStaminaUp': '试镜前体力回复',
    'BeforeAuditionRefreshStaminaDown': '试镜前体力减少',
    'EventSchoolStaminaUp': '授業体力回复',
    'EventSchoolStaminaDown': '授業体力减少',
    'ProducePointAddition': 'SP',
    'ProducePointAdditionDisableTrigger': 'SP(不可触发)',
    'ProducePointReduceFix': 'SP',
    'EventActivityProducePointUp': '活动SP',
    'EventActivityProducePointDown': '活动SP',
    'CustomizeProduceCardProducePointDownMultiple': '自定义卡SP折扣',
    'LessonPresentProducePointUp': '授课礼物SP',
    'ProduceCardChange': '替换卡片',
    'ProduceCardChangeSelect': '选择替换卡片',
    'ProduceCardChangeUpgrade': '替换为强化版',
    'ProduceCardDelete': '删除卡片',
    'ProduceCardDuplicate': '复制卡片',
    'ProduceCardUpgrade': '强化卡片',
    'ProduceCardExcludeCountUp': '除外栏位',
    'ProduceCardSelectRerollCountUp': '卡牌重roll次数',
    'IdolCardProduceCardCustomizeEnable': '自定义偶像卡',
    'ProduceCustomizeItemUpgrade': '升级自定义物品',
    'ProduceDrinkPossessLimitUp': '饮料持有上限',
    'AuditionVoteCountUp': '试镜得票率',
    'AuditionParameterBonusMultiple': '试镜参数倍率',
    'AuditionNpcEnhance': '试镜对手强化',
    'AuditionNpcWeaken': '试镜对手弱化',
    'EventBusinessVoteCountUp': '营业得票率',
    'VoteCountAddition': '票数',
    'ExamTurnDown': '考试回合减少',
    'ExamStatusEnchant': '考试附魔',
    'ExamPermanentAuditionStatusEnchant': '考试试镜附魔(常驻)',
    'ExamPermanentLessonStatusEnchant': '考试授课附魔(常驻)',
    'LessonSpChangeRatePermilAddition': '授课SP倍率',
    'LessonDanceSpChangeRatePermilAddition': '授课DaSP倍率',
    'LessonVocalSpChangeRatePermilAddition': '授课VoSP倍率',
    'LessonVisualSpChangeRatePermilAddition': '授课ViSP倍率',
    'LessonPresentProduceCardRewardCountUp': '授课礼物卡牌数',
    'ProduceReward': '获得物品',
    'ProduceRewardSet': '选择物品',
    'ShopProduceCardPriceDiscountMultiple': '商店卡牌折扣',
    'ShopProduceCardPriceDiscountMultiplePermanent': '商店卡牌折扣(常驻)',
    'ShopProduceCardUpgradePriceDiscountMultiple': '卡牌强化折扣',
    'ShopProduceCardDeletePriceDiscountMultiple': '卡牌删除折扣',
    'ShopProduceDrinkPriceDiscountMultiple': '商店饮料折扣',
    'ShopPriceDiscountMultiple': '商店折扣',
    'ShopPriceUpMultiple': '商店涨价',
    'ShopRerollCountUp': '商店重roll次数',
    'SupportCardProduceCardUpgradeProbabilityUp': '支援卡强化概率',
    'SupportCardEventParameterAdditionValueUp': '支援事件参数倍率',
    'SupportCardEventProducePointAdditionValueUp': '支援事件SP倍率',
    'SupportCardEventStaminaRecoverUp': '支援事件体力回复',
}

_RESOURCE_LABELS: dict[str, str] = {
    'ProduceResourceType_ProduceCard': '卡牌',
    'ProduceResourceType_ProduceDrink': '饮料',
    'ProduceResourceType_ProduceItem': '物品',
    'ProduceResourceType_ProduceCustomizeItem': '自定义物品',
}


def _effect_display_text(ef) -> str:
    label = _EFFECT_TYPE_LABELS.get(ef.produce_effect_type, ef.produce_effect_type)

    vmin = ef.effect_value_min
    vmax = ef.effect_value_max

    # Enchant effects — the value is the enchant id
    if ef.produce_effect_type in ('ExamStatusEnchant', 'ExamPermanentAuditionStatusEnchant', 'ExamPermanentLessonStatusEnchant'):
        return f"{label} ({ef.id})"

    # Reward effects — show resource type
    if ef.produce_effect_type in ('ProduceReward', 'ProduceRewardSet'):
        rsrc = _RESOURCE_LABELS.get(ef.produce_resource_type, ef.produce_resource_type or '?')
        return f"{label}({rsrc}) ({ef.id})"

    # Card manipulation — show search scope
    if ef.produce_effect_type in ('ProduceCardChange', 'ProduceCardChangeSelect', 'ProduceCardChangeUpgrade',
                          'ProduceCardDelete', 'ProduceCardDuplicate', 'ProduceCardUpgrade'):
        return f"{label} ({ef.id})"

    # Percentage values (permil → percent)
    if ef.produce_effect_type in (
        'AuditionVoteCountUp', 'AuditionParameterBonusMultiple', 'StarPermilUp',
        'ShopProduceCardPriceDiscountMultiple', 'ShopProduceCardPriceDiscountMultiplePermanent',
        'ShopProduceCardUpgradePriceDiscountMultiple', 'ShopProduceCardDeletePriceDiscountMultiple',
        'ShopProduceDrinkPriceDiscountMultiple', 'ShopPriceDiscountMultiple', 'ShopPriceUpMultiple',
        'CustomizeProduceCardProducePointDownMultiple',
        'StaminaRecoverMultiple',
        'EventSchoolStaminaUp', 'EventSchoolStaminaDown',
        'BeforeAuditionRefreshStaminaUp', 'BeforeAuditionRefreshStaminaDown',
        'LessonSpChangeRatePermilAddition',
        'LessonDanceSpChangeRatePermilAddition',
        'LessonVocalSpChangeRatePermilAddition',
        'LessonVisualSpChangeRatePermilAddition',
        'SupportCardProduceCardUpgradeProbabilityUp',
        'SupportCardEventParameterAdditionValueUp',
        'SupportCardEventProducePointAdditionValueUp',
        'SupportCardEventStaminaRecoverUp',
    ):
        if vmin is not None and vmin == vmax:
            return f"{label} +{vmin/10:.0f}% ({ef.id})"
        elif vmin is not None and vmax is not None:
            return f"{label} +{vmin/10:.0f}~{vmax/10:.0f}% ({ef.id})"
        return f"{label} ({ef.id})"

    # Growth rates (1-100 permil = 0.1%-10%)
    if ef.produce_effect_type in ('VocalGrowthRateAddition', 'DanceGrowthRateAddition', 'VisualGrowthRateAddition'):
        if vmin is not None and vmin == vmax:
            return f"{label} +{vmin/10:.1f}% ({ef.id})"
        elif vmin is not None and vmax is not None:
            return f"{label} +{vmin/10:.1f}~{vmax/10:.1f}% ({ef.id})"
        return f"{label} ({ef.id})"

    # Npc enhance/weaken (permil)
    if ef.produce_effect_type in ('AuditionNpcEnhance', 'AuditionNpcWeaken'):
        if vmin is not None and vmin == vmax:
            return f"{label} {vmin/10:.0f}% ({ef.id})"
        return f"{label} ({ef.id})"

    # Fixed integer values
    if vmin is not None and vmin == vmax:
        return f"{label} +{vmin} ({ef.id})"
    elif vmin is not None and vmax is not None:
        return f"{label} +{vmin}~{vmax} ({ef.id})"

    # Fallback
    return f"{label} ({ef.id})"


def _effect_to_dict(ef) -> dict:
    return {
        'id': ef.id,
        'effect_type': ef.produce_effect_type,
        'effect_value_min': ef.effect_value_min,
        'effect_value_max': ef.effect_value_max,
        'resource_type': ef.produce_resource_type,
        'display': _effect_display_text(ef),
    }
