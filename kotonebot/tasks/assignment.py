"""工作。お仕事"""
import logging
from time import sleep
from typing import Literal
from kotonebot import task, device, image, action, ocr, contains, cropped
from .actions.scenes import at_home, goto_home
from . import R

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
def assign(type: Literal['mini', 'online']):
    """
    分配工作

    前置条件：分配工作页面 \n
    结束状态：工作开始动画

    :param type: 工作类型。mini=ミニライブ 或 online=ライブ配信。
    """
    # [kotonebot/tasks/assignment.py]
    if type == 'mini':
        device.click(image.expect(R.Daily.IconAssignMiniLive))
    elif type == 'online':
        device.click(image.expect(R.Daily.IconAssignOnlineLive))
    else:
        raise ValueError(f'Invalid type: {type}')
    # MiniLive/OnlineLive 页面 [screenshots/assignment/assign_mini_live.png]
    image.expect_wait(R.Common.ButtonSelect, timeout=5)
    results = image.find_many(R.Daily.IconAssignKouchou, threshold=0.8)
    results.sort(key=lambda r: tuple(r.position))
    results.pop(0) # 第一个是说明文字里的图标
    # 选择好调偶像
    for target in results:
        with cropped(device, y2=0.4):
            img1 = device.screenshot()
            target = results.pop()
            device.click(target)
            sleep(1)
            img2 = device.screenshot()
            if image.raw().similar(img1, img2):
                logger.info(f'Idol #{target} already assigned. Trying next.')
                continue
    # 点击选择
    sleep(0.5)
    device.click(image.expect(R.Common.ButtonSelect))
    # 等待页面加载
    confirm = image.expect_wait(R.Common.ButtonConfirmNoIcon)
    # 选择时间 [screenshots/assignment/assign_mini_live2.png]
    # CONFIG: 工作时长
    if ocr.find(contains('12時間')):
        logger.info('12時間 selected.')
        device.click()
    else:
        logger.warning('12時間 not found. Using default duration.')
    sleep(0.5)
    # 点击 决定する
    device.click(confirm)
    # 点击 開始する [screenshots/assignment/assign_mini_live3.png]
    device.click(image.expect_wait(R.Common.ButtonStart, timeout=5))


@task('工作')
def assignment():
    if not at_home():
        goto_home()
    # 由于“完了”标签会有高光特效，所以要多试几次
    if image.wait_for(R.Daily.TextAssignmentCompleted, timeout=6, interval=0):
        logger.info('Assignment completed. Acquiring...')
        device.click()
        # 加载页面等待
        sleep(4)
        acquire_assignment()
        logger.info('Assignment acquired.')
        # 领取完后会自动进入分配页面
        image.expect_wait(R.Daily.IconAssignMiniLive, timeout=7)
        assign('mini')
        image.expect_wait(R.Daily.IconAssignOnlineLive, timeout=7)
        assign('online')
    else:
        logger.info('Assignment not completed yet. Skipped.')

if __name__ == '__main__':
    from kotonebot.backend.context import init_context
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    init_context()
    # assignment()
    # acquire_assignment()
    # logger.info('Assignment acquired.')
    # # 领取完后会自动进入分配页面
    # image.expect_wait(R.Daily.IconAssignMiniLive, timeout=7)
    # assign_mini_live()
    assign('online')

