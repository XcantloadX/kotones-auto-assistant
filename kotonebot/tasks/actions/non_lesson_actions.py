"""
此文件包含非练习周的行动。

具体包括：おでかけ、相談、活動支給、授業
"""
from time import sleep
from logging import getLogger

from kotonebot import device, image, ocr, debug, action
from kotonebot.tasks import R
from ..actions.loading import wait_loading_end, wait_loading_start
from .common import acquisitions, AcquisitionType

logger = getLogger(__name__)

@action('检测是否可以执行活動支給')
def allowance_available():
    """
    判断是否可以执行活動支給。
    """
    return image.expect(R.InPurodyuusu.ButtonTextAllowance) is not None

@action('检测是否可以执行授業')
def study_available():
    """
    判断是否可以执行授業。
    """
    return image.expect(R.InPurodyuusu.ButtonTextStudy) is not None

@action('执行授業')
def enter_study():
    """
    执行授業。
    """
    raise NotImplementedError("授業功能未实现")

@action('执行活動支給')
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
    wait_loading_end()
    # 处理可能会出现的支援卡奖励
    while not image.find(R.InPurodyuusu.IconTitleAllowance):
        logger.debug("Waiting for 活動支給 screen.")
        acquisitions()
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
    # wait_loading_start() # 可能会因为加载太快，截图没截到，导致抛出异常
    sleep(1)
    wait_loading_end()
    # 可能会出现的新动画
    # 技能卡：[screenshots\allowance\step_4.png]


def study():
    """授業"""
    pass