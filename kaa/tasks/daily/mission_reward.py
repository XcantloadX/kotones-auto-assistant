"""领取任务奖励"""
import logging

from kaa.tasks import R

from kaa.config import Priority
from ..actions.scenes import goto_home
from kotonebot import device, task, action, sleep
from kotonebot.backend.loop import Loop

logger = logging.getLogger(__name__)

@action('任务奖励')
def claim_mission_reward(name: str):
    """领取任务奖励"""
    # [screenshots/mission/daily.png]
    R.Daily.MissonRewards.ButtonClaim.wait()
    if R.Daily.MissonRewards.ButtonClaim.q(enabled=True).try_click():
        logger.info(f'Claiming {name} mission reward.')
        sleep(0.5)
        for _ in Loop(interval=0.5):
            if not R.Daily.MissonRewards.ButtonClaim.q(enabled=False).exists():
                if R.Common.ButtonIconClose.try_click():
                    logger.debug('Closed popup dialog.')
                    sleep(1)
            else:
                break
    else:
        logger.info(f'No {name} mission reward to claim.')

@action('领取任务页面奖励')
def claim_mission_rewards():
    """领取任务奖励"""
    goto_home()

    for _ in Loop(interval=0.5):
        if R.Daily.MissonRewards.TitleIcon.exists():
            logger.debug('Pass screen loaded.')
            sleep(1)
            break
        R.Daily.ButtonMission.try_click()
        logger.debug('Clicking 任务 button.')

    device.click(R.Daily.MissonRewards.PointDaily)
    sleep(1.5)
    if R.Daily.MissonRewards.ButtonClaim.q(enabled=True).exists():
        claim_mission_reward('daily')

    device.click(R.Daily.MissonRewards.PointWeekly)
    sleep(1.5)
    if R.Daily.MissonRewards.ButtonClaim.q(enabled=True).exists():
        claim_mission_reward('weekly')

@action('通行证奖励')
def claim_pass_reward():
    """领取通行证奖励"""
    goto_home()

    for _ in Loop(interval=0.5):
        if R.Daily.PassRewards.IconTitle.exists():
            logger.debug('Pass screen loaded.')
            break
        R.Daily.ButtonPass.try_click()
        logger.debug('Clicking パス button.')

    sc = R.Daily.PassRewards.Scrollbar.require()
    for _ in sc(step=0.1, start=None):
        # 先扫描所有领取按钮并尝试挨个领取
        for _ in Loop():
            if R.Daily.PassRewards.ButtonClaim.exists():
                # 点击并等待弹窗
                for _ in Loop():
                    if R.Common.ButtonIconClose.exists():
                        logger.debug('Now at popup dialog.')
                        break
                    # TODO: 理论上，ButtonClaim 要加 .q(enabled=True) 才能保证不会找到 enabled=False 的按钮
                    # 但是不知道为什么，不加也不会找到禁用的按钮。可能是潜在的 bug
                    if R.Daily.PassRewards.ButtonClaim.try_click():
                        logger.info('Found pass reward to claim.')
                        logger.debug('Clicked pass reward claim.')
                        sleep(1)
                # 确认并等待结束
                for _ in Loop():
                    if R.Common.ButtonIconClose.try_click():
                        logger.debug('Closed popup dialog.')
                        sleep(1)
                        continue
                    if R.Daily.PassRewards.IconTitle.exists():
                        logger.info('Pass reward item claimed.')
                        break
            else:
                break

        sleep(0.5)
        logger.debug('Scrolling pass reward list.')

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
    logger.info('Claiming mission rewards.')

    claim_mission_rewards()
    sleep(1)
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
    mission_reward()
    # claim_mission_rewards()
