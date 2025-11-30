from logging import getLogger

from kaa.tasks import R
from kotonebot.primitives import Rect
from kotonebot import device, image, action, sleep

logger = getLogger(__name__)

# 三个饮料的坐标
POSTIONS = [
    Rect(157, 820, 128, 128),  # x, y, w, h
    Rect(296, 820, 128, 128),
    Rect(435, 820, 128, 128),
]  # TODO: HARD CODED

@action('领取 P 饮料')
def acquire_p_drink():
    """
    领取 P 饮料

    前置：领取饮料弹窗

    :param index: 要领取的 P 饮料的索引。从 0 开始。
    """
    # TODO: 随机领取一个饮料改成根据具体情况确定最佳
    # 如果能不领取，就不领取
    if image.find(R.InPurodyuusu.TextDontClaim):
        # [kotonebot-resource/sprites/jp/in_purodyuusu/screenshot_select_p_drink_full.png]
        logger.info("Skip claiming PDrink.")
        device.click()
        sleep(0.3)
        if image.find(R.InPurodyuusu.ButtonDontClaim):
            device.click()
    else:
        # 点击饮料
        device.click(POSTIONS[0])
        logger.debug(f"PDrink clicked: {POSTIONS[0]}")
        sleep(0.3)
        # 确定按钮
        if image.find(R.InPurodyuusu.AcquireBtnDisabled):
            device.click()
            logger.debug("受け取る clicked")


if __name__ == '__main__':
    acquire_p_drink()
    input()
