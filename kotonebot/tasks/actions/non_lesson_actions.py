"""
此文件包含非练习周的行动。

具体包括：おでかけ、相談、活動支給、授業
"""
from time import sleep
from logging import getLogger

from kotonebot import device, image, ocr, debug
from kotonebot.tasks import R
from .common import acquisitions, AcquisitionType

logger = getLogger(__name__)

def allowance_available():
    """
    判断是否可以执行活動支給。
    """
    return image.expect(R.InPurodyuusu.ButtonTextAllowance) is not None

def study_available():
    """
    判断是否可以执行授業。
    """
    return image.expect(R.InPurodyuusu.ButtonTextStudy) is not None

def enter_study():
    """
    执行授業。
    """
    raise NotImplementedError("授業功能未实现")

def enter_allowance():
    """
    执行活動支給。
    
    前置条件：位于行动页面，且所有行动按钮清晰可见 \n
    结束状态：无
    """
    logger.info("Executing 活動支給.")
    # 点击活動支給 [screenshots\allowance\step_1.png]
    logger.info("Double clicking on 活動支給.")
    device.double_click(image.expect(R.InPurodyuusu.ButtonTextAllowance), interval=1)
    # 等待进入页面
    sleep(3)
    # 第一个箱子 [screenshots\allowance\step_2.png]
    logger.info("Clicking on the first lootbox.")
    device.click(image.expect_wait_any([
        R.InPurodyuusu.LootboxSliverLock
    ]))
    while acquisitions() is None:
        logger.info("Waiting for acquisitions finished.")
        sleep(2)
    # 第二个箱子
    logger.info("Clicking on the second lootbox.")
    device.click(image.expect_wait_any([
        R.InPurodyuusu.LootboxSliverLock
    ]))
    while acquisitions() is None:
        logger.info("Waiting for acquisitions finished.")
        sleep(2)
    logger.info("活動支給 completed.")
    # 可能会出现的新动画
    # 技能卡：[screenshots\allowance\step_4.png]


def study():
    """授業"""
    pass