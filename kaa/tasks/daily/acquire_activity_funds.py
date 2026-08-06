"""收取活动费"""
import logging

from kaa.game_ui import dialog
from kotonebot import task, device, color, sleep, action, Loop

from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import goto_home

logger = logging.getLogger(__name__)

@action('判断活动费是否需要收取')
def need_acquire() -> bool:
    """
    判断活动费入口处是否存在需要收取的红点提示。

    前置条件：位于首页
    结束状态：无变化

    :return: 是否需要收取活动费
    """
    needed = (
        color.find('#ff6085', rect=R.Daily.ActivityFunds.EntryArea)
        or color.find('#ff1249', rect=R.Daily.ActivityFunds.EntryArea)
    ) is not None
    return needed

@task('收取活动费', screenshot_mode='manual-inherit')
def acquire_activity_funds():
    if not conf().tasks.activity_funds.enabled:
        logger.info('Activity funds acquisition is disabled.')
        return

    goto_home()
    sleep(1)
    for _ in Loop():
        # 无需收取活动费，直接结束
        if not need_acquire():
            logger.info('No activity funds to acquire.')
            break

        # 收取弹窗已出现，回首页结束
        if R.Daily.ActivityFunds.DialogTitle.exists():
            logger.debug('Activity funds dialog appeared.')
            dialog.no()
            sleep(0.5)
            break

        # 点击活动费入口
        device.click(R.Daily.ActivityFunds.EntryArea)
        sleep(0.5)

    goto_home()


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    acquire_activity_funds()