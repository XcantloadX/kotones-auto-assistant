from time import sleep
from typing import Callable, Protocol, TYPE_CHECKING, overload, runtime_checkable

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
    def __init__(self, device: 'DeviceProtocol', func: Callable[[MatLike], MatLike]):
        self.device = device
        self.func = func
        self.old_func = device.screenshot_hook

    def __enter__(self):
        self.device.screenshot_hook = self.func
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.device.screenshot_hook = self.old_func

class DeviceProtocol(Protocol):
    """
    针对单个设备可执行的操作的协议/接口。
    """

    screenshot_hook: Callable[[MatLike], MatLike] | None

    @staticmethod
    def list_devices() -> list[str]:
        ...
        
    def launch_app(self, package_name: str) -> None:
        """
        根据包名启动 app
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

    def hook(self, func: Callable[[MatLike], MatLike]) -> HookContextManager:
        """
        注册 Hook，在截图前将会调用此函数，对截图进行处理
        """
        return HookContextManager(self, func)

    @property
    def screen_size(self) -> tuple[int, int]:
        """
        屏幕尺寸
        """
        ...

