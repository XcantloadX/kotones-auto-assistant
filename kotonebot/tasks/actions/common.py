from typing import Literal
from logging import getLogger
from time import sleep

from kotonebot import (
    ocr,
    device,
    contains,
    image,
    grayscaled,
    grayscale_cached,
    action
)
from .. import R
from .pdorinku import acquire_pdorinku

logger = getLogger(__name__)

@action('领取技能卡')
def acquire_skill_card():
    """获取技能卡（スキルカード）"""
    # TODO: 识别卡片内容，而不是固定选卡
    # TODO: 不硬编码坐标
    CARD_POSITIONS = [
        (157, 820, 128, 128),
        (296, 820, 128, 128),
        (435, 820, 128, 128),
    ]
    logger.info("Click first skill card")
    device.click(CARD_POSITIONS[0])
    sleep(0.5)
    # 确定
    logger.info("Click 受け取る")
    device.click(ocr.expect(contains("受け取る")).rect)
    # 跳过动画
    device.click(image.expect_wait_any([
        R.InPurodyuusu.PSkillCardIconBlue,
        R.InPurodyuusu.PSkillCardIconColorful
    ]))

AcquisitionType = Literal[
    "PDrinkAcquire", # P饮料被动领取
    "PDrinkSelect", # P饮料主动领取
    "PDrinkMax", # P饮料到达上限
    "PSkillCardAcquire", # 技能卡领取
    "PSkillCardSelect", # 技能卡选择
    "PItem", # P物品
    "Clear", # 目标达成
]

@action('检测并领取奖励')
def acquisitions() -> AcquisitionType | None:
    """处理行动开始前和结束后可能需要处理的事件，直到到行动页面为止"""
    img = device.screenshot_raw()
    gray_img = grayscaled(img)
    logger.info("Acquisition stuffs...")

    # P饮料被动领取
    logger.info("Check PDrink acquisition...")
    if image.raw().find(img, R.InPurodyuusu.PDrinkIcon):
        logger.info("Click to finish animation")
        device.click_center()
        sleep(1)
        return "PDrinkAcquire"
    # P饮料主动领取
    # if ocr.raw().find(img, contains("受け取るＰドリンクを選れでください")):
    if image.raw().find(img, R.InPurodyuusu.TextPleaseSelectPDrink):
        logger.info("PDrink acquisition")
        # 不领取
        # device.click(ocr.expect(contains("受け取らない")))
        # sleep(0.5)
        # device.click(image.expect(R.InPurodyuusu.ButtonNotAcquire))
        # sleep(0.5)
        # device.click(image.expect(R.InPurodyuusu.ButtonConfirm))
        acquire_pdorinku(index=0)
        return "PDrinkSelect"
    # P饮料到达上限
    if image.raw().find(img, R.InPurodyuusu.TextPDrinkMax):
        device.click(image.expect(R.InPurodyuusu.ButtonLeave))
        sleep(0.7)
        # 可能需要点击确认
        device.click(image.expect(R.Common.ButtonConfirm, threshold=0.8))
        return "PDrinkMax"
    # 技能卡被动领取（支援卡效果）
    logger.info("Check skill card acquisition...")
    if image.raw().find_any(img, [
        R.InPurodyuusu.PSkillCardIconBlue,
        R.InPurodyuusu.PSkillCardIconColorful
    ]):
        logger.info("Acquire skill card")
        device.click_center()
        return "PSkillCardAcquire"
    # 技能卡选择
    if ocr.raw().find(img, contains("受け取るスキルカードを選んでください")):
        logger.info("Acquire skill card")
        acquire_skill_card()
        sleep(5)
        return "PSkillCardSelect"
    # 奖励箱技能卡
    if res := image.raw().find(gray_img, grayscaled(R.InPurodyuusu.LootBoxSkillCard)):
        logger.info("Acquire skill card from loot box")
        device.click(res.rect)
        # 下面就是普通的技能卡选择
        return acquisitions()
    # 目标达成
    if image.raw().find(gray_img, grayscale_cached(R.InPurodyuusu.IconClearBlue)):
        logger.debug("達成: clicked")
        device.click_center()
        sleep(5)
        # TODO: 可能不存在 達成 NEXT
        logger.debug("達成 NEXT: clicked")
        device.click_center()
        return "Clear"
    # P物品
    if image.raw().find(img, R.InPurodyuusu.PItemIconColorful):
        logger.info("Click to finish PItem acquisition")
        device.click_center()
        sleep(1)
        return "PItem"
    # 支援卡
    # logger.info("Check support card acquisition...")
    # 记忆
    # 未跳过剧情
    return None

if __name__ == '__main__':
    from logging import getLogger
    import logging
    from kotonebot.backend.context import init_context
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    getLogger('kotonebot').setLevel(logging.DEBUG)
    getLogger(__name__).setLevel(logging.DEBUG)
    init_context()
    acquisitions()
