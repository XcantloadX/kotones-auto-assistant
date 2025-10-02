"""收取活动费"""
import logging

from kotonebot.backend.loop import Loop
from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import at_home, goto_home
from kotonebot import task, device, image, color

logger = logging.getLogger(__name__)

@task('收取活动费', screenshot_mode='manual-inherit')
def acquire_activity_funds():
    if not conf().activity_funds.enabled:
        logger.info('Activity funds acquisition is disabled.')
        return

    if not at_home():
        goto_home()
    
    for _ in Loop():
        if (
            not color.find('#ff1249', rect=R.Daily.BoxHomeActivelyFunds)
            and at_home()
        ): 
            break
        elif image.find(R.Common.ButtonClose):
            logger.info('Closing popup dialog.')
            device.click()
        else:
            device.click(R.Daily.BoxHomeActivelyFunds)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    acquire_activity_funds()
