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
from kotonebot.tasks.actions.commu import check_and_skip_commu
from .loading import loading, wait_loading_end
from .. import R
from .pdorinku import acquire_pdorinku

logger = getLogger(__name__)

@action('领取技能卡')
def acquire_skill_card():
    """获取技能卡（スキルカード）"""
    # TODO: 识别卡片内容，而不是固定选卡
    # TODO: 不硬编码坐标
    logger.debug("Locating all skill cards...")
    cards = image.find_all_multi([
        R.InPurodyuusu.A,
        R.InPurodyuusu.M
    ])
    cards = sorted(cards, key=lambda x: (x.position[0], x.position[1]))
    logger.info(f"Found {len(cards)} skill cards")
    logger.debug("Click first skill card")
    device.click(cards[0].rect)
    sleep(0.5)
    # 确定
    logger.debug("Click 受け取る")
    device.click(ocr.expect(contains("受け取る")).rect)
    # 跳过动画
    device.click(image.expect_wait_any([
        R.InPurodyuusu.PSkillCardIconBlue,
        R.InPurodyuusu.PSkillCardIconColorful
    ], timeout=60))
    logger.info("Skill card #1 acquired")

AcquisitionType = Literal[
    "PDrinkAcquire", # P饮料被动领取
    "PDrinkSelect", # P饮料主动领取
    "PDrinkMax", # P饮料到达上限
    "PSkillCardAcquire", # 技能卡领取
    "PSkillCardChange", # 技能卡更换
    "PSkillCardSelect", # 技能卡选择
    "PSkillCardEnhance", # 技能卡强化
    "PItem", # P物品
    "Clear", # 目标达成
    "NetworkError", # 网络中断弹窗
    "SkipCommu", # 跳过交流
]

@action('检测并领取奖励')
# TODO: 这个函数可能要换个更好的名字
def acquisitions() -> AcquisitionType | None:
    """处理行动开始前和结束后可能需要处理的事件，直到到行动页面为止"""
    img = device.screenshot_raw()
    gray_img = grayscaled(img)
    ocr_results = ocr.raw().ocr(img)
    ocr_text = ''.join(r.text for r in ocr_results)
    logger.info("Acquisition stuffs...")

    # P饮料被动领取
    if image.raw().find(img, R.InPurodyuusu.PDrinkIcon):
        logger.info("PDrink acquire found")
        device.click_center()
        sleep(1)
        return "PDrinkAcquire"
    # P饮料主动领取
    # if ocr.raw().find(img, contains("受け取るＰドリンクを選れでください")):
    if image.raw().find(img, R.InPurodyuusu.TextPleaseSelectPDrink):
        logger.info("PDrink select found")
        acquire_pdorinku(index=0)
        return "PDrinkSelect"
    # P饮料到达上限
    if image.raw().find(img, R.InPurodyuusu.TextPDrinkMax):
        logger.info("PDrink max found")
        device.click(image.expect(R.InPurodyuusu.ButtonLeave))
        sleep(0.7)
        # 可能需要点击确认
        device.click(image.expect(R.Common.ButtonConfirm, threshold=0.8))
        return "PDrinkMax"
    # 技能卡被动领取（支援卡效果）
    logger.info("Check skill card acquisition...")
    if image.raw().find_multi(img, [
        R.InPurodyuusu.PSkillCardIconBlue,
        R.InPurodyuusu.PSkillCardIconColorful
    ]):
        logger.info("Acquire skill card found")
        device.click_center()
        return "PSkillCardAcquire"
    # 技能卡更换（支援卡效果）
    # [screenshots/produce/in_produce/support_card_change.png]
    if 'チェンジ' in ocr_text:
        logger.info("Change skill card found")
        device.click_center()
        return "PSkillCardChange"
    # 技能卡强化
    # [screenshots/produce/in_produce/skill_card_enhance.png]
    if '強化' in ocr_text:
        logger.info("Enhance skill card found")
        device.click_center()
        return "PSkillCardEnhance"
    # 技能卡选择
    if '受け取るスキルカードを選んでください' in ocr_text:
        logger.info("Acquire skill card found")
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
        logger.info("Clear found")
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
    # 网络中断弹窗
    if image.raw().find(img, R.Common.TextNetworkError):
        logger.info("Network error popup found")
        device.click(image.expect(R.Common.ButtonRetry))
        return "NetworkError"
    # 加载画面
    if loading():
        logger.info("Loading screen found")
        wait_loading_end()
    # 支援卡
    # logger.info("Check support card acquisition...")
    # 记忆
    # 跳过未读交流
    if check_and_skip_commu(img):
        return "SkipCommu"
    # TODO: 在这里加入定时点击以避免再某个地方卡住
    return None

if __name__ == '__main__':
    from logging import getLogger
    import logging
    from kotonebot.backend.context import init_context
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    getLogger('kotonebot').setLevel(logging.DEBUG)
    getLogger(__name__).setLevel(logging.DEBUG)
    init_context()
