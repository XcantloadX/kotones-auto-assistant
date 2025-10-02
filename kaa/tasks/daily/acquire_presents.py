"""领取礼物（邮箱）"""
import logging

from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import at_home, goto_home
from kotonebot import device, image, task, color, rect_expand, sleep

logger = logging.getLogger(__name__)

@task('领取礼物')
def acquire_presents():
    if not conf().presents.enabled:
        logger.info('Presents acquisition is disabled.')
        return

    if not at_home():
        goto_home()
    present = image.expect_wait(R.Daily.ButtonPresentsPartial, timeout=1)
    rect = present.rect
    # 判断是否存在未领取礼物
    color_rect = rect_expand(rect, top=50, right=50)
    if not color.find('#ff1249', rect=color_rect):
        logger.info('No presents to claim.')
        return
    # 点击礼物图标
    logger.debug('Clicking presents icon.')
    device.click()
    logger.debug('Claiming presents.')
    device.click(image.expect_wait(R.Daily.ButtonClaimAllNoIcon, timeout=5))
    logger.debug('Cliking close button.')
    device.click(image.expect_wait(R.Common.ButtonClose, timeout=5))
    logger.info('Claimed presents.')
    sleep(0.7)
    goto_home()

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    # acquire_presents()
    print(image.find(R.Common.ButtonIconArrowShort, colored=True))
    print(image.find(R.Common.ButtonIconArrowShortDisabled, colored=True))

