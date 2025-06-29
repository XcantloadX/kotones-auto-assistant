import time
from typing import Literal

import numpy as np
import uiautomator2 as u2
from cv2.typing import MatLike

from kotonebot import logging
from ..device import Device
from ..protocol import Screenshotable, Commandable, Touchable
from ..registration import register_impl
from .adb import AdbImplConfig, _create_adb_device_base

logger = logging.getLogger(__name__)

SCREENSHOT_INTERVAL = 0.2

class UiAutomator2Impl(Screenshotable, Commandable, Touchable):
    def __init__(self, device: Device):
        self.device = device
        self.u2_client = u2.Device(device.adb.serial)
        self.__last_screenshot_time = 0
        
    def screenshot(self) -> MatLike:
        """
        截图
        """
        from kotonebot import sleep
        delta = time.time() - self.__last_screenshot_time
        if delta < SCREENSHOT_INTERVAL:
            time.sleep(SCREENSHOT_INTERVAL - delta)
        start_time = time.time()
        image = self.u2_client.screenshot(format='opencv')
        logger.verbose(f'uiautomator2 screenshot: {time.time() - start_time}s')
        self.__last_screenshot_time = time.time()
        assert isinstance(image, np.ndarray)
        return image
    
    @property
    def screen_size(self) -> tuple[int, int]:
        info = self.u2_client.info
        sizes = info['displayWidth'], info['displayHeight']
        if self.device.orientation == 'landscape':
            return (max(sizes), min(sizes))
        else:
            return (min(sizes), max(sizes))
    
    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None:
        """
        检测设备方向
        """
        orientation = self.u2_client.info['displayRotation']
        if orientation == 1:
            return 'portrait'
        elif orientation == 0:
            return 'landscape'
        else:
            return None
    
    def launch_app(self, package_name: str) -> None:
        """
        启动应用
        """
        self.u2_client.app_start(package_name)
        
    def current_package(self) -> str | None:
        """
        获取当前应用包名
        """
        try:
            result = self.u2_client.app_current()
            logger.verbose(f'uiautomator2 current_package: {result}')
            return result['package']
        except:
            return None
        
    def click(self, x: int, y: int) -> None:
        """
        点击屏幕
        """
        self.u2_client.click(x, y)
        
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float|None = None) -> None:
        """
        滑动屏幕
        """
        self.u2_client.swipe(x1, y1, x2, y2, duration=duration or 0.1)


@register_impl('uiautomator2', config_model=AdbImplConfig)
def create_uiautomator2_device(config: AdbImplConfig) -> Device:
    """UiAutomator2Impl 工厂函数"""
    return _create_adb_device_base(config, UiAutomator2Impl)
