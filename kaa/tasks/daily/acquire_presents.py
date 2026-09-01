"""领取礼物（邮箱）"""
import logging

from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import at_home, goto_home
from kotonebot import device, task, color, rect_expand, sleep
from kotonebot.backend.loop import Loop

logger = logging.getLogger(__name__)

@task('领取礼物')
def acquire_presents():
    if not conf().tasks.presents.enabled:
        logger.info('Presents acquisition is disabled.')
        return


    goto_home()

    for _ in Loop():
        if R.Daily.Presents.ButtonClaimAllNoIcon.exists():
            logger.debug('Presents page is already open.')
            if R.Daily.Presents.ButtonClaimAllNoIcon.q(enabled=False).exists():
                logger.info('No presents to claim.')
                return
            break

        # 尝试进入礼物页面
        R.Daily.ButtonPresentsPartial.try_click()
        sleep(1)

    # 领取全部礼物并关闭页面
    logger.debug('Claiming presents.')
    for _ in Loop():
        if R.Daily.Presents.ButtonClaimAllNoIcon.try_click():
            logger.debug('Clicked claim all button.')
            sleep(1)
        elif R.Common.ButtonClose.try_click():
            logger.debug('Clicked close button.')
            sleep(1)
            break
    logger.info('Claimed presents.')
    goto_home()

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    # acquire_presents()
    # print(image.find(R.Common.ButtonIconArrowShort, colored=True))