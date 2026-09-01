"""扭蛋机，支持任意次数的任意扭蛋类型"""
import logging

from kaa.tasks import R
from kaa.config import conf
from ..actions.scenes import at_home, goto_home

from kotonebot.core import GameObject
from kotonebot.backend.loop import Loop
from kotonebot.primitives import Point, Rect
from kotonebot import task, device, ocr, action, sleep

logger = logging.getLogger(__name__)

@action('抽某种类型的扭蛋times次')
def draw_capsule_toys(button: GameObject, times: int):
    """
    抽某种类型的扭蛋N次

    :param button: 扭蛋按钮
    :param times: 抽取次数
    """
    
    button.click()
    sleep(0.5)

    device.swipe(
        R.Daily.CapsuleToys.SliderStartPoint.x,
        R.Daily.CapsuleToys.SliderStartPoint.y,
        R.Daily.CapsuleToys.SliderEndPoint.x,
        R.Daily.CapsuleToys.SliderEndPoint.y,
        duration=1.0
    )
    sleep(0.5)

    add_button = R.Daily.ButtonShopCountAdd.wait(timeout=5)
    for _ in range(times):
        add_button.click()
        sleep(0.3)
    sleep(0.5)

    confirm_button = R.Common.ButtonConfirm.q(enabled=True).find()
    if confirm_button is None:
        # 硬币不足
        logger.info('Not enough coins.')
    else:
        # 硬币足够
        device.click(confirm_button)
        sleep(1.5)
    
    # 等待动画完成
    for _ in Loop():
        if R.Common.ButtonIconClose.try_click():
            sleep(1)
        elif R.Daily.CapsuleToys.IconTitle.exists():
            break

@action('获取抽扭蛋按钮')
def get_capsule_toys_draw_buttons():
    """
    在扭蛋页面中获取两个抽扭蛋按钮，并按y轴排序
    """
    buttons = R.Daily.ButtonShopCapsuleToysDraw.find_all()
    if len(buttons) != 2:
        logger.error('Failed to find 2 capsule toys buttons.')
        return []
    # 按y轴排序
    buttons.sort(key=lambda x: x.rect.y1)
    return buttons

@task('扭蛋机')
def capsule_toys():
    """
    扭蛋机，支持任意次数的任意扭蛋类型
    """
    if not conf().tasks.capsule_toys.enabled:
        logger.info('"Capsule Toys" is disabled.')
        return
    
    if not at_home():
        goto_home()
    
    # 进入扭蛋机页面
    logger.info('Entering Capsule Toys page')

    for _ in Loop(interval=0.5):
        # 已经位于扭蛋
        if R.Daily.CapsuleToys.IconTitle.exists():
            logger.debug('Now at coin gacha.')
            break
        # 打开商店
        if R.Daily.ButtonShop.try_click():
            logger.debug('Clicked shop button.')
            sleep(0.5)
            continue
        # 进入每日商店
        if R.Daily.ButtonShopCapsuleToys.try_click():
            logger.debug('Clicked daily shop button.')
            sleep(1)

    logger.info('Now at Capsule Toys page.')

    sc = R.Daily.CapsuleToys.Scrollbar.require()

    friend_done = False
    sense_done = False
    logic_done = False
    anomaly_done = False
    for _ in sc(step=0.33):
        buttons = R.Daily.ButtonShopCapsuleToysDraw.find_all()
        # 600 100，往上 160，往左 300
        for button in buttons:
            logger.debug(f'Found capsule toys button at {button.rect}.')
            rect_tl = button.rect.center + Point(-300, -160)
            rect = Rect(x=rect_tl.x, y=rect_tl.y, w=600, h=100)
            # 识别按钮上的文字
            texts = ocr.ocr(rect).squash().text
            if 'フレンド' in texts:
                logger.debug('Found friend capsule toys button.')
                if not friend_done and conf().tasks.capsule_toys.friend_capsule_toys_count > 0:
                    logger.info(f'Drawing friend capsule toys {conf().tasks.capsule_toys.friend_capsule_toys_count} times.')
                    draw_capsule_toys(button, conf().tasks.capsule_toys.friend_capsule_toys_count)
                    friend_done = True
            elif 'センス' in texts:
                logger.debug('Found sense capsule toys button.')
                if not sense_done and conf().tasks.capsule_toys.sense_capsule_toys_count > 0:
                    logger.info(f'Drawing sense capsule toys {conf().tasks.capsule_toys.sense_capsule_toys_count} times.')
                    draw_capsule_toys(button, conf().tasks.capsule_toys.sense_capsule_toys_count)
                    sense_done = True
            elif 'ロジック' in texts:
                logger.debug('Found logic capsule toys button.')
                if not logic_done and conf().tasks.capsule_toys.logic_capsule_toys_count > 0:
                    logger.info(f'Drawing logic capsule toys {conf().tasks.capsule_toys.logic_capsule_toys_count} times.')
                    draw_capsule_toys(button, conf().tasks.capsule_toys.logic_capsule_toys_count)
                    logic_done = True
            elif 'アノマリー' in texts:
                logger.debug('Found anomaly capsule toys button.')
                if not anomaly_done and conf().tasks.capsule_toys.anomaly_capsule_toys_count > 0:
                    logger.info(f'Drawing anomaly capsule toys {conf().tasks.capsule_toys.anomaly_capsule_toys_count} times.')
                    draw_capsule_toys(button, conf().tasks.capsule_toys.anomaly_capsule_toys_count)
                    anomaly_done = True
            else:
                logger.debug(f'Unknown capsule toys button text: {texts}')


if __name__ == '__main__':
    capsule_toys()
    # while True:
    #     print(R.Daily.CapsuleToys.IconTitle.exists())
