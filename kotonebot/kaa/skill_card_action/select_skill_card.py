from logging import getLogger

from kotonebot import device, image, Interval, ocr, contains, Countdown, action
from kotonebot.backend.core import HintBox
from kotonebot.kaa.game_ui import dialog, badge
from kotonebot.kaa.game_ui.skill_card_select import extract_cards
from kotonebot.kaa.skill_card_action.card_reader import ActualCard
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
        skill_card_elements = extract_cards(img)
        if skill_card_elements:
            cards = [ActualCard.create_by(skill_card_element) for skill_card_element in skill_card_elements]
            cards = sorted(cards)
            target_card = cards[0]
            select_suggest = False

            # 非卡组配置的卡时，尝试刷新
            if not target_card.select():
                if try_refresh_skill_card(target_card.skill_card_element.rect):
                    it.wait()
                    continue
                # 如果没刷新次数，尝试选取除外卡,没有除外卡才选择推荐卡
                if once_cards := [card for card in cards if card.lost()]:
                    target_card = once_cards[0]
                else:
                    select_suggest = True
            if select_suggest:
                # 既没有刷新，也没有除外卡，选择推荐卡
                card_rect = find_recommended_card_rect([card.skill_card_element.rect for card in cards])
                logger.info(f"Select recommended card")
                device.click(card_rect)
            else:
                logger.info(f"Select {target_card.skill_card_element.skill_card.name}")
                device.click(target_card.skill_card_element.rect)
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


@action('寻找推荐卡', screenshot_mode='manual-inherit')
def find_recommended_card_rect(cards: list[Rect]) -> Rect:
    # 判断是否有推荐卡
    rec_badges = image.find_all(R.InPurodyuusu.TextRecommend)
    rec_badges = [card.rect for card in rec_badges]
    if rec_badges:
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
        target_card = cards[0]
    return target_card


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
