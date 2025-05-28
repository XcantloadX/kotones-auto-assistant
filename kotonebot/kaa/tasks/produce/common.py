from typing import Literal
from logging import getLogger

from kotonebot import (
    ocr,
    device,
    image,
    action,
    sleep,
    Interval,
)
from kotonebot.kaa.skill_card_action.select_skill_card import select_skill_card
from kotonebot.primitives import Rect
from kotonebot.kaa.tasks import R
from .p_drink import acquire_p_drink
from kotonebot.util import measure_time
from kotonebot.kaa.common import conf
from kotonebot.kaa.tasks.actions.loading import loading
from kotonebot.kaa.game_ui import CommuEventButtonUI, dialog, badge
from kotonebot.kaa.tasks.actions.commu import handle_unread_commu

logger = getLogger(__name__)

@action('领取技能卡', screenshot_mode='manual-inherit')
def acquire_skill_card():
    """获取技能卡（スキルカード）"""
    select_skill_card()
    # TODO: 识别卡片内容，而不是固定选卡
    # TODO: 不硬编码坐标
    # logger.debug("Locating all skill cards...")
    # 
    # it = Interval()
    # cards = None
    # card_clicked = False
    # target_card = None
    # 
    # while True:
    #     device.screenshot()
    #     it.wait()
    #     
    #     # 是否显示技能卡选择指导的对话框
    #     # [kotonebot-resource/sprites/jp/in_purodyuusu/screenshot_show_skill_card_select_guide_dialog.png]
    #     if image.find(R.InPurodyuusu.TextSkillCardSelectGuideDialogTitle):
    #         # 默认就是显示，直接确认
    #         dialog.yes()
    #         continue
    #     if not cards:
    #         cards = image.find_all_multi([
    #             R.InPurodyuusu.A,
    #             R.InPurodyuusu.M
    #         ])
    #         if not cards:
    #             logger.warning("No skill cards found. Skip acquire.")
    #             return
    #         cards = sorted(cards, key=lambda x: (x.position[0], x.position[1]))
    #         logger.info(f"Found {len(cards)} skill cards")
    #         # 判断是否有推荐卡
    #         rec_badges = image.find_all(R.InPurodyuusu.TextRecommend)
    #         rec_badges = [card.rect for card in rec_badges]
    #         if rec_badges:
    #             cards = [card.rect for card in cards]
    #             matches = badge.match(cards, rec_badges, 'mb')
    #             logger.debug("Recommend card badge matches: %s", matches)
    #             # 选第一个推荐卡
    #             target_match = next(filter(lambda m: m.badge is not None, matches), None)
    #             if target_match:
    #                 target_card = target_match.object
    #             else:
    #                 target_card = cards[0]
    #         else:
    #             logger.debug("No recommend badge found. Pick first card.")
    #             target_card = cards[0].rect
    #         continue
    #     if not card_clicked and target_card is not None:
    #         logger.debug("Click target skill card")
    #         device.click(target_card)
    #         card_clicked = True
    #         sleep(0.2)
    #         continue
    #     if acquire_btn := image.find(R.InPurodyuusu.AcquireBtnDisabled):
    #         logger.debug("Click acquire button")
    #         device.click(acquire_btn)
    #         break

@action('选择P物品', screenshot_mode='auto')
def select_p_item():
    """
    前置条件：P物品选择对话框（受け取るＰアイテムを選んでください;）\n
    结束状态：P物品获取动画
    """
    # 前置条件 [screenshots/produce/in_produce/select_p_item.png]
    # 前置条件 [screenshots/produce/in_produce/claim_p_item.png]

    POSTIONS = [
        Rect(157, 820, 128, 128), # x, y, w, h
        Rect(296, 820, 128, 128),
        Rect(435, 820, 128, 128),
    ] # TODO: HARD CODED
    device.click(POSTIONS[0])
    sleep(0.5)
    device.click(ocr.expect_wait('受け取る'))


@action('技能卡自选强化', screenshot_mode='manual-inherit')
def handle_skill_card_enhance():
    """
    前置条件：技能卡强化对话框\n
    结束状态：技能卡强化动画结束后瞬间

    :return: 是否成功处理对话框
    """
    # 前置条件 [kotonebot-resource\sprites\jp\in_purodyuusu\screenshot_skill_card_enhane.png]
    # 结束状态 [screenshots/produce/in_produce/skill_card_enhance.png]
    cards = image.find_all_multi([
        R.InPurodyuusu.A,
        R.InPurodyuusu.M
    ])
    if cards is None:
        logger.info("No skill cards found")
        return False
    cards = sorted(cards, key=lambda x: (x.position[1], x.position[0]))
    it = Interval(0.5)
    for card in reversed(cards):
        device.click(card)
        it.wait()
        device.screenshot()
        if image.find(R.InPurodyuusu.ButtonEnhance, colored=True):
            logger.debug("Enhance button found")
            device.click()
            it.wait()
            break
    logger.debug("Handle skill card enhance finished.")
    return True

@action('技能卡自选删除', screenshot_mode='manual-inherit')
def handle_skill_card_removal():
    """
    前置条件：技能卡删除对话框\n
    结束状态：技能卡删除动画结束后瞬间
    """
    # 前置条件 [kotonebot-resource\sprites\jp\in_purodyuusu\screenshot_remove_skill_card.png]
    card = image.find_multi([
        R.InPurodyuusu.A,
        R.InPurodyuusu.M
    ])
    if card is None:
        logger.info("No skill cards found")
        return False
    device.click(card)
    it = Interval()
    while True:
        device.screenshot()
        if image.find(R.InPurodyuusu.ButtonRemove):
            device.click()
            logger.debug("Remove button clicked.")
            break
        it.wait()
    logger.debug("Handle skill card removal finished.")

AcquisitionType = Literal[
    "PDrinkAcquire", # P饮料被动领取
    "PDrinkSelect", # P饮料主动领取
    "PDrinkMax", # P饮料到达上限
    "PSkillCardAcquire", # 技能卡领取
    "PSkillCardSelect", # 技能卡选择
    "PSkillCardEnhanced", # 技能卡强化
    "PSkillCardEnhanceSelect", # 技能卡自选强化
    "PSkillCardRemoveSelect", # 技能卡自选删除
    "PSkillCardEvent", # 技能卡事件（随机强化、删除、更换）
    "PItemClaim", # P物品领取
    "PItemSelect", # P物品选择
    "Clear", # 目标达成
    "ClearNext", # 目标达成 NEXT
    "NetworkError", # 网络中断弹窗
    "SkipCommu", # 跳过交流
    "Loading", # 加载画面
]
@measure_time()
@action('处理培育事件', screenshot_mode='manual')
def fast_acquisitions() -> AcquisitionType | None:
    """处理行动开始前和结束后可能需要处理的事件"""
    img = device.screenshot()
    logger.info("Acquisition stuffs...")
    
    # 加载画面
    if loading():
        logger.info("Loading...")
        return "Loading"
    device.click(10, 10)

    # 跳过未读交流
    logger.debug("Check skip commu...")
    if conf().produce.skip_commu and handle_unread_commu(img):
        return "SkipCommu"
    device.click(10, 10)

    # P饮料到达上限
    logger.debug("Check PDrink max...")
    # TODO: 需要封装一个更好的实现方式。比如 wait_stable？
    if image.find(R.InPurodyuusu.TextPDrinkMax):
        logger.debug("PDrink max found")
        device.screenshot()
        if image.find(R.InPurodyuusu.TextPDrinkMax):
            # 有对话框标题，但是没找到确认按钮
            # 可能是需要勾选一个饮料
            if not image.find(R.InPurodyuusu.ButtonLeave, colored=True):
                logger.info("No leave button found, click checkbox")
                device.click(image.expect(R.Common.CheckboxUnchecked, colored=True))
                sleep(0.2)
                device.screenshot()
            if leave := image.find(R.InPurodyuusu.ButtonLeave, colored=True):
                logger.info("Leave button found")
                device.click(leave)
                return "PDrinkMax"
    # P饮料到达上限 确认提示框
    # [kotonebot-resource\sprites\jp\in_purodyuusu\screenshot_pdrink_max_confirm.png]
    if image.find(R.InPurodyuusu.TextPDrinkMaxConfirmTitle):
        logger.debug("PDrink max confirm found")
        device.screenshot()
        if image.find(R.InPurodyuusu.TextPDrinkMaxConfirmTitle):
            if confirm := image.find(R.Common.ButtonConfirm):
                logger.info("Confirm button found")
                device.click(confirm)
                return "PDrinkMax"
    device.click(10, 10)

    # 技能卡自选强化
    if image.find(R.InPurodyuusu.IconTitleSkillCardEnhance):
        if handle_skill_card_enhance():
            return "PSkillCardEnhanceSelect"
    device.click(10, 10)

    # 技能卡自选删除
    if image.find(R.InPurodyuusu.IconTitleSkillCardRemoval):
        if handle_skill_card_removal():
            return "PSkillCardRemoveSelect"
    device.click(10, 10)

    # 网络中断弹窗
    logger.debug("Check network error popup...")
    if (image.find(R.Common.TextNetworkError) 
        and (btn_retry := image.find(R.Common.ButtonRetry))
    ):
        logger.info("Network error popup found")
        device.click(btn_retry)
        return "NetworkError"
    device.click(10, 10)

    # 物品选择对话框
    logger.debug("Check award select dialog...")
    if image.find(R.InPurodyuusu.TextClaim):
        logger.info("Award select dialog found.")

        # P饮料选择
        logger.debug("Check PDrink select...")
        if image.find(R.InPurodyuusu.TextPDrink):
            logger.info("PDrink select found")
            acquire_p_drink()
            return "PDrinkSelect"
        # 技能卡选择
        logger.debug("Check skill card select...")
        if image.find(R.InPurodyuusu.TextSkillCard):
            logger.info("Acquire skill card found")
            acquire_skill_card()
            return "PSkillCardSelect"
        # P物品选择
        logger.debug("Check PItem select...")
        if image.find(R.InPurodyuusu.TextPItem):
            logger.info("Acquire PItem found")
            select_p_item()
            return "PItemSelect"
    device.click(10, 10)

    return None

def until_acquisition_clear():
    """
    处理各种奖励、弹窗，直到没有新的奖励、弹窗为止

    前置条件：任意\n
    结束条件：任意
    """
    interval = Interval(0.6)
    while fast_acquisitions():
        interval.wait()

ORANGE_RANGE = ((14, 87, 23)), ((37, 211, 255))
@action('处理交流事件', screenshot_mode='manual-inherit')
def commu_event():
    ui = CommuEventButtonUI([ORANGE_RANGE])
    buttons = ui.all(description=False, title=True)
    if len(buttons) > 1:
        for button in buttons:
            # 冲刺课程，跳过处理
            if '重点' in button.title:
                return False
        logger.info(f"Found commu event: {buttons}")
        logger.info("Select first choice")
        if buttons[0].selected:
            device.click(buttons[0])
        else:
            device.double_click(buttons[0])
        return True
    return False
    

if __name__ == '__main__':
    from logging import getLogger
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    getLogger('kotonebot').setLevel(logging.DEBUG)
    getLogger(__name__).setLevel(logging.DEBUG)

    select_p_item()