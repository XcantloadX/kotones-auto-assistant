import logging

from kaa.tasks import R
from kotonebot.backend.loop import Loop
from kotonebot import device, action, sleep

logger = logging.getLogger(__name__)


@action('检测是否位于首页')
def at_home() -> bool:
    return R.Daily.ButtonHomeCurrent.exists()

@action('返回首页', screenshot_mode='manual')
def goto_home():
    """
    从其他场景返回首页。

    前置条件：无 \n
    结束状态：位于首页
    """
    logger.info("Going home.")
    for _ in Loop():
        if at_home():
            logger.info("At home.")
            break
        if R.Common.ButtonHome.try_click():
            logger.debug("Clicked home button.")
            sleep(0.2)
        elif R.Common.ButtonToolbarHome.try_click():
            logger.debug("Clicked toolbar home button.")
            sleep(1)
        # 課題CLEAR [screenshots/go_home/quest_clear.png]
        elif R.Common.ButtonIconClose.try_click():
            logger.debug("Clicked close button.")
            sleep(0.2)
        logger.debug(f"Trying to go home...")

if __name__ == "__main__":
    goto_home()
