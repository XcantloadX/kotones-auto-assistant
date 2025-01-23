"""收取活动费"""
import logging

from . import R
from .common import conf, BaseConfig
from .actions.scenes import at_home, goto_home
from kotonebot import task, device, image, cropped, sleep

logger = logging.getLogger(__name__)

@task('收取活动费')
def acquire_activity_funds():
    if not conf().activity_funds.enabled:
        logger.info('Activity funds acquisition is disabled.')
        return

    if not at_home():
        goto_home()
    sleep(1)
    if image.find(R.Daily.TextActivityFundsMax):
        logger.info('Activity funds maxed out.')
        device.click()
        device.click(image.expect_wait(R.Common.ButtonClose, timeout=2))
        logger.info('Activity funds acquired.')
    else:
        logger.info('Activity funds not maxed out. No action needed.')


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    acquire_activity_funds()
