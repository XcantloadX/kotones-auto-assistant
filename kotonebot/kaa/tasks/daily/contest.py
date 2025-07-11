"""竞赛"""
import logging
from gettext import gettext as _

from kotonebot.kaa.tasks import R
from kotonebot.kaa.config import conf
from kotonebot.kaa.game_ui import WhiteFilter
from ..actions.scenes import at_home, goto_home
from ..actions.loading import wait_loading_end
from kotonebot import device, image, ocr, color, action, task, user, rect_expand, sleep, contains, Interval

logger = logging.getLogger(__name__)

@action('前往竞赛页面', screenshot_mode='manual-inherit')
def goto_contest() -> bool:
    """
    前置条件：位于首页 \n
    结束状态：位于竞赛界面，且已经点击了各种奖励领取提示

    :return: 是否存在未完成的挑战
    """
    it = Interval()
    has_ongoing_contest = None
    while True:
        device.screenshot()
        it.wait()
        
        if image.find(R.Common.ButtonContest):
            device.click()
        elif image.find(R.Daily.TextRoadToIdol):
            # 已进入竞赛 Tab
            if image.find(R.Daily.TextContestLastOngoing):
                logger.info('Ongoing contest found.')
                has_ongoing_contest = True
            else:
                has_ongoing_contest = False
            # 点击进入竞赛页面
            logger.debug('Clicked on Contest.')
            device.click(R.Daily.PointContest)
            continue

        # 有未完成的挑战
        if has_ongoing_contest is True:
            if image.find(R.Daily.ButtonContestChallengeStart):
                logger.info('Challenging.')
                break
        # 新开挑战
        elif has_ongoing_contest is False:
            if image.find(R.Daily.ButtonContestRanking):
                logger.info('Now at pick contestant screen.')
                break
            # 跳过奖励领取
            # [kotonebot-resource\sprites\jp\daily\screenshot_contest_season_reward.png]
            # [screenshots/contest/acquire2.png]
            device.click(R.Daily.PointDissmissContestReward)
    return has_ongoing_contest

@action('处理竞赛挑战', screenshot_mode='manual-inherit')
def handle_challenge() -> bool:
    """

    前置条件：- \n
    结束状态：位于竞赛选择对手界面
    :return: 是否命中任何处理
    """
    # 挑战开始 [screenshots/contest/start1.png]
    if image.find(R.Daily.ButtonContestStart, threshold=0.75): # TODO: 为什么默认阈值找不到？
        logger.debug('Clicking on start button.')
        device.click()

    # 记忆未编成 [screenshots/contest/no_memo.png]
    if image.find(R.Daily.TextContestNoMemory):
        logger.debug('Memory not set. Using auto-compilation.')
        user.warning('竞赛未编成', _('记忆未编成。将使用自动编成。'), once=True)
        if image.find(R.Daily.ButtonContestChallenge):
            device.click()
            return True

    # 勾选跳过所有
    # [screenshots/contest/contest2.png]
    if image.find(R.Common.CheckboxUnchecked, colored=True):
        logger.debug('Checking skip all.')
        device.click()
        return True

    # 跳过所有
    # [screenshots/contest/contest1.png]
    if image.find(R.Daily.ButtonIconSkip, preprocessors=[WhiteFilter()]):
        logger.debug('Skipping all.')
        device.click()
        return True

    if image.find(R.Common.ButtonNextNoIcon):
        logger.debug('Clicking on next.')
        device.click()

    # 終了 [screenshots/contest/after_contest3.png]
    if image.find(R.Common.ButtonEnd):
        logger.debug('Clicking on end.')
        device.click()
        return True

    # 可能出现的奖励弹窗 [screenshots/contest/after_contest4.png]
    if image.find(R.Common.ButtonClose):
        logger.debug('Clicking on close.')
        device.click()

    return False

@action('选择对手')
def handle_pick_contestant(has_ongoing_contest: bool = False) -> tuple[bool, bool]:
    """
    选择并挑战

    前置条件：位于竞赛界面 \n
    结束状态：位于竞赛界面

    :param has_ongoing_contest: 是否有中断未完成的挑战
    :return: 二元组。第一个值表示是否命中任何处理。
        第二个值表示是否应该继续挑战，为 False 表示今天挑战次数已经用完了。
    """
    if image.find(R.Daily.ButtonContestRanking):
        # 无进行中挑战，说明要选择对手
        if not has_ongoing_contest:
            # 随机选一个对手 [screenshots/contest/main.png]
            logger.debug('Clicking on contestant.')
            contestant_list = image.find_all(R.Daily.TextContestOverallStats)
            if contestant_list is None or len(contestant_list) == 0:
                logger.info('No contestant found. Today\'s challenge points used up.')
                return True, False
            # 按照y坐标从上到下排序对手列表
            contestant_list.sort(key=lambda x: x.position[1])
            if len(contestant_list) != 3:
                logger.warning('Cannot find all 3 contestants.')
            # 选择配置文件中对应的对手顺序（1最强，3最弱）
            target = conf().contest.select_which_contestant
            if target >= 1 and target <= 3 and target <= len(contestant_list):
                target -= 1  # [1, 3]映射至[0, 2]
            else:
                target = 0  # 出错则默认选择第一个
            contestant = contestant_list[target]
            logger.info('Picking up contestant #%d.', target + 1)
            device.click(contestant)
            sleep(2)
            return True, True
    return False, True

@task('竞赛')
def contest():
    if not conf().contest.enabled:
        logger.info('Contest is disabled.')
        return
    logger.info('Contest started.')
    if not at_home():
        goto_home()
    sleep(0.3)
    btn_contest = image.expect(R.Common.ButtonContest)
    notification_dot = rect_expand(btn_contest.rect, top=35, right=35)
    if not color.find('#ff104a', rect=notification_dot):
        logger.info('No action needed.')
        return
    has_ongoing_contest = goto_contest()
    while True:
        device.screenshot()
        handled, should_continue = handle_pick_contestant(has_ongoing_contest)
        if not should_continue:
            break
        if not handled: 
            handled = handle_challenge()
        if not handled:
            device.click(10, 10)
        has_ongoing_contest = False
    goto_home()
    logger.info('Contest all finished.')

if __name__ == '__main__':
    from kotonebot.kaa.main import Kaa
    from kotonebot.backend.context import tasks_from_id
    Kaa('config.json').run(tasks_from_id(['contest']))