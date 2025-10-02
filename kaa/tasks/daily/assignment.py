"""工作。お仕事"""
import logging
from typing import Literal
from datetime import timedelta

from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import at_home, goto_home
from kotonebot import task, device, image, action, ocr, contains, cropped, rect_expand, color, sleep, regex

logger = logging.getLogger(__name__)

@action('领取工作奖励')
def handle_claim_assignment():
    """
    领取工作奖励

    前置条件：点击了工作按钮，已进入领取页面 \n
    结束状态：分配工作页面
    """
    # 领取奖励 [screenshots/assignment/acquire.png]
    if image.find(R.Common.ButtonCompletion):
        device.click()
        return True
    return False

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
    logger.info('Now at assignment idol selection scene.')
    # 选择好调偶像
    selected = False
    max_attempts = 4
    attempts = 0
    while not selected:
        # 寻找所有好调图标
        results = image.find_all(R.Daily.IconAssignKouchou, threshold=0.8)
        logger.debug(f'Found {len(results)} kouchou icons.')
        if not results:
            logger.warning('No kouchou icons found. Trying again...')
            continue
        results.sort(key=lambda r: r.position[1])
        results.pop(0) # 第一个是说明文字里的图标
        # 尝试点击所有目标
        for target in results:
            logger.debug(f'Clicking idol #{target}...')
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
    while not at_assignment():
        # 点击 决定する
        if image.find(R.Common.ButtonConfirmNoIcon):
            device.click()
        elif image.find(R.Common.ButtonStart):
            # 点击 開始する [screenshots/assignment/assign_mini_live3.png]
            device.click()
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
    return image.find_multi([
        R.Daily.ButtonAssignmentShortenTime,
        R.Daily.IconAssignMiniLive,
        R.Daily.IconAssignOnlineLive,
    ]) is not None

@task('工作')
def assignment():
    """领取工作奖励并重新分配工作"""
    if not conf().assignment.enabled:
        logger.info('Assignment is disabled.')
        return
    if not at_home():
        goto_home()
    btn_assignment = image.expect_wait(R.Daily.ButtonAssignmentPartial)

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
    device.click(btn_assignment)
    # 等待加载、领取奖励
    while not at_assignment():
        if completed and handle_claim_assignment():
            logger.info('Assignment acquired.')
    # 重新分配
    if conf().assignment.mini_live_reassign_enabled:
        if image.find(R.Daily.IconAssignMiniLive):
            assign('mini')
    else:
        logger.info('MiniLive reassign is disabled.')
    while not at_assignment():
        pass
    if conf().assignment.online_live_reassign_enabled:
        if image.find(R.Daily.IconAssignOnlineLive):
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
