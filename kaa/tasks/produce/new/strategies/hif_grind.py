"""标准培育策略实现。

:class:`StandardStrategy` 是开箱即用的默认培育策略，实现了
:class:`~kaa.tasks.produce.new.strategies.base.ProduceStrategy` 定义的全部钩子，
覆盖授業、外出、考试、行动选择等常规场景的决策逻辑。
"""

from typing import TYPE_CHECKING
from typing_extensions import override

from kotonebot import logging, sleep, device, Loop
from kotonebot.errors import UnrecoverableError

from kaa.tasks import R
from kaa.tasks.produce.shared.cards import SKIP_CARD_BUTTON
from kaa.kaa_context import produce_solution
from kaa.config.const import ProduceAction
from kaa.tasks.produce.shared.common import ProduceInterrupt, acquisition_date_change_dialog
from kaa.tasks.actions.commu import handle_unread_commu

from .base import HifProduceStrategy

if TYPE_CHECKING:
    from ..page import (
        DrinkSelectContext, ActionSelectContext,
        PracticeContext, ExamContext, CardSelectContext, PItemSelectContext,
        StudyContext, OutingContext, ConsultContext, AllowanceContext,
        SkillCardEnhanceContext, SkillCardRemovalContext,
        PDrinkMaxContext, PDrinkMaxConfirmContext, DateChangeContext,
        HifRoundIntervalContext, SkillCardChangeContext
    )
    from ..controller import ProduceController

logger = logging.getLogger(__name__)


class HifGrindStrategy(HifProduceStrategy):
    """
    Hif 正赛弃赛刷奖励。

    培育中会尽可能跳过所有周，两次 Round 也会跳过全部回合。
    """

    def __init__(self, controller: 'ProduceController') -> None:
        super().__init__(controller)

    def on_study(self, ctx: 'StudyContext'):
        ctx.commit(0)

    def on_outing(self, ctx: 'OutingContext'):
        ctx.commit(0)

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
        options = ctx.fetch_cards()
        ctx.commit(options[0])

    def on_select_pitem(self, ctx: 'PItemSelectContext'):
        """选择P道具"""
        ctx.commit(0)

    def on_skill_card_enhance(self, ctx: 'SkillCardEnhanceContext'):
        """技能卡自选强化"""
        ctx.commit(0)

    def on_skill_card_removal(self, ctx: 'SkillCardRemovalContext'):
        """技能卡自选删除"""
        ctx.commit(0)
    
    @override
    def on_skill_card_change(self, ctx: 'SkillCardChangeContext'):
        if ctx.stage == 1:
            ctx.commit_stage1(0)
        ctx.commit_stage2(0)

    @override
    def on_hif_round_interval(self, ctx: 'HifRoundIntervalContext'):
        """HIF 两轮 Round 之间的中场休息"""
        ctx.end()

    def on_action_select(self, ctx: 'ActionSelectContext'):
        # 行动选择页在切页动画期间可能出现按钮尚未渲染完成的瞬时状态，
        # 此时 fetch_available_actions() 会返回空列表。为避免误判为不可恢复错误
        # 直接中断整个培育任务，无可用行动时等待 1s 后重试（最多 5 次）；
        # 连续多次仍无可用行动才真正抛出异常。
        for attempt in range(5):
            availables = ctx.fetch_available_actions()[0]

            # 优先级：
            # 休息 > 差し入れ > 课程 > 授業 > 相談
            orders = [
                ProduceAction.REST,
                ProduceAction.GIFT,
                ProduceAction.VISUAL_SP,
                ProduceAction.VOCAL_SP,
                ProduceAction.DANCE_SP,
                ProduceAction.STUDY_VISUAL_HIF,
                ProduceAction.STUDY_VOCAL_HIF,
                ProduceAction.STUDY_DANCE_HIF,
                ProduceAction.CONSULT
            ]
            for action in orders:
                if action in availables:
                    ctx.commit(action)
                    return

            # 无可用行动：等待 1s 后重试（覆盖切页动画等瞬时状态）
            if attempt < 4:
                logger.warning(
                    "No available actions to execute. Waiting 1s and retrying... (%d/5)",
                    attempt + 1,
                )
                sleep(1)
                device.screenshot()
                continue
            break

        raise UnrecoverableError("No available actions to execute.")

    def on_practice_entered(self, ctx: 'PracticeContext'):
        logger.error("Practice scene detected. This should not be in HIF.")

    def on_practice_exited(self):
        pass

    def on_exam_entered(self, ctx: 'ExamContext'):
        from kotonebot import ocr, contains

        for _ in Loop():
            if bool(
                not ocr.find(contains('残りターン'), rect=R.InProduce.BoxExamTop)
                and R.Common.ButtonNext.find()
            ):
                break
            elif R.Common.ButtonIconCheckMark.try_click():
                logger.info("Confirmation dialog detected")
                continue
            else:
                skip_btn_rect = SKIP_CARD_BUTTON
                x, y, w, h = skip_btn_rect.x, skip_btn_rect.y, skip_btn_rect.w, skip_btn_rect.h
                device.click(x + w // 2, y + h // 2)

        for _ in Loop():
            if R.Common.ButtonNext.try_click():
                logger.info("Exam next button clicked.")
                sleep(2)
            elif R.InProduce.TextRechallengeEndProduce.try_click():
                logger.info("Exam failed, end produce clicked.")
                sleep(2)
            else:
                break