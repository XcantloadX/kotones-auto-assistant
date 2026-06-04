"""工作。お仕事"""
import logging
from typing import Literal
from datetime import timedelta

import cv2
from cv2.typing import MatLike
from kotonebot.core import AnyOf
from kotonebot.backend import image as raw_image
from kotonebot import task, device, action, ocr, contains, color, sleep, regex

from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import at_home, goto_home

logger = logging.getLogger(__name__)

def similar(
    image1: MatLike,
    image2: MatLike,
    threshold: float = 0.9
) -> bool:
    """
    判断两张图像是否相似（灰度）。输入的两张图片必须为相同尺寸。
    """
    from skimage.metrics import structural_similarity
    if image1.shape != image2.shape:
        raise ValueError('Expected two images with the same size.')
    image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
    result = structural_similarity(image1, image2, multichannel=True)
    return result >= threshold

@action('重新分配工作')
def assign(type: Literal['mini', 'online']) -> bool:
    """
    分配工作

    前置条件：分配工作页面 \n
    结束状态：分配工作页面

    :param type: 工作类型。mini=ミニライブ 或 online=ライブ配信。
    """
    # [kotonebot/tasks/assignment.py]
    target_duration = 12
    R.Daily.IconTitleAssign.wait(timeout=10)
    if type == 'mini':
        target_duration = conf().assignment.mini_live_duration
        if R.Daily.IconAssignMiniLive.try_click():
            pass
        else:
            logger.warning('MiniLive already assigned. Skipping...')
            return False
    elif type == 'online':
        target_duration = conf().assignment.online_live_duration
        if R.Daily.IconAssignOnlineLive.try_click():
            pass
        else:
            logger.warning('OnlineLive already assigned. Skipping...')
            return False
    else:
        raise ValueError(f'Invalid type: {type}')
    # MiniLive/OnlineLive 页面 [screenshots/assignment/assign_mini_live.png]
    R.Common.ButtonSelect.wait(timeout=5)
    logger.info('Now at assignment idol selection scene.')
    # 选择好调偶像
    selected = False
    max_attempts = 4
    attempts = 0
    while not selected:
        # 寻找所有好调图标
        results = R.Daily.IconAssignKouchou.find_all()
        logger.debug(f'Found {len(results)} kouchou icons.')
        if not results:
            logger.warning('No kouchou icons found. Trying again...')
            continue
        results.sort(key=lambda r: r.rect.x1)

        # 尝试点击所有目标
        for target in results:
            logger.debug(f'Clicking idol #{target}...')
            img1 = device.screenshot()
            x, y, w, h = R.Daily.Assignment.BoxCharName.rect
            img1 = img1[y:y+h, x:x+w]
            # 选择偶像并判断是否选择成功
            device.click(target)
            sleep(1)
            img2 = device.screenshot()
            img2 = img2[y:y+h, x:x+w]
            if raw_image.find(img1, img2, threshold=0.95):
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
    R.Common.ButtonSelect.click()
    # 等待页面加载
    R.Common.ButtonConfirmNoIcon.wait()
    # 选择时间 [screenshots/assignment/assign_mini_live2.png]
    if target_duration == 4:
        R.Daily.Assignment.Button4Hours.wait().click()
    elif target_duration == 8:
        R.Daily.Assignment.Button8Hours.wait().click()
    elif target_duration == 12:
        R.Daily.Assignment.Button12Hours.wait().click()
    else:
        raise ValueError(f'Invalid target_duration: {target_duration}')
    sleep(0.5)
    while not at_assignment():
        # 点击 决定する
        if R.Common.ButtonConfirmNoIcon.try_click():
            pass
        elif R.Common.ButtonStart.try_click():
            # 点击 開始する [screenshots/assignment/assign_mini_live3.png]
            pass
    return True

@action('获取剩余时间')
def get_remaining_time() -> timedelta | None:
    """
    获取剩余时间

    前置条件：首页 \n
    结束状态：-
    """
    texts = ocr.ocr(rect=R.Daily.BoxHomeAssignment)
    if not texts.where(contains('お仕事')):
        logger.warning('お仕事 area not found.')
        return None
    time = texts.where(regex(r'\d+:\d+:\d+')).first()
    if not time:
        logger.warning('お仕事 remaining time not found.')
        return None
    logger.info(f'お仕事 remaining time: {time}')
    return timedelta(hours=time.numbers()[0], minutes=time.numbers()[1], seconds=time.numbers()[2])

@action('检测工作页面')
def at_assignment():
    """
    判断是否在工作页面
    """
    # 不能以 R.Daily.IconTitleAssign 作为判断依据，
    # 因为标题出现后还有一段动画
    return AnyOf[
        R.Daily.ButtonAssignmentShortenTime,
        R.Daily.IconAssignMiniLive,
        R.Daily.IconAssignOnlineLive,
    ].exists()

@task('工作')
def assignment():
    """领取工作奖励并重新分配工作"""
    if not conf().assignment.enabled:
        logger.info('Assignment is disabled.')
        return
    if not at_home():
        goto_home()
    btn_assignment = R.Daily.ButtonAssignmentPartial.wait()

    completed = color.find('#ff6085', rect=R.Daily.BoxHomeAssignment)
    if completed:
        logger.info('Assignment completed. Acquiring...')
    notification_dot = color.find('#ff134a', rect=R.Daily.BoxHomeAssignment)
    if not notification_dot and not completed:
        logger.info('No action needed.')
        # TODO: 获取剩余时间，并根据时间更新调度
        return

    # 点击工作按钮
    logger.debug('Clicking assignment icon.')
    btn_assignment.click()
    # 等待加载、领取奖励
    while not at_assignment():
        if completed:
            # 领取奖励 [screenshots/assignment/acquire.png]
            if R.Common.ButtonCompletion.try_click():
                logger.info('Assignment acquired.')
    # 重新分配
    if conf().assignment.mini_live_reassign_enabled:
        if R.Daily.IconAssignMiniLive.exists():
            assign('mini')
    else:
        logger.info('MiniLive reassign is disabled.')
    while not at_assignment():
        pass
    if conf().assignment.online_live_reassign_enabled:
        if R.Daily.IconAssignOnlineLive.exists():
            assign('online')
    else:
        logger.info('OnlineLive reassign is disabled.')
    # 等待动画结束
    while not at_assignment():
        pass

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    # assignment()
    # print(get_remaining_time())
    assign('online')
