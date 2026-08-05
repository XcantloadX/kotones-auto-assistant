from kaa.db.produce_enums import ProduceEffectType, ProduceResourceType, ProduceStepType
from kaa.db.school_event import ProduceEffectRow, ProduceStepEventSuggestionRow


def test_produce_effect_row_parses_enums():
    row = ProduceEffectRow.model_validate({
        'id': 'p_effect-vocal_addition-0040_0040',
        'produceEffectType': 'ProduceEffectType_VocalAddition',
        'effectValueMin': 40,
        'effectValueMax': 40,
        'produceResourceType': 'ProduceResourceType_Unknown',
    })
    assert row.produce_effect_type is ProduceEffectType.VocalAddition
    assert row.produce_resource_type is ProduceResourceType.Unknown


def test_produce_step_event_suggestion_row_parses_enums():
    row = ProduceStepEventSuggestionRow.model_validate({
        'id': 'test-suggestion',
        'stepType': 'ProduceStepType_LessonVocalNormal',
        'successStepType': 'ProduceStepType_EventActivity',
        'failStepType': 'ProduceStepType_Unknown',
    })
    assert row.step_type is ProduceStepType.LessonVocalNormal
    assert row.success_step_type is ProduceStepType.EventActivity
    assert row.fail_step_type is ProduceStepType.Unknown