import logging
import time
from time import sleep
from typing import Callable

from .. import R
from .loading import loading
from kotonebot import device, image, action, cropped, UnrecoverableError

logger = logging.getLogger(__name__)

def until(
    condition: Callable[[], bool],
    timeout: float=10,
    interval: float=0.5,
    critical: bool=False
) -> bool:
    """
    等待条件成立，如果条件不成立，则返回 False 或抛出异常。

    :param condition: 条件函数。
    :param timeout: 等待时间，单位为秒。
    :param interval: 检查条件的时间间隔，单位为秒。
    :param critical: 如果条件不成立，是否抛出异常。
    """
    start = time.time()
    while not condition():
        if time.time() - start > timeout:
            if critical:
                raise TimeoutError(f"Timeout while waiting for condition {condition.__name__}.")
            return False
        time.sleep(interval)
    return True

@action('检测是否位于首页')
def at_home() -> bool:
    with cropped(device, y1=0.7):
        return image.find(R.Daily.ButtonHomeCurrent) is not None

@action('检测是否位于日常商店页面')
def at_daily_shop() -> bool:
    icon = image.find(R.Daily.IconShopTitle)
    if icon is not None:
        return True
    else:
        # 调整默认购买数量的设置弹窗
        # [screenshots/contest/settings_popup.png]
        if image.find(R.Common.ButtonIconClose):
            device.click()
            sleep(1)
            return at_daily_shop()
        else:
            return False

@action('返回首页')
def goto_home():
    """
    从其他场景返回首页。

    前置条件：无 \n
    结束状态：位于首页
    """
    logger.info("Going home.")
    with cropped(device, y1=0.7):
        if image.find(
            R.Common.ButtonToolbarHome,
            transparent=True,
            threshold=0.9999,
            colored=True
        ):
            device.click()
            while loading():
                sleep(0.5)
        elif image.find(R.Common.ButtonHome):
            device.click()
        else:
            raise UnrecoverableError("Failed to go home.")
    image.expect_wait(R.Daily.ButtonHomeCurrent, timeout=20)

@action('前往商店页面')
def goto_shop():
    """
    从首页进入 ショップ。

    前置条件：无 \n
    结束状态：位于商店页面
    """
    logger.info("Going to shop.")
    if not at_home():
        goto_home()
    device.click(image.expect(R.Daily.ButtonShop))
    until(at_daily_shop, critical=True)


if __name__ == "__main__":
    from kotonebot.backend.context import init_context
    init_context()
    print(at_home())
    print(at_daily_shop())
    goto_shop()
