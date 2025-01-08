from time import sleep
from typing import Callable, Protocol, TYPE_CHECKING, overload, runtime_checkable
from abc import ABC

from cv2.typing import MatLike

from kotonebot.backend.util import Rect, is_rect

@runtime_checkable
class ClickableObjectProtocol(Protocol):
    """
    可点击对象的协议
    """
    @property
    def rect(self) -> Rect:
        ...

class DeviceScreenshotProtocol(Protocol):
    def screenshot(self) -> MatLike:
        """
        截图
        """
        ...

class HookContextManager:
    def __init__(self, device: 'DeviceABC', func: Callable[[MatLike], MatLike]):
        self.device = device
        self.func = func
        self.old_func = device.screenshot_hook_after

    def __enter__(self):
        self.device.screenshot_hook_after = self.func
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.device.screenshot_hook_after = self.old_func


class PinContextManager:
    def __init__(self, device: 'DeviceABC'):
        self.device = device
        self.old_hook = device.screenshot_hook_before
        self.memo = None

    def __hook(self) -> MatLike:
        if self.memo is None:
            self.memo = self.device.screenshot_raw()
        return self.memo

    def __enter__(self):
        self.device.screenshot_hook_before = self.__hook
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.device.screenshot_hook_before = self.old_hook

    def update(self) -> None:
        """
        更新记住的截图
        """
        self.memo = self.device.screenshot_raw()


class DeviceABC(ABC):
    """
    针对单个设备可执行的操作的抽象基类。
    """
    def __init__(self) -> None:
        self.screenshot_hook_after: Callable[[MatLike], MatLike] | None = None
        """截图后调用的函数"""
        self.screenshot_hook_before: Callable[[], MatLike | None] | None = None
        """截图前调用的函数"""
        self.last_find: Rect | ClickableObjectProtocol | None = None
        """上次 image 对象或 ocr 对象的寻找结果"""

    @staticmethod
    def list_devices() -> list[str]:
        ...
        
    def launch_app(self, package_name: str) -> None:
        """
        根据包名启动 app
        """
        ...
    
    @overload
    def click(self) -> None:
        """
        点击上次 `image` 对象或 `ocr` 对象的寻找结果（仅包括返回单个结果的函数）。
        （不包括 `image.raw()` 和 `ocr.raw()` 的结果。）

        如果没有上次寻找结果或上次寻找结果为空，会抛出异常 ValueError。
        """
        ...

    @overload
    def click(self, x: int, y: int) -> None:
        """
        点击屏幕上的某个点
        """
        ...

    @overload
    def click(self, rect: Rect) -> None:
        """
        从屏幕上的某个矩形区域随机选择一个点并点击
        """
        ...

    @overload
    def click(self, clickable: ClickableObjectProtocol) -> None:
        """
        点击屏幕上的某个可点击对象
        """
        ...

    def click(self, *args, **kwargs) -> None:
        ...

    def click_center(self) -> None:
        """
        点击屏幕中心
        """
        x, y = self.screen_size[0] // 2, self.screen_size[1] // 2
        self.click(x, y)
    
    @overload
    def double_click(self, x: int, y: int, interval: float = 0.5) -> None:
        """
        双击屏幕上的某个点
        """
        ...

    @overload
    def double_click(self, rect: Rect, interval: float = 0.5) -> None:
        """
        双击屏幕上的某个矩形区域
        """
        ...
    
    @overload
    def double_click(self, clickable: ClickableObjectProtocol, interval: float = 0.5) -> None:
        """
        双击屏幕上的某个可点击对象
        """
        ...
    
    def double_click(self, *args, **kwargs) -> None:
        arg0 = args[0]
        if is_rect(arg0) or isinstance(arg0, ClickableObjectProtocol):
            rect = arg0
            interval = kwargs.get('interval', 0.5)
            self.click(rect)
            sleep(interval)
            self.click(rect)
        else:
            x = args[0]
            y = args[1]
            interval = kwargs.get('interval', 0.5)
            self.click(x, y)
            sleep(interval)
            self.click(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """
        滑动屏幕
        """
        ...
    
    def screenshot(self) -> MatLike:
        """
        截图
        """
        ...

    def screenshot_raw(self) -> MatLike:
        """
        截图，不调用任何 Hook。
        """
        ...

    def hook(self, func: Callable[[MatLike], MatLike]) -> HookContextManager:
        """
        注册 Hook，在截图前将会调用此函数，对截图进行处理
        """
        return HookContextManager(self, func)

    def pinned(self) -> PinContextManager:
        """
        记住下次截图结果，并将截图调整为手动挡。
        之后截图都会返回记住的数据，节省重复截图时间。

        调用返回对象中的 PinContextManager.update() 可以立刻更新记住的截图。
        """
        return PinContextManager(self)

    @property
    def screen_size(self) -> tuple[int, int]:
        """
        屏幕尺寸
        """
        ...

