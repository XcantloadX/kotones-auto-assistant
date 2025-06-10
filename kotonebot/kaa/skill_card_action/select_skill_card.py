from logging import getLogger

from kotonebot import device, image, Interval, ocr, contains, Countdown, action
from kotonebot.backend.core import HintBox
from kotonebot.kaa.game_ui import dialog, badge
from kotonebot.kaa.game_ui.skill_card_select import extract_cards
from kotonebot.kaa.skill_card.enum_constant import CardPriority
from kotonebot.kaa.skill_card_action.card_reader import ActualCard
from kotonebot.kaa.skill_card_action.global_idol_setting_action import idol_setting
from kotonebot.kaa.tasks import R
from kotonebot.primitives import Rect

logger = getLogger(__name__)

# 除外技能卡按钮位置
RemoveSkillButton = HintBox(x1=90, y1=1076, x2=200, y2=1115, source_resolution=(720, 1280))
# 除外技能卡确认按钮位置
RemoveConfirmButton = HintBox(x1=440, y1=1125, x2=600, y2=1190, source_resolution=(720, 1280))
# 再抽選按钮位置
RefreshSkillButton = HintBox(x1=570, y1=1076, x2=655, y2=1115, source_resolution=(720, 1280))


@action('获取技能卡', screenshot_mode='manual-inherit')
def select_skill_card():
    """获取技能卡（スキルカード）"""
    logger.debug("Locating all skill cards...")

    it = Interval(0.5)
    cd = Countdown(sec=60).start()
    while not cd.expired():
        device.screenshot()
        it.wait()

        # 是否显示技能卡选择指导的对话框
        # [kotonebot-resource/sprites/jp/in_purodyuusu/screenshot_show_skill_card_select_guide_dialog.png]
        if image.find(R.InPurodyuusu.TextSkillCardSelectGuideDialogTitle):
            # 默认就是显示，直接确认
            dialog.yes()
            continue

        img = device.screenshot()
        match_results = image.find_multi([
            R.InPurodyuusu.A,
            R.InPurodyuusu.M
        ])
        if match_results:
            cards = extract_cards(img)
            cards = [ActualCard.create_by(card.rect, card.skill_card) for card in cards]

            target_card = sorted(cards, key=lambda x: x.priority)[0]
            select_other = target_card.priority == CardPriority.other

            # 非卡组配置的卡时，判断是否需要刷新
            if select_other:
                # 若考虑先刷新，则尝试刷新，刷新成功则重新识别卡
                if not idol_setting.select_once_card_before_refresh:
                    if try_refresh_skill_card(target_card.rect):
                        it.wait()
                        continue
                # 选择一回一次的卡，如果没有，尝试刷新，刷新成功则重新识别卡
                if once_cards := [card for card in cards if card.skill_card.once]:
                    target_card = once_cards[0]
                elif try_refresh_skill_card(target_card.rect):
                    it.wait()
                    continue

            logger.info(f"select {target_card.name}")
            device.click(target_card.rect)
            it.wait()

        else:
            logger.info("No skill card found, retrying...")
            continue

        device.screenshot()
        it.wait()
        if acquire_btn := image.find(R.InPurodyuusu.AcquireBtnDisabled):
            logger.debug("Click acquire button")
            device.click(acquire_btn)
            return
    logger.warning("Skill card select failed")


@action('刷新技能卡', screenshot_mode='manual-inherit')
def try_refresh_skill_card(first_card: Rect) -> bool:
    """
    尝试刷新
    :param first_card: 选择“除去”的卡的位置
    :return: True为成功刷新
    """
    device.screenshot()
    it = Interval(0.5)
    if ocr.find(contains("除去"), rect=RemoveSkillButton):
        device.click(first_card)
        device.screenshot()
        it.wait()
        device.click(RemoveSkillButton)
        cd = Countdown(sec=5).start()
        # 等待除去页面
        while not ocr.find(contains("除去"), rect=RemoveConfirmButton):
            if cd.expired():
                break
            device.screenshot()
            it.wait()
        device.click(RemoveConfirmButton)
        cd.reset()
        # 回到领取技能卡页面
        while not image.find(R.InPurodyuusu.TextClaim):
            if cd.expired():
                break
            device.click(10, 10)
            device.screenshot()
            it.wait()
        logger.info("Remove success")
        return True
    if ocr.find(contains("再抽選"), rect=RefreshSkillButton):
        device.click(RefreshSkillButton)
        logger.info("Refresh success")
        it.wait()
        return True
    logger.info("No Refresh")
    it.wait()
    return False
