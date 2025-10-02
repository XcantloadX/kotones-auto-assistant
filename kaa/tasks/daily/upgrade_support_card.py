"""升级一张支援卡，优先升级低等级支援卡"""
import logging

from kaa.tasks import R
from kaa.config import conf
from kaa.game_ui.scrollable import Scrollable
from ..actions.scenes import at_home, goto_home
from kotonebot import task, device, image, sleep

logger = logging.getLogger(__name__)

@task('升级一张低等级支援卡')
def upgrade_support_card():
    """
    升级一张支援卡，优先升级低等级支援卡
    """
    # 自动化思路是这样的：
    # 进入支援卡页面后，一直往下滑，滑倒底部（低等级支援卡区域）；
    # 然后点击左上角第一张支援卡，将左上角第一张支援卡提升一级。

    if not conf().upgrade_support_card.enabled:
        logger.info('"Upgrade support card" is disabled.')
        return
    
    if not at_home():
        goto_home()
    
    # 进入支援卡页面
    logger.info('Entering Support Card page')
    device.click(image.expect_wait(R.Common.ButtonIdol, timeout=5))
    device.click(image.expect_wait(R.Common.ButtonIdolSupportCard, timeout=5))
    sleep(2)

    # 往下滑，划到最底部
    Scrollable().to(1)
    
    # 点击左上角第一张支援卡
    # 点击位置百分比: (0.18, 0.34)
    # 720p缩放后的位置: (130, 435)
    for _ in range(2):
        device.click(
            R.Daily.SupportCard.TargetSupportCard.x,
            R.Daily.SupportCard.TargetSupportCard.y
        )
        sleep(0.5)
    
    # 点击两次升级按钮（两个按钮的logo不一样，但是文字是一样的，这里资源文件只包含文字）
    device.click(image.expect_wait(R.Daily.ButtonSupportCardUpgrade, timeout=5))
    sleep(0.5)
    device.click(image.expect_wait(R.Daily.ButtonSupportCardUpgrade, timeout=5))
    sleep(1)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    upgrade_support_card()

