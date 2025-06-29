"""
Remote Windows implementation using XML-RPC.

This module provides:
1. RemoteWindowsImpl - Client implementation that connects to a remote Windows machine
2. RemoteWindowsServer - Server implementation that exposes a WindowsImpl instance via XML-RPC
"""

import io
import base64
import logging
import xmlrpc.client
import xmlrpc.server
from typing import Literal, cast, Any, Tuple
from functools import cached_property
from threading import Thread
from dataclasses import dataclass

import cv2
import numpy as np
from cv2.typing import MatLike

from kotonebot import logging
from ..device import Device, WindowsDevice
from ..protocol import Touchable, Screenshotable
from ..registration import register_impl, ImplConfig
from .windows import WindowsImpl, WindowsImplConfig, create_windows_device

logger = logging.getLogger(__name__)

# 定义配置模型
@dataclass
class RemoteWindowsImplConfig(ImplConfig):
    windows_impl_config: WindowsImplConfig
    host: str = "localhost"
    port: int = 8000

def _encode_image(image: MatLike) -> str:
    """Encode an image as a base64 string."""
    success, buffer = cv2.imencode('.png', image)
    if not success:
        raise RuntimeError("Failed to encode image")
    return base64.b64encode(buffer.tobytes()).decode('ascii')

def _decode_image(encoded_image: str) -> MatLike:
    """Decode a base64 string to an image."""
    buffer = base64.b64decode(encoded_image)
    image = cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("Failed to decode image")
    return image

class RemoteWindowsServer:
    """
    XML-RPC server that exposes a WindowsImpl instance.

    This class wraps a WindowsImpl instance and exposes its methods via XML-RPC.
    """

    def __init__(self, windows_impl_config: WindowsImplConfig, host="localhost", port=8000):
        """Initialize the server with the given host and port."""
        self.host = host
        self.port = port
        self.server = None
        self.device = WindowsDevice()
        self.impl = create_windows_device(windows_impl_config)
        self.device._screenshot = self.impl
        self.device._touch = self.impl

    def start(self):
        """Start the XML-RPC server."""
        self.server = xmlrpc.server.SimpleXMLRPCServer(
            (self.host, self.port),
            logRequests=True,
            allow_none=True
        )
        self.server.register_instance(self)
        logger.info(f"Starting RemoteWindowsServer on {self.host}:{self.port}")
        self.server.serve_forever()

    def start_in_thread(self):
        """Start the XML-RPC server in a separate thread."""
        thread = Thread(target=self.start, daemon=True)
        thread.start()
        return thread

    # Screenshotable methods

    def screenshot(self) -> str:
        """Take a screenshot and return it as a base64-encoded string."""
        try:
            image = self.impl.screenshot()
            return _encode_image(image)
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            raise

    def get_screen_size(self) -> tuple[int, int]:
        """Get the screen size."""
        return self.impl.screen_size

    def detect_orientation(self) -> str | None:
        """Detect the screen orientation."""
        return self.impl.detect_orientation()

    # Touchable methods

    def click(self, x: int, y: int) -> bool:
        """Click at the given coordinates."""
        try:
            self.impl.click(x, y)
            return True
        except Exception as e:
            logger.error(f"Error clicking at ({x}, {y}): {e}")
            return False

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> bool:
        """Swipe from (x1, y1) to (x2, y2)."""
        try:
            self.impl.swipe(x1, y1, x2, y2, duration)
            return True
        except Exception as e:
            logger.error(f"Error swiping from ({x1}, {y1}) to ({x2}, {y2}): {e}")
            return False

    # Other methods

    def get_scale_ratio(self) -> float:
        """Get the scale ratio."""
        return self.impl.scale_ratio

    def ping(self) -> bool:
        """Check if the server is alive."""
        return True


class RemoteWindowsImpl(Touchable, Screenshotable):
    """
    Client implementation that connects to a remote Windows machine via XML-RPC.

    This class implements the same interfaces as WindowsImpl but forwards all
    method calls to a remote server.
    """

    def __init__(self, device: Device, host="localhost", port=8000):
        """Initialize the client with the given device, host, and port."""
        self.device = device
        self.host = host
        self.port = port
        self.proxy = xmlrpc.client.ServerProxy(
            f"http://{host}:{port}/",
            allow_none=True
        )
        # Test connection
        try:
            if not self.proxy.ping():
                raise ConnectionError(f"Failed to connect to RemoteWindowsServer at {host}:{port}")
            logger.info(f"Connected to RemoteWindowsServer at {host}:{port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to RemoteWindowsServer at {host}:{port}: {e}")

    @cached_property
    def scale_ratio(self) -> float:
        """Get the scale ratio from the remote server."""
        return cast(float, self.proxy.get_scale_ratio())

    @property
    def screen_size(self) -> tuple[int, int]:
        """Get the screen size from the remote server."""
        return cast(Tuple[int, int], self.proxy.get_screen_size())

    def detect_orientation(self) -> None | Literal['portrait'] | Literal['landscape']:
        """Detect the screen orientation from the remote server."""
        return cast(None | Literal['portrait'] | Literal['landscape'], self.proxy.detect_orientation())

    def screenshot(self) -> MatLike:
        """Take a screenshot from the remote server."""
        encoded_image = cast(str, self.proxy.screenshot())
        return _decode_image(encoded_image)

    def click(self, x: int, y: int) -> None:
        """Click at the given coordinates on the remote server."""
        if not self.proxy.click(x, y):
            raise RuntimeError(f"Failed to click at ({x}, {y})")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        """Swipe from (x1, y1) to (x2, y2) on the remote server."""
        if not self.proxy.swipe(x1, y1, x2, y2, duration):
            raise RuntimeError(f"Failed to swipe from ({x1}, {y1}) to ({x2}, {y2})")


# 编写并注册创建函数
@register_impl('remote_windows', config_model=RemoteWindowsImplConfig)
def create_remote_windows_device(config: RemoteWindowsImplConfig) -> Device:
    device = WindowsDevice()
    remote_impl = RemoteWindowsImpl(device, config.host, config.port)
    device._touch = remote_impl
    device._screenshot = remote_impl
    return device