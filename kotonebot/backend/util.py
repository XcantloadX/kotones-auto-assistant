import re
import time
import typing
from time import sleep
from functools import lru_cache
from typing import Literal, NamedTuple, Callable, TYPE_CHECKING

import cv2
from cv2.typing import MatLike
from thefuzz import fuzz as _fuzz

if TYPE_CHECKING:
    from kotonebot.client.protocol import DeviceABC

class TaskInfo(NamedTuple):
    name: str
    description: str
    entry: Callable[[], None]

class UnrecoverableError(Exception):
    pass

Rect = typing.Sequence[int]
"""左上X, 左上Y, 宽度, 高度"""

def is_rect(rect: typing.Any) -> bool:
    return isinstance(rect, typing.Sequence) and len(rect) == 4 and all(isinstance(i, int) for i in rect)

@lru_cache(maxsize=1000)
def fuzz(text: str) -> Callable[[str], bool]:
    """返回 fuzzy 算法的字符串匹配函数。"""
    f = lambda s: _fuzz.ratio(s, text) > 90
    f.__repr__ = lambda: f"fuzzy({text})"
    f.__name__ = f"fuzzy({text})"
    return f

@lru_cache(maxsize=1000)
def regex(regex: str) -> Callable[[str], bool]:
    """返回正则表达式字符串匹配函数。"""
    f = lambda s: re.match(regex, s) is not None
    f.__repr__ = lambda: f"regex({regex})"
    f.__name__ = f"regex({regex})"
    return f

@lru_cache(maxsize=1000)
def contains(text: str) -> Callable[[str], bool]:
    """返回包含指定文本的函数。"""
    f = lambda s: text in s
    f.__repr__ = lambda: f"contains({text})"
    f.__name__ = f"contains({text})"
    return f


def crop(img: MatLike, x1: float, y1: float, x2: float, y2: float) -> MatLike:
    """按比例裁剪图像"""
    h, w = img.shape[:2]
    x1_px = int(w * x1)
    y1_px = int(h * y1) 
    x2_px = int(w * x2)
    y2_px = int(h * y2)
    return img[y1_px:y2_px, x1_px:x2_px]

def crop_y(img: MatLike, y1: float, y2: float) -> MatLike:
    """按比例垂直裁剪图像"""
    h, _ = img.shape[:2]
    y1_px = int(h * y1)
    y2_px = int(h * y2)
    return img[y1_px:y2_px, :]

def crop_x(img: MatLike, x1: float, x2: float) -> MatLike:
    """按比例水平裁剪图像"""
    _, w = img.shape[:2]
    x1_px = int(w * x1)
    x2_px = int(w * x2)
    return img[:, x1_px:x2_px]

CropperParams = tuple[Literal['x', 'y'], float, float]
def x(from_: float=0, to: float=1) -> CropperParams:
    return ('x', from_, to)

def y(from_: float=0, to: float=1) -> CropperParams:
    return ('y', from_, to)

def cropper(*params: CropperParams) -> Callable[[MatLike], MatLike]:
    if len(params) == 0:
        raise ValueError("cropper() takes at least 1 positional argument.")
    elif len(params) > 2:
        raise ValueError("cropper() takes at most 2 positional arguments.")
    x1, x2, y1, y2 = 0, 1, 0, 1
    for param in params:
        if param[0] == 'x':
            x1, x2 = param[1], param[2]
        elif param[0] == 'y':
            y1, y2 = param[1], param[2]
    return lambda img: crop(img, x1, y1, x2, y2)

def cropper_y(y1: float, y2: float) -> Callable[[MatLike], MatLike]:
    return lambda img: crop_y(img, y1, y2)

def cropper_x(x1: float, x2: float) -> Callable[[MatLike], MatLike]:
    return lambda img: crop_x(img, x1, x2)  

class DeviceHookContextManager:
    def __init__(
        self,
        device: 'DeviceABC',
        *,
        screenshot_hook_before: Callable[[], MatLike|None] | None = None,
        screenshot_hook_after: Callable[[MatLike], MatLike] | None = None,
        click_hook_before: Callable[[int, int], tuple[int, int]] | None = None,
    ):
        self.device = device
        self.screenshot_hook_before = screenshot_hook_before
        self.screenshot_hook_after = screenshot_hook_after
        self.click_hook_before = click_hook_before

        self.old_screenshot_hook_before = self.device.screenshot_hook_before
        self.old_screenshot_hook_after = self.device.screenshot_hook_after
    
    def __enter__(self):
        if self.screenshot_hook_before is not None:
            self.device.screenshot_hook_before = self.screenshot_hook_before
        if self.screenshot_hook_after is not None:
            self.device.screenshot_hook_after = self.screenshot_hook_after
        if self.click_hook_before is not None:
            self.device.click_hooks_before.append(self.click_hook_before)
        return self.device
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.device.screenshot_hook_before = self.old_screenshot_hook_before
        self.device.screenshot_hook_after = self.old_screenshot_hook_after
        if self.click_hook_before is not None:
            self.device.click_hooks_before.remove(self.click_hook_before)

def cropped(
    device: 'DeviceABC',
    x1: float = 0,
    y1: float = 0,
    x2: float = 1,
    y2: float = 1,
) -> DeviceHookContextManager:
    """
    Hook 设备截图与点击操作，将截图裁剪为指定区域，并调整点击坐标。

    在进行 OCR 识别或模板匹配时，可以先使用此函数缩小图像，加快速度。

    :param device: 设备对象
    :param x1: 裁剪区域左上角相对X坐标。范围 [0, 1]，默认为 0
    :param y1: 裁剪区域左上角相对Y坐标。范围 [0, 1]，默认为 0
    :param x2: 裁剪区域右下角相对X坐标。范围 [0, 1]，默认为 1
    :param y2: 裁剪区域右下角相对Y坐标。范围 [0, 1]，默认为 1
    """
    def _screenshot_hook(img: MatLike) -> MatLike:
        return crop(img, x1, y1, x2, y2)
    def _click_hook(x: int, y: int) -> tuple[int, int]:
        w, h = device.screen_size
        x_px = int(x1 * w + x)
        y_px = int(y1 * h + y)
        return x_px, y_px
    return DeviceHookContextManager(
        device,
        screenshot_hook_after=_screenshot_hook,
        click_hook_before=_click_hook,
    )

def grayscaled(img: MatLike | str) -> MatLike:
    if isinstance(img, str):
        img = cv2.imread(img)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

@lru_cache
def grayscale_cached(img: MatLike | str) -> MatLike:
    return grayscaled(img)


class AdaptiveWait:
    """
    自适应延时。延迟时间会随着时间逐渐增加，直到达到最大延迟时间。
    """
    def __init__(
        self,
        base_interval: float = 0.5,
        max_interval: float = 10,
        *,
        timeout: float = -1,
        timeout_message: str = "Timeout",
        factor: float = 1.15,
    ):
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.interval = base_interval
        self.factor = factor
        self.timeout = timeout
        self.start_time: float | None = time.time()
        self.timeout_message = timeout_message

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.reset()

    def __call__(self):
        if self.start_time is None:
            self.start_time = time.time()
        sleep(self.interval)
        self.interval = min(self.interval * self.factor, self.max_interval)
        if self.timeout > 0 and time.time() - self.start_time > self.timeout:
            raise TimeoutError(self.timeout_message)

    def reset(self):
        self.interval = self.base_interval
        self.start_time = None
