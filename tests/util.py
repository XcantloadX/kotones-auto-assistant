import unittest
from typing import Literal

import cv2
from cv2.typing import MatLike

from kotonebot.client import Device
from kotonebot.client.protocol import Screenshotable, SimpleInputDriver, Touchable


class _MockDeviceAdapter(Screenshotable, Touchable, SimpleInputDriver):
    def __init__(self, device: 'MockDevice'):
        self.device = device

    @property
    def screen_size(self) -> tuple[int, int]:
        image = self.device._load_image()
        return image.shape[1], image.shape[0]

    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None:
        width, height = self.screen_size
        return 'portrait' if height >= width else 'landscape'

    def screenshot(self) -> MatLike:
        return self.device._load_image().copy()

    def click(self, x: int, y: int) -> None:
        self.device.last_click = (x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        self.device.last_swipe = (x1, y1, x2, y2)


class MockDevice(Device):
    def __init__(
        self,
        screenshot_path: str = '',
    ):
        super().__init__()
        self.screenshot_path = screenshot_path
        self.last_click: tuple[int, int] | None = None
        self.last_swipe: tuple[int, int, int, int] | None = None
        self._adapter = _MockDeviceAdapter(self)
        self.setup(screenshot=self._adapter, touch=self._adapter)

    def inject_image(self, path: str):
        self.screenshot_path = path

    def _load_image(self) -> MatLike:
        img = cv2.imread(self.screenshot_path)
        if img is None:
            raise RuntimeError(f'Failed to load screenshot: {self.screenshot_path}')
        return img


class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.device = MockDevice()
        from kotonebot.backend.debug.server import start_server
        from kotonebot.backend.debug import debug
        debug.enabled = True
        # debug.wait_for_message_sent = True
        start_server()
        from kotonebot.backend.context import init_context, inject_context
        init_context(target_device=cls.device, force=True)
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
