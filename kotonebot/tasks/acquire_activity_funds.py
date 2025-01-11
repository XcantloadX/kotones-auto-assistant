"""收取活动费"""
import logging

from kotonebot import task, device, image, cropped
from .actions.scenes import at_home, goto_home
from . import R

logger = logging.getLogger(__name__)

@task('收取活动费')
def acquire_activity_funds():
    if not at_home():
        goto_home()
    if image.find(R.Daily.TextActivityFundsMax):
        logger.info('Activity funds maxed out.')
        device.click()
        device.click(image.expect_wait(R.InPurodyuusu.ButtonClose, timeout=2))
        logger.info('Activity funds acquired.')
    else:
        logger.info('Activity funds not maxed out. No action needed.')


if __name__ == '__main__':
    from kotonebot.backend.context import init_context
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    init_context()
    acquire_activity_funds()
