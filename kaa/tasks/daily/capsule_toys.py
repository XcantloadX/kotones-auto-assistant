"""扭蛋机，支持任意次数的任意扭蛋类型"""
import logging

from kaa.tasks import R
from kaa.config import conf
from kaa.game_ui.scrollable import Scrollable
from ..actions.scenes import at_home, goto_home
from kotonebot.backend.loop import Loop
from kotonebot import task, device, image, action, sleep
from kotonebot.core import GameObject

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
    sleep(0.5)

    confirm_button = R.Common.ButtonConfirm(enabled=True).find()
    if confirm_button is None:
        # 硬币不足
        logger.info('Not enough coins.')
    else:
        # 硬币足够
        device.click(confirm_button)
        sleep(0.5)
    
    # 等待动画完成
    for _ in Loop():
        if R.Common.ButtonIconClose.try_click():
            pass
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
    # 自动化思路：
    # 进入扭蛋机页面后，可以发现扭蛋机总共有4种类型。
    # 通过硬编码的滑动翻页，把每两种扭蛋分为同一页。
    # 第一页：好友扭蛋+感性扭蛋；
    # 第二页：逻辑扭蛋+非凡扭蛋。
    # 划到某一页之后，识别截图中所有“抽扭蛋”按钮，再按照y轴排序，即可以实现选择扭蛋类型。
    
    # [screenshots/shop/capsule_toys_upper.png]
    # [screenshots/shop/capsule_toys_lower.png]

    if not conf().capsule_toys.enabled:
        logger.info('"Capsule Toys" is disabled.')
        return
    
    if not at_home():
        goto_home()
    
    # 进入扭蛋机页面
    logger.info('Entering Capsule Toys page')
    R.Daily.ButtonShop.wait(timeout=5).click()
    sleep(0.5) # 动画未加载完毕时，提前点击按钮
    R.Daily.ButtonShopCapsuleToys.wait(timeout=5).click()
    # 等待加载
    R.Daily.CapsuleToys.IconTitle.wait()

    # 处理好友扭蛋和感性扭蛋
    buttons = get_capsule_toys_draw_buttons()
    if len(buttons) != 2:
        return

    if conf().capsule_toys.friend_capsule_toys_count > 0:
        draw_capsule_toys(buttons[0], conf().capsule_toys.friend_capsule_toys_count)
    
    if conf().capsule_toys.sense_capsule_toys_count > 0:
        draw_capsule_toys(buttons[1], conf().capsule_toys.sense_capsule_toys_count)
    
    # 划到第二页
    sc = Scrollable()
    sc.next(page=1)

    # 处理逻辑扭蛋扭蛋和非凡扭蛋
    buttons = get_capsule_toys_draw_buttons()
    if len(buttons) != 2:
        return
    
    if conf().capsule_toys.logic_capsule_toys_count > 0:
        draw_capsule_toys(buttons[0], conf().capsule_toys.logic_capsule_toys_count)
    
    if conf().capsule_toys.anomaly_capsule_toys_count > 0:
        draw_capsule_toys(buttons[1], conf().capsule_toys.anomaly_capsule_toys_count)

if __name__ == '__main__':
    capsule_toys()