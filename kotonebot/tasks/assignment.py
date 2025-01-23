"""工作。お仕事"""
import logging
from typing import Literal

from . import R
from .common import conf
from .actions.loading import wait_loading_end
from .actions.scenes import at_home, goto_home
from kotonebot import task, device, image, action, ocr, contains, cropped, rect_expand, color, sleep

logger = logging.getLogger(__name__)

@action('领取工作奖励')
def acquire_assignment():
    """
    领取工作奖励

    前置条件：点击了工作按钮，已进入领取页面 \n
    结束状态：分配工作页面
    """
    # 领取奖励 [screenshots/assignment/acquire.png]
    while image.wait_for(R.Common.ButtonCompletion, timeout=5):
        device.click()
        sleep(5)

@action('重新分配工作')
def assign(type: Literal['mini', 'online']) -> bool:
    """
    分配工作

    前置条件：分配工作页面 \n
    结束状态：工作开始动画

    :param type: 工作类型。mini=ミニライブ 或 online=ライブ配信。
    """
    # [kotonebot/tasks/assignment.py]
    target_duration = 12
    image.expect_wait(R.Daily.IconTitleAssign, timeout=10)
    if type == 'mini':
        target_duration = conf().assignment.mini_live_duration
        if image.find(R.Daily.IconAssignMiniLive):
            device.click()
        else:
            logger.warning('MiniLive already assigned. Skipping...')
            return False
    elif type == 'online':
        target_duration = conf().assignment.online_live_duration
        if image.find(R.Daily.IconAssignOnlineLive):
            device.click()
        else:
            logger.warning('OnlineLive already assigned. Skipping...')
            return False
    else:
        raise ValueError(f'Invalid type: {type}')
    # MiniLive/OnlineLive 页面 [screenshots/assignment/assign_mini_live.png]
    image.expect_wait(R.Common.ButtonSelect, timeout=5)
    # 选择好调偶像
    selected = False
    max_attempts = 4
    attempts = 0
    while not selected:
        # 寻找所有好调图标
        results = image.find_all(R.Daily.IconAssignKouchou, threshold=0.8)
        results.sort(key=lambda r: tuple(r.position))
        results.pop(0) # 第一个是说明文字里的图标
        # 尝试点击所有目标
        for target in results:
            with cropped(device, y2=0.3):
                img1 = device.screenshot()
                # 选择偶像并判断是否选择成功
                device.click(target)
                sleep(1)
                img2 = device.screenshot()
                if image.raw().similar(img1, img2, 0.97):
                    logger.info(f'Idol #{target} already assigned. Trying next.')
                    continue
                selected = True
                break
        if not selected:
            attempts += 1
            if attempts >= max_attempts:
                logger.warning('Failed to select kouchou idol. Keep using the default idol.')
                break
            # 说明可能在第二页
            device.swipe_scaled(0.6, 0.7, 0.2, 0.7)
            sleep(0.5)
        else:
            break
    # 点击选择
    sleep(0.5)
    device.click(image.expect(R.Common.ButtonSelect))
    # 等待页面加载
    confirm = image.expect_wait(R.Common.ButtonConfirmNoIcon)
    # 选择时间 [screenshots/assignment/assign_mini_live2.png]
    if ocr.find(contains(f'{target_duration}時間')):
        logger.info(f'{target_duration}時間 selected.')
        device.click()
    else:
        logger.warning(f'{target_duration}時間 not found. Using default duration.')
    sleep(0.5)
    # 点击 决定する
    device.click(confirm)
    # 点击 開始する [screenshots/assignment/assign_mini_live3.png]
    device.click(image.expect_wait(R.Common.ButtonStart, timeout=5))
    return True

@task('工作')
def assignment():
    """领取工作奖励并重新分配工作"""
    if not conf().assignment.enabled:
        logger.info('Assignment is disabled.')
        return
    if not at_home():
        goto_home()
    btn_assignment = image.expect_wait(R.Daily.ButtonAssignmentPartial)
    notification_rect = rect_expand(btn_assignment.rect, top=40, right=40)
    complete_rect = rect_expand(btn_assignment.rect, right=40, bottom=60)
    with device.pinned():
        completed = color.find_rgb('#ff6085', rect=complete_rect)
        if completed:
            logger.info('Assignment completed. Acquiring...')
        notification_dot = color.find_rgb('#ff134a', rect=notification_rect)
        if not notification_dot and not completed:
            logger.info('No action needed.')
            return

    # 点击工作按钮
    logger.debug('Clicking assignment icon.')
    device.click(btn_assignment)
    # 加载页面等待
    wait_loading_end()
    if completed:
        acquire_assignment()
        logger.info('Assignment acquired.')
    # 领取完后会自动进入分配页面
    image.expect_wait(R.Daily.IconTitleAssign)
    if conf().assignment.mini_live_reassign_enabled:
        if image.find(R.Daily.IconAssignMiniLive):
            assign('mini')
            sleep(6) # 等待动画结束
            # TODO: 更好的方法来等待动画结束。
    else:
        logger.info('MiniLive reassign is disabled.')
    if conf().assignment.online_live_reassign_enabled:
        if image.find(R.Daily.IconAssignOnlineLive):
            assign('online')
            sleep(6) # 等待动画结束
    else:
        logger.info('OnlineLive reassign is disabled.')

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    assignment()
