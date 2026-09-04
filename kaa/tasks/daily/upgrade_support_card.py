"""升级一张支援卡，优先升级低等级支援卡"""
import logging

from kotonebot import task, device, Loop, sleep

from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import at_home, goto_home

logger = logging.getLogger(__name__)

@task('升级一张低等级支援卡')
def upgrade_support_card():
    """
    升级一张支援卡，优先升级低等级支援卡
    """
    # 自动化思路是这样的：
    # 进入支援卡页面后，一直往下滑，滑倒底部（低等级支援卡区域）；
    # 然后点击左上角第一张支援卡，将左上角第一张支援卡提升一级。

    if not conf().tasks.upgrade_support_card.enabled:
        logger.info('"Upgrade support card" is disabled.')
        return
    
    if not at_home():
        goto_home()
    
    # 进入支援卡页面
    logger.info('Entering Support Card page')
    for _ in Loop():
        if R.Common.ButtonIdolSupportCard.try_click():
            continue
        if R.Common.ButtonIdol.try_click():
            continue
        if R.Daily.SupportCard.ButtonSeeDetails.exists():
            break

    # 重试10次
    for retry_idx in range(10):
        logger.debug(f'Scrolling down to find low-level support cards, attempt {retry_idx + 1}/10')
        # 往下滑，划到最底部
        scrollbar = R.Daily.SupportCard.Scrollbar.require()
        scrollbar.to(1)
        sleep(0.1)
        scrollbar.update()
        if (scrollbar.position or 0) >= 0.99:
            logger.debug('Successfully scrolled to the bottom.')
            break
        sleep(0.5)
    
    # 点击左上角第一张支援卡
    # 点击位置百分比: (0.18, 0.34)
    # 720p缩放后的位置: (130, 435)
    for _ in range(2):
        device.click(R.Daily.SupportCard.TargetSupportCard)
        sleep(0.5)
    
    # 点击两次升级按钮
    for _ in Loop():
        if R.Daily.SupportCard.ButtonUpgrade.try_click():
            logger.debug('Clicked ButtonUpgrade')
            sleep(1)
            continue
        if R.Daily.SupportCard.ButtonUpgrade2.try_click():
            logger.debug('Clicked ButtonUpgrade')
            sleep(1)
            break

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    upgrade_support_card()
