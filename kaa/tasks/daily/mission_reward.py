"""领取任务奖励"""
import logging

from kaa.tasks import R

from kotonebot.primitives import Rect
from kaa.config import conf, Priority
from ..actions.loading import wait_loading_end
from ..actions.scenes import at_home, goto_home
from kotonebot import device, image, color, task, action, rect_expand, sleep
from kotonebot.backend.loop import Loop

logger = logging.getLogger(__name__)

@action('检查任务')
def check_and_goto_mission() -> bool:
    """
    检查任务。如果需要领取，
    则前往任务页面，并返回 True。
    否则返回 False。
    
    :return: 是否需要领取任务奖励
    """
    rect = image.expect_wait(R.Daily.ButtonMission, timeout=1).rect
    # 向上、向右扩展 50px
    color_rect = rect_expand(rect, top=50, right=50)
    if not color.find('#ff1249', rect=color_rect):
        logger.info('No mission reward to claim.')
        return False
    # 点击任务奖励图标
    logger.debug('Clicking mission reward icon.')
    device.click()
    sleep(0.5)
    # 加载
    wait_loading_end()
    return True

@action('任务奖励')
def claim_mission_reward(name: str):
    """领取任务奖励"""
    # [screenshots/mission/daily.png]
    image.expect_wait(R.Common.ButtonIconArrowShort)
    if image.find(R.Common.ButtonIconArrowShort, colored=True):
        logger.info(f'Claiming {name} mission reward.')
        device.click()
        sleep(0.5)
        for _ in Loop(interval=0.5):
            if not image.find(R.Common.ButtonIconArrowShortDisabled, colored=True):
                if image.find(R.Common.ButtonIconClose):
                    logger.debug('Closing popup dialog.')
                    device.click()
                    sleep(1)
            else:
                break
    else:
        logger.info(f'No {name} mission reward to claim.')

@action('领取任务页面奖励')
def claim_mission_rewards():
    """领取任务奖励"""
    # [screenshots/mission/daily.png]
    logger.info('Claiming daily mission rewards.')
    red_dots = color.find_all('#ff1249', rect=R.Daily.BoxMissonTabs)
    logger.debug(f'Found {len(red_dots)} red dots.')
    for i, dot in enumerate(red_dots, 1):
        logger.debug(f'Red dot at {dot.position} with similarity {dot.confidence:.2f}.')
        device.click(*dot.position)
        sleep(0.2)
        claim_mission_reward(f'#{i} {dot.position}')
    logger.info('All daily mission rewards claimed.')

@action('通行证奖励')
def claim_pass_reward():
    """领取通行证奖励"""
    # [screenshots/mission/daily.png]
    pass_rect = image.expect_wait(R.Daily.ButtonIconPass, timeout=1).rect
    # 向右扩展 150px，向上扩展 35px
    color_rect = (pass_rect.x1, pass_rect.y1 - 35, pass_rect.w + 150, pass_rect.h + 35)
    if not color.find('#ff1249', rect=Rect(xywh=color_rect)):
        logger.info('No pass reward to claim.')
        return
    logger.info('Claiming pass reward.')
    logger.debug('Clicking パス button.')
    device.click()
    # [screenshots/mission/pass.png]
    # 对话框 [screenshots/mission/pass_dialog.png]
    for _ in Loop(interval=0.2):
        if image.find(R.Common.ButtonIconClose):
            logger.debug('Closing popup dialog.')
            device.click()
        elif image.find(R.Daily.IconTitlePass):
            break
    logger.debug('Pass screen loaded.')
    for _ in Loop():
        if image.find(R.Common.ButtonIconClose):
            logger.debug('Closing popup dialog.')
            device.click()
        elif image.find(R.Daily.ButtonPassClaim, colored=True):
            logger.debug('Clicking 受取 button.')
            device.click()
        elif not image.find(R.Daily.ButtonPassClaim, colored=True) and image.find(R.Daily.IconTitlePass):
            break
    logger.info('All pass rewards claimed.')

@action('活动奖励')
def claim_event_reward():
    """领取活动奖励"""
    # TODO: 领取活动奖励
    pass

@task('领取任务奖励', priority=Priority.CLAIM_MISSION_REWARD)
def mission_reward():
    """
    领取任务奖励
    """
    if not conf().mission_reward.enabled:
        logger.info('Mission reward is disabled.')
        return
    logger.info('Claiming mission rewards.')
    if not at_home():
        goto_home()
    # TODO: 这个 MISSION 按钮上的红点只会指示 MISSON 的领取
    # PASS 的领取需要另外判断
    if not check_and_goto_mission():
        return
    image.expect_wait(R.Daily.ButtonIconPass)
    claim_mission_rewards()
    sleep(0.5)
    claim_pass_reward()
    logger.info('All mission rewards claimed.')


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logging.getLogger('kotonebot').setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    
    # if image.find(R.Common.CheckboxUnchecked):
    #     logger.debug('Checking skip all.')
    #     device.click()
    #     sleep(0.5)
    # device.click(image.expect(R.Daily.ButtonIconSkip, colored=True, transparent=True, threshold=0.999))
    # mission_reward()
    claim_pass_reward()
    # claim_mission_rewards()
