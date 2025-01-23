"""领取任务奖励"""
import logging

from . import R
from .common import conf, Priority
from .actions.loading import wait_loading_end
from .actions.scenes import at_home, goto_home
from kotonebot import device, image, color, task, action, rect_expand, sleep

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
    if not color.find_rgb('#ff1249', rect=color_rect):
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
    if image.find(R.Common.ButtonIconArrowShort, colored=True):
        logger.info(f'Claiming {name} mission reward.')
        device.click()
        sleep(0.5)
        while not image.find(R.Common.ButtonIconArrowShortDisabled, colored=True):
            if image.find(R.Common.ButtonIconClose):
                logger.debug('Closing popup dialog.')
                device.click()
                sleep(1)
            sleep(0.5)
    else:
        logger.info(f'No {name} mission reward to claim.')

@action('领取任务页面奖励')
def claim_mission_rewards():
    """领取任务奖励"""
    # [screenshots/mission/daily.png]
    # デイリー Daily
    claim_mission_reward('デイリー')
    # ウィークリー Weekly
    device.swipe_scaled(0.8, 0.5, 0.2, 0.5)
    sleep(0.5)
    claim_mission_reward('ウィークリー')
    # ノーマル Normal
    device.swipe_scaled(0.8, 0.5, 0.2, 0.5)
    sleep(0.5)
    claim_mission_reward('ノーマル')
    # 期間限定
    device.swipe_scaled(0.8, 0.5, 0.2, 0.5)
    sleep(0.5)
    claim_mission_reward('期間限定')
    

@action('通行证奖励')
def claim_pass_reward():
    """领取通行证奖励"""
    # [screenshots/mission/daily.png]
    pass_rect = image.expect_wait(R.Daily.ButtonIconPass, timeout=1).rect
    # 向右扩展 150px，向上扩展 35px
    color_rect = (pass_rect[0], pass_rect[1] - 35, pass_rect[2] + 150, pass_rect[3] + 35)
    if not color.find_rgb('#ff1249', rect=color_rect):
        logger.info('No pass reward to claim.')
        return
    logger.info('Claiming pass reward.')
    logger.debug('Clicking パス button.')
    device.click()
    sleep(0.5)
    # [screenshots/mission/pass.png]
    # 对话框 [screenshots/mission/pass_dialog.png]
    while not image.find(R.Daily.IconTitlePass):
        if image.find(R.Common.ButtonIconClose):
            logger.debug('Closing popup dialog.')
            device.click()
            sleep(1)
        sleep(0.5)
    logger.debug('Pass screen loaded.')
    while image.find(R.Daily.ButtonPassClaim, colored=True):
        logger.debug('Clicking 受取 button.')
        device.click()
        sleep(1.5)
        while not image.find(R.Daily.ButtonPassClaim):
            if image.find(R.Common.ButtonIconClose):
                logger.debug('Closing popup dialog.')
                device.click()
                sleep(1)
            sleep(0.5)
        sleep(1.5)
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
    if not check_and_goto_mission():
        return
    sleep(0.7)
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
