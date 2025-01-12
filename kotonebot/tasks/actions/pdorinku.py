from time import sleep
from logging import getLogger

from kotonebot import device, ocr, image, Rect, action
from kotonebot.backend.util import contains
from .. import R

logger = getLogger(__name__)

# TODO: 加入一个 device.snapshot() 方法，用于保存当前设备画面，避免重复截图。
# TODO: 比较 OCR 和模板匹配文字的性能，如果模板匹配更好，
# 则首次使用 OCR，找到结果后自动截图，后续使用模板匹配。

@action('检测是否在 P 饮料领取中')
def is_on_pdorinku_acquisition() -> bool:
    """检查是否在 P 饮料领取中"""
    return ocr.find('受け取るＰドリンクを選んでください。') is not None

@action('列出当前要领取的 P 饮料')
def list_pdorinku() -> list[tuple[str, Rect]]:
    """
    列出当前要领取的 P 饮料

    :return: 检测结果。`[(饮料名称, 饮料矩形坐标), ...]`
    """
    # 截图所有饮料
    # TODO: 自动记录未知饮料
    dorinkus = image.find_crop_many(
        R.InPurodyuusu.Action.PDorinkuBg,
        mask=R.InPurodyuusu.Action.PDorinkuBgMask,
    )
    return [
        ('', dorinku.rect) # TODO: 获取饮料名称
        for dorinku in dorinkus
    ]

@action('领取 P 饮料')
def acquire_pdorinku(index: int):
    """
    领取 P 饮料
    :param index: 要领取的 P 饮料的索引。从 0 开始。
    """
    # TODO: 随机领取一个饮料改成根据具体情况确定最佳
    # 如果能不领取，就不领取
    if ocr.find(contains('受け取らない')):
        device.click()
        sleep(0.5)
        device.click(image.expect(R.InPurodyuusu.ButtonNotAcquire))
        sleep(0.5)
        device.click(image.expect(R.Common.ButtonConfirm))
    else:
        # 点击饮料
        drinks = list_pdorinku()
        dorinku = drinks[index]
        device.click(dorinku[1])
        logger.debug(f"Pドリンク clicked: {dorinku[0]}")
        sleep(0.3)
        # 确定按钮
        ret = ocr.expect('受け取る')
        device.click(ret.rect)
        logger.debug("受け取る clicked")
        sleep(1.3)
        # 再次确定
        device.click_center()
        logger.debug("再次确定 clicked")


__actions__ = [acquire_pdorinku]

if __name__ == '__main__':
    from pprint import pprint as print
    # print(list_pdorinku())
    acquire_pdorinku(0)
    input()
