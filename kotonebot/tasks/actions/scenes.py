import time
from typing import Callable

from .. import R
from kotonebot import device, image, ocr, action, cropper, x, y


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

@action
def at_home() -> bool:
    with device.hook(cropper(y(from_=0.7))):
        return image.find(R.Daily.ButtonHomeCurrent) is not None

@action
def at_shop() -> bool:
    with device.hook(cropper(y(to=0.3))):
        return image.find(R.Daily.IconShopTitle) is not None

@action
def goto_shop():
    """
    从首页进入 ショップ。
    
    前置条件：位于首页 \n
    结束状态：位于商店页面
    """
    device.click(image.expect(R.Daily.ButtonShop))
    until(at_shop, critical=True)


if __name__ == "__main__":
    from kotonebot.backend.context import init_context
    init_context()
    print(at_home())
    print(at_shop())
    goto_shop()
