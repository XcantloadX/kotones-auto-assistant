import unittest
from typing import Sequence, overload
from typing_extensions import override

import cv2
from cv2.typing import MatLike

from kotonebot.client import Device
from kotonebot.client.protocol import ClickableObjectProtocol

class MockDevice(Device):
    def __init__(
        self,
        screenshot_path: str = '',
    ):
        self.screenshot_path = screenshot_path
        self.last_click: tuple[int, int] | None = None
        self.screenshot_hook_after = None
 
    def inject_image(self, path: str):
        self.screenshot_path = path

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
        if len(args) == 0:
            if isinstance(self.last_find, ClickableObjectProtocol):
                self.last_click = self.last_find.rect.center.xy
            elif isinstance(self.last_find, tuple) and len(self.last_find) == 2:
                self.last_click = self.last_find
            else:
                self.last_click = None
        elif len(args) == 2:
            x, y = args
            assert isinstance(x, int) and isinstance(y, int)
            self.last_click = (x, y)
        elif len(args) == 1:
            assert isinstance(args[0], ClickableObjectProtocol)
            self.last_click = args[0].rect.center.xy
        else:
            raise ValueError("Invalid arguments")
            
        return super().click(*args, **kwargs)

    def swipe(self, x1: int, y1: int, x2: int, y2: int) -> None:
        raise NotImplementedError

    @property
    def screen_size(self) -> tuple[int, int]:
        raise NotImplementedError


class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.device = MockDevice()
        from kotonebot.backend.debug.server import start_server
        from kotonebot.backend.debug import debug
        from kaa.common import BaseConfig
        debug.enabled = True
        # debug.wait_for_message_sent = True
        start_server()
        from kotonebot.backend.context import init_context, inject_context
        init_context(config_type=BaseConfig)
        inject_context(device=cls.device)

    def assertPointInRect(
            self,
            point: tuple[int, int] | None,
            topleft: tuple[int, int],
            bottomright: tuple[int, int],
            msg: str | None = None
        ) -> None:
        self.assertIsNotNone(point, msg)
        assert point is not None
        x, y = point
        x1, y1 = topleft
        x2, y2 = bottomright
        self.assertGreaterEqual(x, x1)
        self.assertLessEqual(x, x2)
        self.assertGreaterEqual(y, y1)
        self.assertLessEqual(y, y2)
