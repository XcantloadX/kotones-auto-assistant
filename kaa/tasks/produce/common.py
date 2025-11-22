from typing import Literal
from logging import getLogger

from kotonebot import (
    ocr,
    device,
    image,
    action,
    sleep,
    Loop,
    Interval,
)
from kaa.config.schema import produce_solution
from kaa.tasks.start_game import wait_for_home
from kotonebot.primitives import Rect
from kaa.tasks import R
from kaa.tasks.common import skip
from .p_drink import acquire_p_drink
from kotonebot.util import measure_time
from kaa.config import conf
from kaa.tasks.actions.loading import loading
from kaa.game_ui import CommuEventButtonUI, dialog, badge
from kaa.tasks.actions.commu import handle_unread_commu

logger = getLogger(__name__)

@action('领取技能卡', screenshot_mode='manual-inherit')
def acquire_skill_card():
    """获取技能卡（スキルカード）"""
    # TODO: 识别卡片内容，而不是固定选卡
    # TODO: 不硬编码坐标
    logger.debug("Locating all skill cards...")
    
    cards = None
    card_clicked = False
    target_card = None
    
    for _ in Loop():
        # 是否显示技能卡选择指导的对话框
        # [kotonebot-resource/sprites/jp/in_purodyuusu/screenshot_show_skill_card_select_guide_dialog.png]
        if image.find(R.InPurodyuusu.TextSkillCardSelectGuideDialogTitle):
            # 默认就是显示，直接确认
            dialog.yes()
            continue
        if not cards:
            cards = image.find_all_multi([
                R.InPurodyuusu.A,
                R.InPurodyuusu.M
            ])
            if not cards:
                logger.warning("No skill cards found. Skip acquire.")
                return
            cards = sorted(cards, key=lambda x: (x.position[0], x.position[1]))
            logger.info(f"Found {len(cards)} skill cards")
            # 判断是否有推荐卡
            rec_badges = image.find_all(R.InPurodyuusu.TextRecommend)
            rec_badges = [card.rect for card in rec_badges]
            if rec_badges:
                cards = [card.rect for card in cards]
                matches = badge.match(cards, rec_badges, 'mb')
                logger.debug("Recommend card badge matches: %s", matches)
                # 选第一个推荐卡
                target_match = next(filter(lambda m: m.badge is not None, matches), None)
                if target_match:
                    target_card = target_match.object
                else:
                    target_card = cards[0]
            else:
                logger.debug("No recommend badge found. Pick first card.")
                target_card = cards[0].rect
            continue
        if not card_clicked and target_card is not None:
            logger.debug("Click target skill card")
            device.click(target_card)
            card_clicked = True
            sleep(0.2)
            continue
        if acquire_btn := image.find(R.InPurodyuusu.AcquireBtnDisabled):
            logger.debug("Click acquire button")
            device.click(acquire_btn)
            break

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
    for _ in Loop():
        if image.find(R.InPurodyuusu.ButtonRemove):
            device.click()
            logger.debug("Remove button clicked.")
            break
    logger.debug("Handle skill card removal finished.")

@action('继续当前培育.进入培育', screenshot_mode='manual-inherit')
def resume_produce_pre() -> tuple[Literal['regular', 'pro', 'master'], int]:
    """
    继续当前培育.进入培育\n
    该函数用于处理‘日期变更’等情况；单独执行此函数时，要确保代码已经处于培育状态。

    前置条件：游戏首页，且当前有进行中培育\n
    结束状态：培育中的任意一个页面
    """
    device.screenshot()
    # 点击 プロデュース中
    # [res/sprites/jp/daily/home_1.png]
    logger.info('Click ongoing produce button.')
    device.click(R.Produce.BoxProduceOngoing)
    btn_resume = image.expect_wait(R.Produce.ButtonResume)
    # 判断信息
    mode_result = image.find_multi([
        R.Produce.ResumeDialogRegular,
        R.Produce.ResumeDialogPro,
        R.Produce.ResumeDialogMaster
    ])
    if not mode_result:
        raise ValueError('Failed to detect produce mode.')
    if mode_result.index == 0:
        mode = 'regular'
    elif mode_result.index == 1:
        mode = 'pro'
    else:
        mode = 'master'
    logger.info(f'Produce mode: {mode}')
    retry_count = 0
    max_retries = 5
    current_week = None
    while retry_count < max_retries:
        week_text = ocr.ocr(R.Produce.BoxResumeDialogWeeks, lang='en').squash().regex(r'\d+/\d+')
        if week_text:
            weeks = week_text[0].split('/')
            logger.info(f'Current week: {weeks[0]}/{weeks[1]}')
            if len(weeks) >= 2:
                current_week = int(weeks[0])
                break
        week_text2 = ocr.ocr(R.Produce.BoxResumeDialogWeeks_Saving, lang='en').squash().regex(r'\d+/\d+')
        if week_text2:
            weeks = week_text2[0].split('/')
            logger.info(f'Current week: {weeks[0]}/{weeks[1]}')
            if len(weeks) >= 2:
                current_week = int(weeks[0])
                break
        retry_count += 1
        logger.warning(f'Failed to detect weeks. week_text="{week_text}". Retrying... ({retry_count}/{max_retries})')
        sleep(0.5)
        device.screenshot()
    
    if retry_count >= max_retries:
        raise ValueError('Failed to detect weeks after multiple retries.')
    if current_week is None:
        raise ValueError('Failed to detect current_week.')
    # 点击 再開する
    # [kotonebot-resource/sprites/jp/produce/produce_resume.png]
    logger.info('Click resume button.')
    device.click(btn_resume)

    return mode, current_week

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
    "DateChange", # 日期变更
]

def acquisition_date_change_dialog() -> AcquisitionType | None:
    """
    检测是否执行了日期变更。\n
    如果出现了日期变更，则对日期变更直接进行处理（返回标题、进入游戏、重进培育）\n
    注：不更新屏幕截图。
    """

    # 日期变更（可以考虑加入版本更新，但因为我目前没有版本更新的720x1080素材，所以没法加）
    logger.debug("Check date change dialog...")
    if image.find(R.Daily.TextDateChangeDialog):
        logger.info("Date change dialog found.")
        # 点击确认
        device.click(image.expect(R.Daily.TextDateChangeDialogConfirmButton))
        # 进入游戏
        # 注：wait_for_home()里的Loop类第一次进入循环体时，会自动执行device.screenshot()
        wait_for_home()
        # 重进培育
        resume_produce_pre()
        return "DateChange"

    return None

# TODO: 这里要改善一下输出日志。
# Acquisitions finished. Handled: xxx(event name or 'none'). Checked: 12(number of acquisitions) / 12(number of acquisitions)
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
    skip()

    # 跳过未读交流
    logger.debug("Check skip commu...")
    if produce_solution().data.skip_commu and handle_unread_commu(img):
        return "SkipCommu"
    skip()

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
    skip()

    # 技能卡自选强化
    if image.find(R.InPurodyuusu.IconTitleSkillCardEnhance):
        if handle_skill_card_enhance():
            return "PSkillCardEnhanceSelect"
    skip()

    # 技能卡自选删除
    if image.find(R.InPurodyuusu.IconTitleSkillCardRemoval):
        if handle_skill_card_removal():
            return "PSkillCardRemoveSelect"
    skip()

    # 网络中断弹窗
    logger.debug("Check network error popup...")
    if (image.find(R.Common.TextNetworkError) 
        and (btn_retry := image.find(R.Common.ButtonRetry))
    ):
        logger.info("Network error popup found")
        device.click(btn_retry)
        return "NetworkError"
    skip()

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
    skip()

    # 日期变更
    result = acquisition_date_change_dialog()
    if result is not None:
        return result
    skip()

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
        sleep(2.5) # HACK: 为了防止点击后按钮还没消失就进行第二次检测
        return True
    return False
    

if __name__ == '__main__':
    from logging import getLogger
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    getLogger('kotonebot').setLevel(logging.DEBUG)
    getLogger(__name__).setLevel(logging.DEBUG)

    select_p_item()