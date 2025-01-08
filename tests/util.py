from typing import Sequence, overload
from typing_extensions import override

import cv2
from cv2.typing import MatLike

from kotonebot.backend.util import Rect
from kotonebot.client.protocol import DeviceABC

class MockDevice(DeviceABC):
    def __init__(
        self,
        screenshot_path: str = '',
    ):
        self.screenshot_path = screenshot_path
        self.screenshot_hook_after = None
 
    @override
    def screenshot(self) -> MatLike:
        img = cv2.imread(self.screenshot_path)
        if self.screenshot_hook_after is not None:
            img = self.screenshot_hook_after(img)
        return img

    @staticmethod
    def list_devices() -> list[str]:
        raise NotImplementedError

    def launch_app(self, package_name: str) -> None:
        raise NotImplementedError

    @overload
    def click(self, x: int, y: int) -> None:
        ...

    @overload
    def click(self, rect: Sequence[int]) -> None:
        ...

    def click(self, *args, **kwargs):
        raise NotImplementedError

    def swipe(self, x1: int, y1: int, x2: int, y2: int) -> None:
        raise NotImplementedError

    @property
    def screen_size(self) -> tuple[int, int]:
        raise NotImplementedError


