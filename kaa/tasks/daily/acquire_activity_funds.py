"""收取活动费"""
import logging

from kotonebot import task, device, color, sleep
from kotonebot.pipeline import prefab as p, dummy, Pipeline, click_first, node, sleep as make_sleep

from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import goto_home

logger = logging.getLogger(__name__)

@node
def _go_home() -> bool:
    goto_home()
    return True

def AcquireActivityFunds() -> Pipeline:
    entry = dummy()
    exit = dummy()

    click_entry = dummy([lambda c: device.click(R.Daily.ActivityFunds.EntryArea)])
    is_at_dialog = p(R.Daily.ActivityFunds.DialogTitle)
    close_dialog = p(R.Daily.ActivityFunds.DialogButtonClose, [click_first, make_sleep(1)])

    @node
    def need_acquire() -> bool:
        sleep(1)
        needed = (
            color.find('#ff6085', rect=R.Daily.ActivityFunds.EntryArea)
            or color.find('#ff1249', rect=R.Daily.ActivityFunds.EntryArea)
        ) is not None
        return needed
 
    _ = entry >> _go_home() >> [
        need_acquire() >> [
            click_entry,
            is_at_dialog >> [
                close_dialog,
                _go_home() >> exit
            ]
        ],
        exit
    ]

    return Pipeline(entry=entry, exit=exit)

@task('收取活动费', screenshot_mode='manual-inherit')
def acquire_activity_funds():
    if not conf().tasks.activity_funds.enabled:
        logger.info('Activity funds acquisition is disabled.')
        return

    AcquireActivityFunds().run(interval=1)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    acquire_activity_funds()
