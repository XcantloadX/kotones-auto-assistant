from logging import getLogger
from turtle import color
from typing import Literal, Callable

from cv2.typing import MatLike
from kotonebot import (
    ocr,
    device,
    image,
    action,
    sleep,
    Loop,
    Interval,
)
from kotonebot.core import AnyOf
from kotonebot.util import Countdown
from kotonebot.primitives import Rect
from kaa.tasks import R
from kaa.tasks.common import skip
from .p_drink import acquire_p_drink
from kotonebot.util import measure_time
from kotonebot.backend.core import Image
from kotonebot.errors import UnrecoverableError

from kotonebot.core import Prefab
from kaa.tasks import R
from kaa.config import conf
from .p_drink import acquire_p_drink
from kaa.tasks.actions.loading import loading
from kaa.kaa_context import produce_solution
from kaa.tasks.start_game import wait_for_home
from kaa.tasks.actions.commu import handle_unread_commu
from kaa.game_ui import CommuEventButtonUI, dialog, badge

logger = getLogger(__name__)

@action('领取技能卡', screenshot_mode='manual-inherit')
def acquire_skill_card():
    """获取技能卡（スキルカード）"""
    # TODO: 识别卡片内容，而不是固定选卡
    logger.debug("Locating all skill cards...")
    
    cards = None
    card_clicked = False
    target_card = None
    
    for _ in Loop():
        # 是否显示技能卡选择指导的对话框
        # [kotonebot-resource/sprites/jp/in_purodyuusu/screenshot_show_skill_card_select_guide_dialog.png]
        if R.InPurodyuusu.TextSkillCardSelectGuideDialogTitle.exists():
            # 默认就是显示，直接确认
            dialog.yes()
            continue
        if not cards:
            cards = AnyOf[
                R.InPurodyuusu.A,
                R.InPurodyuusu.M
            ].find_all()
            if not cards:
                logger.warning("No skill cards found. Skip acquire.")
                return
            cards = sorted(cards, key=lambda x: x.rect.top_left)
            logger.info(f"Found {len(cards)} skill cards")
            # 判断是否有推荐卡
            rec_badges = R.InPurodyuusu.TextRecommend.find_all()
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
        if acquire_btn := R.InPurodyuusu.AcquireBtnDisabled.find():
            logger.debug("Click acquire button")
            device.click(acquire_btn)
            sleep(0.2)
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
    cards = AnyOf[
        R.InPurodyuusu.A,
        R.InPurodyuusu.M
    ].find_all()
    if cards is None:
        logger.info("No skill cards found")
        return False
    cards = sorted(cards, key=lambda x: x.rect.top_left.xy)
    it = Interval(0.5)
    for card in reversed(cards):
        device.click(card)
        it.wait()
        device.screenshot()
        if R.InPurodyuusu.ButtonEnhance(enabled=True).try_click():
            logger.debug("Enhance button clicked")
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
    card = AnyOf[
        R.InPurodyuusu.A,
        R.InPurodyuusu.M
    ].find()
    if card is None:
        logger.info("No skill cards found")
        return False
    device.click(card)
    for _ in Loop():
        if R.InPurodyuusu.ButtonRemove.try_click():
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
    btn_resume = R.Produce.ButtonResume.wait()
    # 判断信息
    mode_result = AnyOf[
        R.Produce.ResumeDialogRegular,
        R.Produce.ResumeDialogPro,
        R.Produce.ResumeDialogMaster
    ].find()
    if not mode_result:
        raise ValueError('Failed to detect produce mode.')
    if mode_result.prefab == R.Produce.ResumeDialogRegular:
        mode = 'regular'
    elif mode_result.prefab == R.Produce.ResumeDialogPro:
        mode = 'pro'
    else:
        mode = 'master'
    logger.info(f'Produce mode: {mode}')
    retry_count = 0
    max_retries = 5
    current_week = None
    while retry_count < max_retries:
        week_text = ocr.ocr(R.Produce.BoxResumeDialogWeeks, lang='en').squash().regex(r'\d+/\d+')
        logger.debug('Week text: %s', week_text)
        if week_text:
            weeks = week_text[0].split('/')
            logger.info(f'Current week: {weeks[0]}/{weeks[1]}')
            if len(weeks) >= 2:
                current_week = int(weeks[0])
                break
        logger.debug('Week text2: %s', week_text)
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
    if R.Daily.TextDateChangeDialog.exists():
        logger.info("Date change dialog found.")
        # 点击确认
        R.Daily.TextDateChangeDialogConfirmButton.require().click()
        # 进入游戏
        # 注：wait_for_home()里的Loop类第一次进入循环体时，会自动执行device.screenshot()
        wait_for_home()
        # 重进培育
        resume_produce_pre()
        return "DateChange"

    return None

# TODO: 这里要改善一下输出日志。
# Acquisitions finished. Handled: xxx(event name or 'none'). Checked: 12(number of acquisitions) / 12(number of acquisitions)
class ProduceInterrupt:
    def __init__(self, *, timeout: float | None = None):
        """
        :param timeout: 超时时间，单位秒。默认为 None，表示使用配置文件中的时间。
        """
        timeout = timeout or conf().produce.interrupt_timeout
        self.cd = Countdown(timeout)

    @staticmethod
    def _check_loading(img: MatLike) -> AcquisitionType | None:
        """检查加载画面"""
        if loading():
            logger.info("Loading...")
            return "Loading"
        return None

    @staticmethod
    def _check_skip_commu(img: MatLike) -> AcquisitionType | None:
        """检查跳过未读交流"""
        logger.debug("Check skip commu...")
        if produce_solution().data.skip_commu and handle_unread_commu(img):
            return "SkipCommu"
        return None

    @staticmethod
    def _check_pdrink_max(img: MatLike) -> AcquisitionType | None:
        """检查P饮料到达上限"""
        logger.debug("Check PDrink max...")
        # TODO: 需要封装一个更好的实现方式。比如 wait_stable？
        if R.InPurodyuusu.TextPDrinkMax.exists():
            logger.debug("PDrink max found")
            device.screenshot()
            if R.InPurodyuusu.TextPDrinkMax.exists():
                # 有对话框标题，但是没找到确认按钮
                # 可能是需要勾选一个饮料
                # 也有可能是对话框正在往下退出
                if not R.InPurodyuusu.ButtonLeave(enabled=True).find():
                    logger.info("No leave button found, click checkbox")
                    if chk := R.Common.CheckboxUnchecked.find(colored=True):
                        device.click(chk)
                        sleep(0.2)
                        device.screenshot()
                if R.InPurodyuusu.ButtonLeave(enabled=True).try_click():
                    logger.info("Leave button clicked")
                    return "PDrinkMax"
        return None

    @staticmethod
    def _check_pdrink_max_confirm(img: MatLike) -> AcquisitionType | None:
        """检查P饮料到达上限确认提示框"""
        # [kotonebot-resource/sprites/jp/in_purodyuusu/screenshot_pdrink_max_confirm.png]
        if R.InPurodyuusu.TextPDrinkMaxConfirmTitle.exists():
            logger.debug("PDrink max confirm found")
            device.screenshot()
            if R.InPurodyuusu.TextPDrinkMaxConfirmTitle.exists():
                if confirm := R.Common.ButtonConfirm.find():
                    logger.info("Confirm button found")
                    device.click(confirm)
                    return "PDrinkMax"
        return None

    @staticmethod
    def _check_skill_card_enhance(img: MatLike) -> AcquisitionType | None:
        """检查技能卡自选强化"""
        if R.InPurodyuusu.IconTitleSkillCardEnhance.exists():
            if handle_skill_card_enhance():
                return "PSkillCardEnhanceSelect"
        return None

    @staticmethod
    def _check_skill_card_removal(img: MatLike) -> AcquisitionType | None:
        """检查技能卡自选删除"""
        if R.InPurodyuusu.IconTitleSkillCardRemoval.exists():
            if handle_skill_card_removal():
                return "PSkillCardRemoveSelect"
        return None

    @staticmethod
    def _check_network_error(img: MatLike) -> AcquisitionType | None:
        """检查网络中断弹窗"""
        logger.debug("Check network error popup...")
        if (R.Common.TextNetworkError.exists()
            and (btn_retry := R.Common.ButtonRetry.find())
        ):
            logger.info("Network error popup found")
            device.click(btn_retry)
            return "NetworkError"
        return None

    @staticmethod
    def _check_award_select(img: MatLike) -> AcquisitionType | None:
        """检查物品选择对话框"""
        logger.debug("Check award select dialog...")
        if R.InPurodyuusu.TextClaim.exists():
            logger.info("Award select dialog found.")

            # P饮料选择
            logger.debug("Check PDrink select...")
            if R.InPurodyuusu.TextPDrink.exists():
                logger.info("PDrink select found")
                acquire_p_drink()
                return "PDrinkSelect"
            # 技能卡选择
            logger.debug("Check skill card select...")
            if R.InPurodyuusu.TextSkillCard.exists():
                logger.info("Acquire skill card found")
                acquire_skill_card()
                return "PSkillCardSelect"
            # P物品选择
            logger.debug("Check PItem select...")
            if R.InPurodyuusu.TextPItem.exists():
                logger.info("Acquire PItem found")
                select_p_item()
                return "PItemSelect"
        return None

    @staticmethod
    def _check_date_change(img: MatLike) -> AcquisitionType | None:
        """检查日期变更"""
        result = acquisition_date_change_dialog()
        if result is not None:
            return result
        return None

    handlers = [
        _check_loading,
        _check_skip_commu,
        _check_pdrink_max,
        _check_pdrink_max_confirm,
        _check_skill_card_enhance,
        _check_skill_card_removal,
        _check_network_error,
        _check_award_select,
        _check_date_change
    ]

    @classmethod
    @action('处理培育事件', screenshot_mode='manual')
    def check(cls) -> AcquisitionType | None:
        """处理行动开始前和结束后可能需要处理的事件"""
        img = device.screenshot()
        logger.info("Acquisition stuffs...")
        
        # 检查各个可能的中断事件        
        for handler in cls.handlers:
            result = handler(img)
            if result:
                return result
            skip()

        return None

    def resolve(self, end_condition: Callable[[], bool] | Image | None = None):
        self.cd.reset().start()
        result: Literal[False] | AcquisitionType | None = False
        for l in Loop():
            if end_condition is not None:
                if callable(end_condition) and end_condition():
                    break
                elif isinstance(end_condition, Image) and image.find(end_condition):
                    break
            else:
                if result is None:
                    break

            if self.cd.expired():
                raise UnrecoverableError("ProduceInterrupt.resolve timed out after 180 seconds")
            
            img = l.screenshot
            if img is None:
                img = device.screenshot()
            for handler in self.handlers:
                result = handler(img)
                if result:
                    break
            skip()

    def handle(self):
        """处理中断事件，并检查是否超时。"""
        if self.cd.expired():
            raise UnrecoverableError('Unable to detect produce scene. Reseason: timed out.')
        return self.check()
    
    def until(self, end_prefab: type[Prefab]):
        """
        持续处理中断事件，直到指定 Prefab 出现为止。
        """
        return self.resolve(end_prefab.exists)

def until_acquisition_clear():
    """
    处理各种奖励、弹窗，直到没有新的奖励、弹窗为止

    前置条件：任意\n
    结束条件：任意
    """
    interval = Interval(0.6)
    while ProduceInterrupt.check():
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