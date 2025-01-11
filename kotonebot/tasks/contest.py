"""竞赛"""
import logging
from time import sleep
from gettext import gettext as _

from . import R
from .actions.scenes import at_home, goto_home
from .actions.loading import wait_loading_end
from kotonebot import device, image, ocr, action, task, user

logger = logging.getLogger(__name__)

@action
def goto_contest():
    """
    前置条件：位于首页 \n
    结束状态：位于竞赛界面，且已经点击了各种奖励领取提示
    """
    device.click(image.expect(R.Common.ButtonContest))
    device.click(image.expect_wait(R.Daily.TextContest, colored=True, transparent=True, threshold=0.9999))
    sleep(0.5)
    wait_loading_end()
    while not image.find(R.Daily.ButtonContestRanking):
        # [screenshots/contest/acquire1.png]
        # [screenshots/contest/acquire2.png]
        device.click_center()
        sleep(1)
    # [screenshots/contest/main.png]

@action
def pick_and_contest() -> bool:
    """
    选择并挑战

    前置条件：位于竞赛界面 \n
    结束状态：位于竞赛界面

    :return: 如果返回假，说明今天挑战次数已经用完了
    """
    image.expect_wait(R.Daily.ButtonContestRanking)
    sleep(1) # 等待动画
    logger.info('Randomly pick a contestant and start challenge.')
    # 随机选一个对手 [screenshots/contest/main.png]
    logger.debug('Clicking on contestant.')
    contestant = image.wait_for(R.Daily.TextContestOverallStats, timeout=2)
    if contestant is None:
        logger.info('No contestant found. Today\'s challenge points used up.')
        return False
    device.click(contestant)
    # 挑战开始 [screenshots/contest/start1.png]
    logger.debug('Clicking on start button.')
    device.click(image.expect_wait(R.Daily.ButtonContestStart))
    sleep(1)
    # 记忆未编成 [screenshots/contest/no_memo.png]
    if image.find(R.Daily.TextContestNoMemory):
        logger.debug('Memory not set. Using auto-compilation.')
        user.warning(_('记忆未编成。将使用自动编成。'), once=True)
        device.click(image.expect(R.Daily.ButtonContestChallenge))
    # 进入挑战页面 [screenshots/contest/contest1.png]
    # [screenshots/contest/contest2.png]
    image.expect_wait(R.Daily.ButtonContestChallengeStart)
    # 勾选跳过所有
    if image.find(R.Common.CheckboxUnchecked):
        logger.debug('Checking skip all.')
        device.click()
        sleep(0.5)
    # 点击 SKIP
    logger.debug('Clicking on SKIP.')
    device.click(image.expect(R.Daily.ButtonIconSkip, colored=True, transparent=True, threshold=0.999))
    while not image.wait_for(R.Common.ButtonNextNoIcon, timeout=2):
        device.click_center()
        logger.debug('Waiting for the result.')
    # [screenshots/contest/after_contest1.png]
    # 点击 次へ [screenshots/contest/after_contest2.png]
    logger.debug('Challenge finished. Clicking on next.')
    device.click()
    # 点击 終了 [screenshots/contest/after_contest3.png]
    logger.debug('Clicking on end.')
    device.click(image.expect_wait(R.Common.ButtonEnd))
    # 可能出现的奖励弹窗 [screenshots/contest/after_contest4.png]
    sleep(1)
    if image.find(R.Common.ButtonClose):
        logger.debug('Clicking on close.')
        device.click()
    # 等待返回竞赛界面
    wait_loading_end()
    image.expect_wait(R.Daily.ButtonContestRanking)
    logger.info('Challenge finished.')
    return True

@task('竞赛')
def contest():
    """"""
    logger.info('Contest started.')
    if not at_home():
        goto_home()
    goto_contest()
    while pick_and_contest():
        sleep(1.3)
    goto_home()
    logger.info('Contest all finished.')
    

if __name__ == '__main__':
    from kotonebot.backend.context import init_context
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logging.getLogger('kotonebot').setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    init_context()
    
    # if image.find(R.Common.CheckboxUnchecked):
    #     logger.debug('Checking skip all.')
    #     device.click()
    #     sleep(0.5)
    # device.click(image.expect(R.Daily.ButtonIconSkip, colored=True, transparent=True, threshold=0.999))
    contest()