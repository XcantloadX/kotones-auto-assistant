"""培育流程策略抽象基类。

策略（Strategy）负责对培育流程中各个场景（授業、外出、考试、行动选择等）
做出决策并驱动 Controller 执行。不同策略可继承 :class:`ProduceStrategy`
并覆盖相应钩子方法，以实现不同的培育自动化逻辑。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from kaa.tasks.actions.scenes import at_home
from kotonebot import logging, Loop, device, sleep

from kaa.kaa_context import produce_solution
from kaa.tasks.actions.commu import handle_unread_commu
from kaa.tasks import R

if TYPE_CHECKING:
    from ..page import (
        DrinkSelectContext, ActionSelectContext,
        PracticeContext, ExamContext, CardSelectContext, PItemSelectContext,
        StudyContext, OutingContext, ConsultContext, AllowanceContext,
        SkillCardEnhanceContext, SkillCardRemovalContext,
        PDrinkMaxContext, PDrinkMaxConfirmContext, DateChangeContext,
        SkillCardChangeContext, HifRoundIntervalContext, ProduceEndContext
    )
    from ..controller import ProduceController

logger = logging.getLogger(__name__)

class ProduceStrategy(ABC):
    """培育流程策略抽象基类。

    定义所有培育策略必须（或可选）实现的钩子方法。Controller 在识别到对应场景后
    会调用相应钩子，由具体策略决定如何操作。
    """

    def __init__(self, controller: 'ProduceController') -> None:
        self.controller = controller
        self.page = controller.page

    @abstractmethod
    def on_study(self, ctx: 'StudyContext'):
        """处理授業场景的决策。"""

    @abstractmethod
    def on_action_select(self, ctx: 'ActionSelectContext'):
        """处理行动选择页的决策。"""

    @abstractmethod
    def on_practice_entered(self, ctx: 'PracticeContext'):
        """处理进入练习战后的流程。"""

    @abstractmethod
    def on_exam_entered(self, ctx: 'ExamContext'):
        """处理进入考试后的流程。"""

    @abstractmethod
    def on_select_card(self, ctx: 'CardSelectContext'):
        """处理技能卡选择。"""

    @abstractmethod
    def on_outing(self, ctx: 'OutingContext'):
        """处理外出事件选择。"""
        pass

    @abstractmethod
    def on_consult(self, ctx: 'ConsultContext'):
        pass

    @abstractmethod
    def on_allowance(self, ctx: 'AllowanceContext'):
        pass

    @abstractmethod
    def on_pdrink_max(self, ctx: 'PDrinkMaxContext'):
        """处理 P饮料到达上限弹窗。"""
        pass

    @abstractmethod
    def on_pdrink_max_confirm(self, ctx: 'PDrinkMaxConfirmContext'):
        """处理 P饮料到达上限确认弹窗。"""
        pass

    @abstractmethod
    def on_date_change(self, ctx: 'DateChangeContext'):
        """处理日期变更弹窗。"""
        pass

    @abstractmethod
    def on_select_drink(self, ctx: 'DrinkSelectContext'):
        """处理饮料选择。"""
        pass

    @abstractmethod
    def on_select_pitem(self, ctx: 'PItemSelectContext'):
        """处理 P道具选择。"""
        pass

    @abstractmethod
    def on_skill_card_enhance(self, ctx: 'SkillCardEnhanceContext'):
        """处理技能卡自选强化。"""
        pass

    @abstractmethod
    def on_skill_card_removal(self, ctx: 'SkillCardRemovalContext'):
        """处理技能卡自选删除。"""
        pass

    @abstractmethod
    def on_skill_card_change(self, ctx: 'SkillCardChangeContext'):
        """处理技能卡自选变更"""
        pass

    @abstractmethod
    def on_practice_exited(self):
        """练习战场景退出后的回调。"""
        pass

    def try_handle_commu(self, img) -> bool:
        """尝试处理交流事件。

        :return: 是否已处理交流事件。
        """
        if produce_solution().data.skip_commu and handle_unread_commu(img):
            return True
        return False

    def on_produce_end(self, ctx: 'ProduceEndContext'):
        """处理培育结算场景"""
        for _ in Loop(interval=1):
            if at_home():
                logger.info("Back to home after produce end.")
                ctx.controller.abort()
                break

            # 生成记忆
            elif R.InProduce.End.ButtonGenerate.try_click():
                logger.info("Clicked generate memory.")
            elif R.Produce.SaveMemoPic.Title.exists():
                logger.info("Save memory picture dialog detected. Click to close.")
                if R.Produce.SaveMemoPic.ButtonConfirm.try_click():
                    logger.debug("Clicked confirm button in save memory picture dialog.")
                    sleep(3)
            elif R.InProduce.ButtonNextNoIcon.try_click():
                logger.info("Clicked 'Next' button in produce end scene.")

            # 活动积分进度 奖励领取
            # [screenshots/produce_end/end_activity1.png]
            # 制作人 升级
            # [screenshots/produce_end/end_level_up.png]
            if R.Common.ButtonIconClose.try_click():
                logger.info("Activity award claim dialog found. Clicked to close.")
            # 活动积分进度
            # [screenshots/produce_end/end_activity.png]
            elif R.Common.ButtonNextNoIcon.q(enabled=True).try_click():
                logger.debug("Clicked next")
            # 关注制作人
            # [screenshots/produce_end/end_follow.png]
            elif R.InProduce.ButtonCancel.exists():
                logger.info("Follow producer dialog found. Click to close.")
                if produce_solution().data.follow_producer:
                    logger.info("Follow producer")
                    R.InProduce.ButtonFollowNoIcon.wait().click()
                else:
                    logger.info("Skip follow producer")
                    device.click()
            # 偶像强化月 新纪录达成
            # [kotonebot-resource/sprites/jp/in_purodyuusu/screenshot_new_record.png]
            elif R.Common.ButtonOK.exists():
                logger.info("OK button found. Click to close.")
                device.click()

            else:
                device.click_center()


class HifProduceStrategy(ProduceStrategy):
    """HIF 培育策略基类。"""

    def on_hif_round_interval(self, ctx: 'HifRoundIntervalContext'):
        raise NotImplementedError()
