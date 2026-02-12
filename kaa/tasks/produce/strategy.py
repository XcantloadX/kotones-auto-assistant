from typing import TYPE_CHECKING, Literal

from kaa.tasks.produce.in_purodyuusu import produce_end
from kaa.tasks.produce.play_cards.bandai_strategy import BandaiStrategy
from kotonebot import logging, sleep, device, Loop
from kotonebot.core import AnyOf
from kotonebot.errors import UnrecoverableError

from kaa.tasks import R
from kaa.tasks.produce.cards import CardDetectResult, do_cards
from kaa.tasks.produce.play_cards.expert_strategy import ExpertSystemStrategy
from kaa.kaa_context import produce_solution
from kaa.config.const import ProduceAction, RecommendCardDetectionMode
from kaa.tasks.produce.common import ProduceInterrupt, acquisition_date_change_dialog
from kaa.tasks.actions.commu import handle_unread_commu

from .consts import Scene, SceneType
if TYPE_CHECKING:
    from .page import (
        DrinkSelectContext, ActionSelectContext,
        PracticeContext, ExamContext, CardSelectContext, PItemSelectContext,
        StudyContext, OutingContext, ConsultContext, AllowanceContext,
        SkillCardEnhanceContext, SkillCardRemovalContext,
        PDrinkMaxContext, PDrinkMaxConfirmContext, NetworkErrorContext, DateChangeContext,
    )
    from .controller import ProduceController

logger = logging.getLogger(__name__)

def _lesson_to_sp(lesson: ProduceAction | None) -> ProduceAction | None:
    match lesson:
        case ProduceAction.VISUAL:
            return ProduceAction.VISUAL_SP
        case ProduceAction.VOCAL:
            return ProduceAction.VOCAL_SP
        case ProduceAction.DANCE:
            return ProduceAction.DANCE_SP
        case _:
            return None

class StandardStrategy:
    def __init__(self, controller: 'ProduceController') -> None:
        self.controller = controller
        self.page = controller.page

    def on_study(self, ctx: 'StudyContext'):
        if ctx.is_self_study():
            logger.info("授業 type: Self study.")
            lesson = produce_solution().data.self_study_lesson
            ctx.commit_self_study(lesson)
            logger.info(f"Committed {lesson}.")
        else:
            logger.info("授業 type: Normal.")
            options = ctx.fetch_options()
            # 选中 +30 的选项
            target_btn = next((btn for btn in options if '+30' in btn.description), None)
            if target_btn is None:
                logger.error("Failed to find +30 option. Pick the second button instead.")
                target_btn = options[1]
            logger.debug('Picking "%s".', target_btn.description)
            ctx.commit(options.index(target_btn))

    def on_outing(self, ctx: 'OutingContext'):
        # 固定选中第二个选项
        # TODO: 可能需要二次处理外出事件
        options = ctx.fetch_options()
        target_index = min(1, len(options) - 1)
        ctx.commit(target_index)

    def on_consult(self, ctx: 'ConsultContext'):
        ctx.commit()

    def on_allowance(self, ctx: 'AllowanceContext'):
        ctx.claim()

    def on_pdrink_max(self, ctx: 'PDrinkMaxContext'):
        """处理 P饮料到达上限弹窗"""
        ProduceInterrupt._check_pdrink_max(device.screenshot())

    def on_pdrink_max_confirm(self, ctx: 'PDrinkMaxConfirmContext'):
        """处理 P饮料到达上限确认弹窗"""
        ProduceInterrupt._check_pdrink_max_confirm(device.screenshot())

    def on_network_error(self, ctx: 'NetworkErrorContext'):
        """处理网络错误弹窗"""
        ProduceInterrupt._check_network_error(device.screenshot())

    def on_date_change(self, ctx: 'DateChangeContext'):
        """处理日期变更弹窗（确认后自动回到培育内）"""
        result = acquisition_date_change_dialog()
        if result is None:
            logger.warning("DATE_CHANGE scene detected but acquisition_date_change_dialog returned None.")

    def try_handle_commu(self, img) -> bool:
        """处理交流"""
        if produce_solution().data.skip_commu and handle_unread_commu(img):
            return True
        return False

    def on_select_drink(self, ctx: 'DrinkSelectContext'):
        """选择饮料"""
        data = ctx.fetch_select_drink()
        if data.can_skip:
            ctx.commit(data, None)
        else:
            # 默认选择第一个饮料
            ctx.commit(data, data.drinks[0])

    def on_select_card(self, ctx: 'CardSelectContext'):
        """选择技能卡"""
        card_idx = ctx.fetch_recommend_card()
        if card_idx is None:
            ctx.commit(0)
        else:
            ctx.commit(card_idx)

    def on_select_pitem(self, ctx: 'PItemSelectContext'):
        """选择P道具"""
        ctx.commit(0)

    def on_skill_card_enhance(self, ctx: 'SkillCardEnhanceContext'):
        """技能卡自选强化"""
        ctx.commit(0)

    def on_skill_card_removal(self, ctx: 'SkillCardRemovalContext'):
        """技能卡自选删除"""
        ctx.commit(0)

    def on_action_select(self, ctx: 'ActionSelectContext'):
        recommend = ctx.fetch_sensei_tip()
        availables = ctx.fetch_available_actions()[0]

        # 首先处理优先 SP
        # 如果优先 SP，
        if produce_solution().data.prefer_lesson_ap and ctx.has_sp_lesson():
            # 1. 推荐行动是休息，则休息
            if recommend == ProduceAction.REST:
                ctx.commit(ProduceAction.REST)
                return
            
            # 2. 推荐行动是 SP 课程，则执行推荐行动
            sp = _lesson_to_sp(recommend)
            if sp and sp in availables:
                ctx.commit(sp)
                return

            # 3. 推荐行动是其他，优先选择 current/max < 0.8 的 SP 课程
            metrics = ctx.fetch_perf_metrics()
            for m in metrics:
                sp_lesson = _lesson_to_sp(m.lesson)
                if m.current / m.max < 0.8 and sp_lesson in availables:
                    ctx.commit(sp_lesson)
                    return

            # 4. 如果都 > 0.8，则选择 current 最小的课程
            min_metric = min(metrics, key=lambda x: x.current)
            ctx.commit(min_metric.lesson)
            return

        # 如果有推荐行动，优先推荐
        if recommend:
            ctx.commit(recommend)
            return
        
        # 否则按照配置里的顺序来
        configured_actions = produce_solution().data.actions_order
        for ac in configured_actions:
            for available in availables:
                if ac == available:
                    ctx.commit(available)
                    return

        raise UnrecoverableError("No available actions to execute.")

    def on_practice_entered(self, ctx: 'PracticeContext'):
        logger.info("Practice started")
        # TODO: 目前练习和考试的实现都不符合数据解析/模拟输入、决策分析这两者分离的写法，后续需要重构
        def threshold_predicate(card_count: int, result: CardDetectResult):
            border_scores = (result.left_score, result.right_score, result.top_score, result.bottom_score)
            is_strict_mode = produce_solution().data.recommend_card_detection_mode == RecommendCardDetectionMode.STRICT
            if is_strict_mode:
                return (
                    result.score >= 0.043
                    and len(list(filter(lambda x: x >= 0.04, border_scores))) >= 3
                )
            else:
                return result.score >= 0.03
            # is_strict_mode 见下方 exam() 中解释
            # 严格模式下区别：
            # 提高平均阈值，且同时要求至少有 3 边达到阈值。

        def end_predicate():
            return not AnyOf[
                R.InPurodyuusu.TextClearUntil,
                R.InPurodyuusu.TextPerfectUntil
            ].exists()
    
        # do_cards(False, threshold_predicate, end_predicate, battle_strategy=BandaiStrategy(threshold_predicate))
        do_cards(False, threshold_predicate, end_predicate, battle_strategy=ExpertSystemStrategy())

    def on_practice_exited(self):
        pass

    def on_practice_tick(self, ctx: 'PracticeContext'):
        pass

    def on_exam(self, ctx: 'ExamContext'):
        pass

    def on_exam_entered(self, ctx: 'ExamContext'):
        type: Literal['mid', 'final'] = 'final'
        if ctx.is_final_exam():
            type = 'final'
        else:
            type = 'mid'
        logger.info(f"Exam type detected: {type}.")

        def threshold_predicate(card_count: int, result: CardDetectResult):
            is_strict_mode = produce_solution().data.recommend_card_detection_mode == RecommendCardDetectionMode.STRICT
            total = lambda t: result.score >= t  # noqa: E731
            def borders(t):
                # 卡片数量小于三时无遮挡，以及最后一张卡片也总是无遮挡
                if card_count <= 3 or (result.type == card_count - 1):
                    return (
                        result.left_score >= t
                        and result.right_score >= t
                        and result.top_score >= t
                        and result.bottom_score >= t
                    )
                # 其他情况下，卡片的右侧会被挡住，并不会发光
                else:
                    return (
                        result.left_score >= t
                        and result.top_score >= t
                        and result.bottom_score >= t
                    )

            if is_strict_mode:
                if type == 'final':
                    return total(0.4) and borders(0.2)
                else:
                    return total(0.10) and borders(0.01)
            else:
                if type == 'final':
                    if result.type == 10: # SKIP
                        return total(0.4) and borders(0.02)
                    else:
                        return total(0.15) and borders(0.02)
                else:
                    return total(0.10) and borders(0.01)

            # 关于上面阈值的解释：
            # 所有阈值均指卡片周围的“黄色度”，
            # score 指卡片四边的平均黄色度阈值，
            # left_score、right_score、top_score、bottom_score 指卡片每边的黄色度阈值

            # 为什么期中和期末考试阈值不一样：
            # 期末考试的场景为黄昏，背景中含有大量黄色，
            # 非常容易对推荐卡的检测造成干扰。
            # 解决方法是提高平均阈值的同时，为每一边都设置阈值。
            # 这样可以筛选出只有四边都包含黄色的发光卡片，
            # 而由夕阳背景造成的假发光卡片通常不会四边都包含黄色。

            # 为什么需要严格模式：
            # 严格模式主要用于琴音。琴音的服饰上有大量黄色元素，
            # 很容易干扰检测，因此需要针对琴音专门调整阈值。
            # 主要变化是给每一边都设置了阈值。

        from kotonebot import ocr, contains
        def end_predicate():
            return bool(
                not ocr.find(contains('残りターン'), rect=R.InPurodyuusu.BoxExamTop)
                and R.Common.ButtonNext.find()
            )

        # do_cards(True, threshold_predicate, end_predicate, battle_strategy=BandaiStrategy(threshold_predicate))
        do_cards(True, threshold_predicate, end_predicate, battle_strategy=ExpertSystemStrategy())

        R.Common.ButtonNext.wait().click()

        is_exam_passed = True

        # 如果考试失败
        sleep(1) # 避免在动画未播放完毕时点击
        if btn := R.InPurodyuusu.TextRechallengeEndProduce.try_wait(timeout=3):
            logger.info('Exam failed, end produce.')
            device.click(btn)
            is_exam_passed = False

        if type == 'final':
            for _ in Loop():
                if ocr.wait_for(contains("メモリー"), timeout=7):
                    device.click_center()
                else:
                    break
            
            produce_end(has_live=is_exam_passed)
            self.controller.abort()
        else:
            if not is_exam_passed:
                produce_end(has_live=False)
                self.controller.abort()