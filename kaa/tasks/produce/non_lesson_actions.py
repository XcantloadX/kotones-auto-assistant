"""
此文件包含非练习/考试的行动。

具体包括：おでかけ、相談、活動支給、授業
"""
from logging import getLogger

from kaa.config.schema import produce_solution
from kaa.game_ui import dialog

from kaa.tasks import R
from kaa.config import conf
from ..produce.common import ProduceInterrupt
from kaa.game_ui.commu_event_buttons import CommuEventButtonUI
from kotonebot.util import Countdown
from kotonebot.backend.loop import Loop
from kotonebot.errors import UnrecoverableError
from kotonebot import device, image, action, sleep
from kotonebot.core import AnyOf
from kotonebot.backend.dispatch import SimpleDispatcher

logger = getLogger(__name__)

@action('检测是否可以执行活動支給')
def allowance_available():
    """
    判断是否可以执行活動支給。
    """
    return R.InPurodyuusu.ButtonTextAllowance.exists()

@action('检测是否可以执行授業')
def study_available():
    """
    判断是否可以执行授業。
    """
    # [screenshots/produce/action_study1.png]
    return R.InPurodyuusu.ButtonIconStudy.exists()

@action('检测是否可以执行相談')
def consult_available():
    """
    判断是否可以执行相談。
    """
    return R.InPurodyuusu.ButtonIconConsult.exists()

# TODO: 把进入授業的逻辑和执行授業的逻辑分离
@action('执行授業')
def enter_study():
    """
    执行授業。

    前置条件：位于行动页面，且所有行动按钮清晰可见 \n
    结束状态：选择选项后可能会出现的，比如领取奖励、加载画面等。
    """
    logger.info("Executing 授業.")
    # [screenshots/produce/action_study1.png]
    logger.debug("Double clicking on 授業.")
    R.InPurodyuusu.ButtonIconStudy.wait().double_click()
    # 等待进入页面。中间可能会出现未读交流
    # [screenshots/produce/action_study2.png]
    ProduceInterrupt().until(R.InPurodyuusu.IconTitleStudy)
    # 首先需要判断是不是自习课
    # [kotonebot-resource\sprites\jp\in_purodyuusu\screenshot_study_self_study.png]
    if AnyOf[
        R.InPurodyuusu.TextSelfStudyDance,
        R.InPurodyuusu.TextSelfStudyVisual,
        R.InPurodyuusu.TextSelfStudyVocal
    ].exists():
        logger.info("授業 type: Self study.")
        target = produce_solution().data.self_study_lesson
        if target == 'dance':
            logger.debug("Clicking on lesson dance.")
            R.InPurodyuusu.TextSelfStudyDance.wait().double_click()
        elif target == 'visual':
            logger.debug("Clicking on lesson visual.")
            R.InPurodyuusu.TextSelfStudyVisual.wait().double_click()
        elif target == 'vocal':
            logger.debug("Clicking on lesson vocal.")
            R.InPurodyuusu.TextSelfStudyVocal.wait().double_click()
        from ..produce.in_purodyuusu import until_practice_scene, practice
        logger.info("Entering practice scene.")
        until_practice_scene()
        logger.info("Executing practice.")
        practice()
        logger.info("Practice completed.")
    # 不是自习课
    else:
        logger.info("授業 type: Normal.")
        # 获取三个选项的内容
        ui = CommuEventButtonUI()
        buttons = ui.all()
        if not buttons:
            raise UnrecoverableError("Failed to find any buttons.")
        # 选中 +30 的选项
        target_btn = next((btn for btn in buttons if '+30' in btn.description), None)
        if target_btn is None:
            logger.error("Failed to find +30 option. Pick the second button instead.")
            target_btn = buttons[1]
        logger.debug('Clicking "%s".', target_btn.description)
        if target_btn.selected:
            device.click(target_btn)
        else:
            device.double_click(target_btn)
        ProduceInterrupt().resolve()
    logger.info("授業 completed.")


@action('执行活動支給')
def enter_allowance():
    """
    执行活動支給。
    
    前置条件：位于行动页面，且所有行动按钮清晰可见 \n
    结束状态：位于行动页面
    """
    logger.info("Executing 活動支給.")
    # 点击活動支給 [screenshots\allowance\step_1.png]
    logger.info("Double clicking on 活動支給.")
    R.InPurodyuusu.ButtonTextAllowance.wait(interval=1).double_click()
    # 等待进入页面
    ProduceInterrupt().until(R.InPurodyuusu.IconTitleAllowance)
    # 领取奖励
    pi = ProduceInterrupt()
    for _ in Loop():
        # TODO: 检测是否在行动页面应当单独一个函数
        if AnyOf[
            R.InPurodyuusu.TextPDiary, # 普通周
            R.InPurodyuusu.ButtonFinalPracticeDance # 离考试剩余一周
        ].exists():
            break
        if R.InPurodyuusu.LootboxSliverLock.try_click():
            logger.info("Clicked on lootbox.")
            sleep(0.5) # 防止点击了第一个箱子后立马点击了第二个
            continue
        if pi.handle():
            continue
    logger.info("活動支給 completed.")

# TODO: 将逻辑用循环改写
@action('执行相談', screenshot_mode='manual-inherit')
def enter_consult():
    """
    执行相談。
    
    前置条件：位于行动页面，且所有行动按钮清晰可见 \n
    结束状态：位于行动页面
    """
    logger.info("Executing 相談.")
    logger.info("Double clicking on 相談.")
    device.screenshot()
    R.InPurodyuusu.ButtonIconConsult.wait(interval=1).double_click()
    
    # 等待进入页面
    ProduceInterrupt().until(R.InPurodyuusu.IconTitleConsult)
    # # 尝试固定购买第一个物品
    # device.click(R.InPurodyuusu.PointConsultFirstItem)
    # sleep(0.5)
    # device.click(image.expect(R.InPurodyuusu.ButtonIconExchange))
    # # 等待弹窗
    # timeout_cd = Countdown(sec=5).start()
    # while not timeout_cd.expired():
    #     if dialog.yes():
    #         break
    # # 结束
    # while not image.find(R.InPurodyuusu.ButtonEndConsult):
    #     fast_acquisitions()
    # device.click(image.expect_wait(R.InPurodyuusu.ButtonEndConsult))
    # # 可能会弹出确认对话框
    # timeout_cd.reset().start()
    # while not timeout_cd.expired():
    #     dialog.yes()
    device.click(R.InPurodyuusu.PointConsultFirstItem)
    sleep(0.3)
    wait_purchase_cd = Countdown(sec=5)
    exit_cd = Countdown(sec=5)
    purchase_clicked = False
    purchase_confirmed = False
    exit_clicked = False
    for _ in Loop():
        if wait_purchase_cd.expired():
            # 等待购买确认对话框超时后直接认为购买完成
            purchase_confirmed = True

        if dialog.yes():
            if purchase_clicked:
                purchase_confirmed = True
                continue
            elif purchase_confirmed:
                continue
            elif exit_clicked:
                break
        if R.InPurodyuusu.ButtonIconExchange(enabled=True).try_click():
            purchase_clicked = True
            continue
        if purchase_confirmed and R.InPurodyuusu.ButtonEndConsult.try_click():
            exit_clicked = True
            exit_cd.start()
            continue

        # 等待退出对话框超时，直接退出
        if exit_cd.expired():
            break

        if not purchase_confirmed:
            device.click(R.InPurodyuusu.PointConsultFirstItem)
            # 处理不能购买的情况（超时）
            # TODO: 应当检测画面文字/图标而不是用超时
            wait_purchase_cd.start()

    logger.info("相談 completed.")

@action('判断是否可以休息')
def is_rest_available():
    """
    判断是否可以休息。
    """
    return R.InPurodyuusu.Rest.exists()


@action('执行休息')
def rest():
    """执行休息"""
    logger.info("Rest for this week.")

    # 部分设备上，第二次click（确定）点击速度过快，导致卡死，所以这里需要添加一个sleep
    R.InPurodyuusu.Rest.wait().click()
    sleep(0.5)
    R.InPurodyuusu.RestConfirmBtn.wait().click()
    # 原方案
    # (SimpleDispatcher('in_produce.rest')
    #     # 点击休息
    #     .click(R.InPurodyuusu.Rest)
    #     # 确定
    #     .click(R.InPurodyuusu.RestConfirmBtn, finish=True)
    # ).run()

@action('判断是否处于行动页面')
def at_action_scene():
    return AnyOf[
        R.InPurodyuusu.TextPDiary, # 普通周
        R.InPurodyuusu.ButtonFinalPracticeDance # 离考试剩余一周
    ].exists()

@action('判断是否可以外出')
def outing_available():
    """
    判断是否可以外出（おでかけ）。
    """
    return R.InPurodyuusu.ButtonIconOuting.exists()

@action('执行外出')
def enter_outing():
    """
    执行外出（おでかけ）。

    前置条件：位于行动页面，且所有行动按钮清晰可见 \n
    结束状态：位于行动页面
    """
    logger.info("Executing おでかけ.")
    # 点击外出
    logger.info("Double clicking on おでかけ.")
    R.InPurodyuusu.ButtonIconOuting.wait().double_click()
    # 等待进入页面
    ProduceInterrupt().until(R.InPurodyuusu.TitleIconOuting)
    # 固定选中第二个选项
    # TODO: 可能需要二次处理外出事件
    # [kotonebot-resource\sprites\jp\in_purodyuusu\screenshot_outing.png]
    ui = CommuEventButtonUI()
    buttons = ui.all()
    if not buttons:
        raise UnrecoverableError("Failed to find any buttons.")
    target_btn = buttons[min(1, len(buttons) - 1)]
    logger.debug('Clicking "%s".', target_btn.description)
    if target_btn.selected:
        device.click(target_btn)
    else:
        device.double_click(target_btn)
    pi = ProduceInterrupt()
    for _ in Loop():
        if at_action_scene():
            break
        elif pi.handle():
            pass
        # [screenshots\produce\outing_ap_confirm.png]
        elif R.Common.ButtonSelect2.try_click():
            logger.info("AP max out dialog found. Clicked continue button.")
            sleep(0.1)

    logger.info("おでかけ completed.")

if __name__ == '__main__':
    enter_consult()