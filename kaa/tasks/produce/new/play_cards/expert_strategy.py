from typing_extensions import override, assert_never

from kotonebot import logging

from .ui import CardGameObject
from .page import LessonBattleContext
from .strategy import AbstractBattleStrategy
from kaa.db.constants import ProduceExamEffectType

logger = logging.getLogger(__name__)

def _default(val: int | None, default: int) -> int:
    return val if val is not None else default

class ExpertSystemStrategy(AbstractBattleStrategy):
    @override
    def on_action(self, ctx: 'LessonBattleContext'):
        hands = ctx.fetch_hands()
        if not hands:
            return
        hands = (h for h in hands if h is not None and h.available)
        hands = filter(lambda c: c.card is not None, hands)
        best_card = max(hands, key=lambda card: self._evaluate_card(ctx, card))
        logger.info('Best card: %s', best_card)
        ctx.commit(best_card)

    def _evaluate_card(self, ctx: 'LessonBattleContext', card: CardGameObject) -> float:
        if not card.card:
            logger.warning('Unrecognized card encountered in expert strategy. %s', card)
            return -9999.0  # 极低分，避免使用未识别的卡片
        
        # ====== 评估消费 ======
        score_cost: float = 0
        card2 = card.card
        # 4点费用以下不扣分，4点费用以上扣（费用-4）分
        # 体力越少，消耗惩罚越大
        if _default(card2.stamina, 0) > 0: # 扣元气
            ratio = _default(ctx.fetch_stamina(), 20) / 20
            weight = 1
        else: # 扣体力
            ratio = _default(ctx.fetch_hp(), 20) / 20
            weight = 2.0 if ratio < 0.3 else 1.0

        cost = card2.stamina or card2.force_stamina or 0
        if cost <= 4:
            score_cost = 0.0  # 4点及以下费用不扣分
        else:
            # 扣分 = -(费用 - 4) * 权重
            score_cost = -(cost - 4) * weight


        # ====== 评估 buff ======
        effects = card.card.play_effects
        score_effects: float = 0.0
        multiplier: float = 1.0 # 分数倍率，不同 buff 在不同阶段权重不同
        stamina = _default(ctx.fetch_stamina(), 20)
        remaining_turns = _default(ctx.fetch_remaining_turns(), 10)
        low_stamina = (stamina / 20) < 0.3
        turn_ratio = (10 - remaining_turns) / 10
        late_stage = turn_ratio < 0.3 # 是否回合后期
        early_stage = turn_ratio > 0.6 # 是否回合前期
        logger.debug(
            'Info: stamina=%.2f, remaining_turns=%d,'
            'stage_type=%s',
            stamina,
            remaining_turns,
            late_stage if late_stage else early_stage,
        )

        for effect in effects:
            produce_effect = effect.produce_exam_effect
            if not produce_effect or not produce_effect.effect_type:
                continue
            
            effect_type = produce_effect.effect_type
            value1 = _default(produce_effect.effect_value1, 0)
            turn = _default(produce_effect.effect_turn, 0)

            match effect_type:
                case ProduceExamEffectType.ExamLesson:
                    score_effects += value1
                    if late_stage:
                        multiplier += 0.15
                case ProduceExamEffectType.ExamBlock:
                    score_effects += value1 * 2
                    if low_stamina:
                        multiplier += 0.2
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamPlayableValueAdd:
                    # 技能卡使用次数追加
                    score_effects += 1000.0
                case ProduceExamEffectType.ExamCardDraw:
                    score_effects += 50.0
                case ProduceExamEffectType.ExamCardUpgrade:
                    score_effects += 20.0
                case ProduceExamEffectType.ExamAntiDebuff:
                    score_effects += 20.0
                case ProduceExamEffectType.ExamDebuffRecover:
                    score_effects += 100.0
                case ProduceExamEffectType.ExamEffectTimer:
                    score_effects += 0.0
                case ProduceExamEffectType.ExamExtraTurn:
                    # 回合追加
                    score_effects += 1000.0
                case ProduceExamEffectType.ExamHandGraveCountCardDraw:
                    score_effects += 1000.0
                case ProduceExamEffectType.ExamLessonValueMultiple:
                    score_effects += 1000.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamSearchPlayCardStaminaConsumptionChange:
                    score_effects += 100.0
                case ProduceExamEffectType.ExamStatusEnchant:
                    score_effects += 100.0
                case ProduceExamEffectType.ExamAddGrowEffect:
                    score_effects += 100.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamCardCreateSearch:
                    score_effects += 100.0
                case ProduceExamEffectType.ExamCardSearchEffectPlayCountBuff:
                    score_effects += 1000.0
                case ProduceExamEffectType.ExamBlockRestriction:
                    score_effects += 0.0
                case ProduceExamEffectType.ExamLessonBuff:
                    # 集中
                    score_effects += value1 * 2
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamLessonAddMultipleLessonBuff:
                    # 集中翻倍
                    score_effects += 1000.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamParameterBuff:
                    # 好调
                    score_effects += turn * 4
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamParameterBuffMultiplePerTurn:
                    # 绝好调
                    score_effects += turn * 10
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamLessonDependParameterBuff:
                    score_effects += 100.0
                    if late_stage:
                        multiplier += 0.15
                case ProduceExamEffectType.ExamMultipleLessonBuffLesson:
                    score_effects += 200.0
                    if late_stage:
                        multiplier += 0.15
                case ProduceExamEffectType.ExamCardPlayAggressive:
                    score_effects += value1 * 2
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamAggressiveValueMultiple:
                    score_effects += 1000.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamReview:
                    score_effects += value1 * 2
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamReviewAdditive:
                    score_effects += 1000.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamReviewValueMultiple:
                    score_effects += 1000.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamBlockAddMultipleAggressive:
                    score_effects += 100.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamBlockPerUseCardCount:
                    score_effects += 100.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamLessonDependExamCardPlayAggressive:
                    score_effects += value1 / 100
                    if late_stage:
                        multiplier += 0.15
                case ProduceExamEffectType.ExamLessonDependBlock:
                    score_effects += value1 / 50
                    if late_stage:
                        multiplier += 0.15
                case ProduceExamEffectType.ExamLessonDependExamReview:
                    score_effects += value1 / 50
                    if late_stage:
                        multiplier += 0.15
                case ProduceExamEffectType.ExamConcentration:
                    score_effects += 100.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamPreservation:
                    score_effects += 200.0
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamFullPowerPoint:
                    score_effects += value1 * 2
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamEnthusiasticAdditive:
                    score_effects += value1 * 2
                    if early_stage:
                        multiplier += 0.1
                case ProduceExamEffectType.ExamLessonFullPowerPoint:
                    score_effects += 100.0
                    if late_stage:
                        multiplier += 0.15
                case ProduceExamEffectType.StanceLock:
                    score_effects += 0.0
                case ProduceExamEffectType.ExamLessonAddMultipleParameterBuff:
                    score_effects += 200.0
                    if late_stage:
                        multiplier += 0.15
                case ProduceExamEffectType.ExamStaminaConsumptionAdd:
                    score_effects += -10.0
                case ProduceExamEffectType.ExamStaminaConsumptionDown:
                    score_effects += turn * 2
                case ProduceExamEffectType.ExamStaminaConsumptionDownFix:
                    score_effects += value1 * 2
                case ProduceExamEffectType.ExamStaminaRecoverFix:
                    score_effects += 10.0
                    if low_stamina:
                        multiplier += 0.2
                case ProduceExamEffectType.ExamStaminaRecoverMultiple:
                    score_effects += 10.0
                    if low_stamina:
                        multiplier += 0.2
                case ProduceExamEffectType.ExamAggressiveAdditive | ProduceExamEffectType.ExamAggressiveReduce | ProduceExamEffectType.ExamBlockAddDown | ProduceExamEffectType.ExamBlockDependExamReview | ProduceExamEffectType.ExamBlockDown | ProduceExamEffectType.ExamBlockFix | ProduceExamEffectType.ExamBlockValueMultiple | ProduceExamEffectType.ExamCardCreateId | ProduceExamEffectType.ExamCardDuplicate | ProduceExamEffectType.ExamCardMove | ProduceExamEffectType.ExamEnthusiasticMultiple | ProduceExamEffectType.ExamForcePlayCardSearch | ProduceExamEffectType.ExamFullPower | ProduceExamEffectType.ExamFullPowerPointAdditive | ProduceExamEffectType.ExamFullPowerPointReduce | ProduceExamEffectType.ExamGimmickLessonDebuff | ProduceExamEffectType.ExamGimmickParameterDebuff | ProduceExamEffectType.ExamGimmickPlayCardLimit | ProduceExamEffectType.ExamGimmickSleepy | ProduceExamEffectType.ExamGimmickSlump | ProduceExamEffectType.ExamGimmickStartTurnCardDrawDown | ProduceExamEffectType.ExamItemFireLimitAdd | ProduceExamEffectType.ExamLessonBuffAdditive | ProduceExamEffectType.ExamLessonBuffDependParameterBuff | ProduceExamEffectType.ExamLessonBuffMultiple | ProduceExamEffectType.ExamLessonBuffReduce | ProduceExamEffectType.ExamLessonDependPlayCardCountSum | ProduceExamEffectType.ExamLessonDependStaminaConsumptionSum | ProduceExamEffectType.ExamLessonFix | ProduceExamEffectType.ExamLessonPerSearchCount | ProduceExamEffectType.ExamLessonValueMultipleDependReviewOrAggressive | ProduceExamEffectType.ExamLessonValueMultipleDown | ProduceExamEffectType.ExamOverPreservation | ProduceExamEffectType.ExamPanic | ProduceExamEffectType.ExamParameterBuffAdditive | ProduceExamEffectType.ExamParameterBuffDependLessonBuff | ProduceExamEffectType.ExamParameterBuffReduce | ProduceExamEffectType.ExamReviewDependExamBlock | ProduceExamEffectType.ExamReviewDependExamCardPlayAggressive | ProduceExamEffectType.ExamReviewMultiple | ProduceExamEffectType.ExamReviewPerSearchCount | ProduceExamEffectType.ExamReviewReduce | ProduceExamEffectType.ExamStaminaConsumptionAddFix | ProduceExamEffectType.ExamStaminaDamage | ProduceExamEffectType.ExamStaminaRecoverRestriction | ProduceExamEffectType.ExamStaminaReduceFix | ProduceExamEffectType.ExamStaminaReduce | ProduceExamEffectType.ExamStanceReset:
                    score_effects += 0.0
                case _:
                    assert_never(effect_type)

        score = score_effects * multiplier + score_cost
        logger.debug('Evaluated card %s: effects_score=%.2f, cost_score=%.2f, total_score=%.2f', card.card.name, score_effects, score_cost, score)
        return score
