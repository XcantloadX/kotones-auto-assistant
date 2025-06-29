import os
import time
import pstats
import typing
import logging
import cProfile
from importlib import resources
from functools import lru_cache
from typing import Literal, Callable, TYPE_CHECKING, TypeGuard
from typing_extensions import deprecated

import cv2
from cv2.typing import MatLike
import numpy as np

if TYPE_CHECKING:
    from kotonebot.client.protocol import Device

logger = logging.getLogger(__name__)



# Rect = tuple[int, int, int, int]
# """左上X, 左上Y, 宽度, 高度"""
# Point = tuple[int, int]
# """X, Y"""
#
# def is_rect(rect: typing.Any) -> TypeGuard[Rect]:
#     return isinstance(rect, typing.Sequence) and len(rect) == 4 and all(isinstance(i, int) for i in rect)
#
# def is_point(point: typing.Any) -> TypeGuard[Point]:
#     return isinstance(point, typing.Sequence) and len(point) == 2 and all(isinstance(i, int) for i in point)

@deprecated('使用 HintBox 类与 Devtool 工具替代')
def crop(img: MatLike, /, x1: float = 0, y1: float = 0, x2: float = 1, y2: float = 1) -> MatLike:
    """
    按比例裁剪图像。

    :param img: 图像
    :param x1: 裁剪区域左上角相对X坐标。范围 [0, 1]，默认为 0
    :param y1: 裁剪区域左上角相对Y坐标。范围 [0, 1]，默认为 0
    :param x2: 裁剪区域右下角相对X坐标。范围 [0, 1]，默认为 1
    :param y2: 裁剪区域右下角相对Y坐标。范围 [0, 1]，默认为 1
    """
    h, w = img.shape[:2]
    x1_px = int(w * x1)
    y1_px = int(h * y1) 
    x2_px = int(w * x2)
    y2_px = int(h * y2)
    return img[y1_px:y2_px, x1_px:x2_px]

# @deprecated('使用 numpy 的切片替代')
# def crop_rect(img: MatLike, rect: Rect) -> MatLike:
#     """
#     按范围裁剪图像。
#
#     :param img: 图像
#     :param rect: 裁剪区域。
#     """
#     x, y, w, h = rect
#     return img[y:y+h, x:x+w]

class DeviceHookContextManager:
    def __init__(
        self,
        device: 'Device',
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

@deprecated('使用 HintBox 类与 Devtool 工具替代')
def cropped(
    device: 'Device',
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

def until(
    condition: Callable[[], bool],
    timeout: float=60,
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
        from kotonebot.backend.context import sleep
        if self.start_time is None:
            self.start_time = time.time()
        sleep(self.interval)
        self.interval = min(self.interval * self.factor, self.max_interval)
        if self.timeout > 0 and time.time() - self.start_time > self.timeout:
            raise TimeoutError(self.timeout_message)

    def reset(self):
        self.interval = self.base_interval
        self.start_time = None

class Countdown:
    def __init__(self, sec: float):
        self.seconds = sec
        self.start_time: float | None = None

    def __str__(self):
        if self.start_time is None:
            return "Unstarted"
        else:
            return f"{self.seconds - (time.time() - self.start_time):.0f}s"
    
    @property
    def started(self) -> bool:
        return self.start_time is not None

    def start(self):
        if self.start_time is None:
            self.start_time = time.time()
        return self

    def stop(self):
        self.start_time = None
        return self

    def expired(self) -> bool:
        if self.start_time is None:
            return False
        else:
            return time.time() - self.start_time > self.seconds

    def reset(self):
        self.start_time = time.time()
        return self

class Stopwatch:
    def __init__(self):
        self.start_time: float | None = None
        self.seconds: float = 0

    def start(self):
        if self.start_time is not None:
            logger.warning('Stopwatch already started.')
        else:
            self.start_time = time.time()
        return self

    def stop(self):
        if self.start_time is None:
            logger.warning('Stopwatch not started.')
        else:
            self.seconds = time.time() - self.start_time
            self.start_time = None
        return self
        
    @property
    def milliseconds(self) -> int:
        return int(self.seconds * 1000)

class Interval:
    def __init__(self, seconds: float = 0.3):
        self.seconds = seconds
        self.start_time = time.time()
        self.last_wait_time = 0

    def wait(self):
        delta = time.time() - self.start_time
        if delta < self.seconds:
            time.sleep(self.seconds - delta)
        self.last_wait_time = time.time() - self.start_time
        self.start_time = time.time()

    def reset(self):
        self.start_time = time.time()

class Throttler:
    """
    限流器，在循环中用于限制某操作的频率。

    示例代码：
    ```python
    while True:
        device.screenshot()
        if throttler.request() and image.find(...):
            do_something()
    ```
    """
    def __init__(self, interval: float, max_requests: int | None = None):
        self.max_requests = max_requests
        self.interval = interval
        self.last_request_time: float | None = None
        self.request_count = 0

    def request(self) -> bool:
        """
        检查是否允许请求。此函数立即返回，不会阻塞。

        :return: 如果允许，返回 True，否则返回 False
        """
        current_time = time.time()
        if self.last_request_time is None or current_time - self.last_request_time >= self.interval:
            self.last_request_time = current_time
            self.request_count = 0
            return True
        else:
            return False

def lf_path(path: str) -> str:
    standalone = os.path.join('kotonebot-resource', path)
    if os.path.exists(standalone):
        return standalone
    return str(resources.files('kaa.res') / path)

class Profiler:
    """
    性能分析器。对 `cProfile` 的简单封装。

    使用方法：
    ```python
    with Profiler('profile.prof'):
        # ...

    # 或者
    profiler = Profiler('profile.prof')
    profiler.begin()
    # ...
    profiler.end()
    ```
    """
    def __init__(self, file_path: str):

        self.profiler = cProfile.Profile()
        self.stats = None
        self.file_path = file_path

    def __enter__(self):
        self.profiler.enable()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.profiler.disable()
        self.stats = pstats.Stats(self.profiler)
        self.stats.dump_stats(self.file_path)

    def begin(self):
        self.__enter__()

    def end(self):
        self.__exit__(None, None, None)

    def snakeviz(self) -> bool:
        if self.stats is None:
            logger.warning("Profiler still running. Exit/End Profiler before run snakeviz.")
            return False
        try:
            from snakeviz import cli
            cli.main([os.path.abspath(self.file_path)])
            return True

        except ImportError:
            logger.warning("snakeviz is not installed")
            return False

def measure_time(
    logger: logging.Logger | None = None,
    level: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'info',
    file_path: str | None = None
) -> Callable:
    """
    测量函数执行时间的装饰器

    :param logger: logging.Logger实例，如果为None则使用root logger
    :param level: 日志级别，可以是'debug', 'info', 'warning', 'error', 'critical'
    :param file_path: 记录执行时间的文件路径，如果提供则会将结果追加到文件中
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            execution_time = end_time - start_time
            message = f'Function {func.__name__} execution time: {execution_time:.3f}秒'
            
            # 使用提供的logger或默认logger
            log = logger or logging.getLogger()
            
            # 获取对应的日志级别方法
            log_method = getattr(log, level.lower())
            
            # 输出执行时间
            log_method(message)
            
            # 如果提供了文件路径，将结果追加到文件中
            if file_path:
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} - {message}\n')
            return result
        return wrapper
    return decorator

def cv2_imread(path: str, flags: int = cv2.IMREAD_COLOR) -> MatLike:
    """
    对 cv2.imread 的简单封装。
    支持了对带中文的路径的读取。

    :param path: 图片路径
    :param flags: cv2.imread 的 flags 参数
    :return: OpenCV 图片
    """
    img = cv2.imdecode(np.fromfile(path,dtype=np.uint8), flags)
    return img

def cv2_imwrite(path: str, img: MatLike):
    """
    对 cv2.imwrite 的简单封装。
    支持了对带中文的路径的写入。
    """
    cv2.imencode('.png', img)[1].tofile(path)
