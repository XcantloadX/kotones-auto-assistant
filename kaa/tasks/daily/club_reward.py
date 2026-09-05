"""领取社团奖励，并尽可能地给其他人送礼物"""
import logging

from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import at_home, goto_home

from kotonebot import task, sleep, action
from kotonebot.backend.loop import Loop

logger = logging.getLogger(__name__)

@action('进入社团页面')
def goto_club():
    """
    进入社团页面。

    前置条件：位于首页
    结束状态：位于社团页面

    通过工具栏菜单进入社团。若期间出现奖励弹窗，则先关闭。
    """
    logger.info('Entering club UI')
    for _ in Loop(interval=1):
        # 已在社团页面
        if R.Daily.Club.TitleIcon.exists():
            logger.debug('Now at club UI.')
            break
        # 笔记请求结束后的奖励弹窗，直接关闭即可领取
        if R.Common.ButtonClose.try_click():
            logger.debug('Closed reward popup.')
            sleep(0.5)
            continue
        # 打开工具栏菜单
        if R.Common.ButtonToolbarMenu.try_click():
            logger.debug('Clicked toolbar menu.')
            sleep(0.5)
            continue
        # 点击社团图标
        if R.Daily.IconMenuClub.try_click():
            logger.debug('Clicked club icon.')
            sleep(1)

@action('发起笔记请求')
def request_note():
    """
    发起一轮新的笔记请求。

    前置条件：位于社团页面
    结束状态：位于社团页面，且笔记请求已经进行中

    若笔记请求正在进行中（按钮显示「リクエスト中」），则直接跳过。
    否则点击「リクエスト」按钮，在弹出的选择窗口中
    选择配置指定的书籍并确认。
    """
    for _ in Loop(interval=1):
        # 笔记请求已经进行中，无需处理
        if R.Daily.Club.ButtonRequestOngoing.exists():
            logger.info('Note request is ongoing.')
            break
        # 笔记选择窗口：选择配置中指定的书籍并确认
        if R.Common.ButtonConfirm.exists():
            note = conf().tasks.club_reward.selected_note.to_resource()
            if note.try_click():
                logger.debug('Clicked selected note.')
                sleep(1)
                # continue
                if R.Common.ButtonConfirm.try_click():
                    logger.debug('Clicked confirm button.')
                    sleep(0.5)
        # 点击发起请求按钮，打开笔记选择窗口
        if R.Daily.Club.ButtonRequest.try_click():
            logger.debug('Clicked request button.')
            sleep(0.5)
            continue

@action('发送社团礼物')
def send_club_gifts():
    """
    尽可能多地给社团成员送礼物。

    前置条件：位于社团页面
    结束状态：位于社团页面

    逐个切换成员并点击「寄付する」送礼物，至多处理 5 位成员。
    """
    logger.info('Sending gifts')
    hit = 0
    for _ in Loop(interval=1):
        # 关闭送礼后的确认弹窗
        if R.Common.ButtonConfirm.try_click():
            logger.debug('Closed gift confirm popup.')
            sleep(0.5)
            continue
        # 送礼物
        if R.Daily.ButtonClubSendGift.q(enabled=True).try_click():
            logger.debug('Clicked send gift button.')
            sleep(0.5)
            continue
        # 切换到下一位成员
        if R.Daily.ButtonClubSendGiftNext.try_click():
            hit += 1
            logger.debug('Switched to next member.')
            # 默认只处理 5 位成员
            if hit >= 5:
                logger.info('Processed 5 members, stop sending gifts.')
                break
            sleep(0.5)
        # 既没有下一个按钮，当前成员也没有送礼物按钮，说明已经处理完所有成员
        if (
            not R.Daily.ButtonClubSendGift.exists() and
            not R.Daily.ButtonClubSendGiftNext.exists()
        ):
            logger.info('No more members to send gifts to.')
            break

@task('领取社团奖励并送礼物')
def club_reward():
    """
    领取社团奖励，并尽可能地给其他人送礼物
    """

    if not at_home():
        goto_home()

    goto_club()

    # 1. 请求笔记
    if conf().tasks.club_reward.enable_request:
        request_note()

    # 2. 送礼物
    if conf().tasks.club_reward.enable_send:
        send_club_gifts()

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    club_reward()
