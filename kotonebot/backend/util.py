from functools import lru_cache
import re
import typing
from typing import NamedTuple, Callable

from cv2.typing import MatLike
from thefuzz import fuzz as _fuzz

class TaskInfo(NamedTuple):
    name: str
    description: str
    entry: Callable[[], None]

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

def cropper(x1: float, y1: float, x2: float, y2: float) -> Callable[[MatLike], MatLike]:
    return lambda img: crop(img, x1, y1, x2, y2)

def cropper_y(y1: float, y2: float) -> Callable[[MatLike], MatLike]:
    return lambda img: crop_y(img, y1, y2)

def cropper_x(x1: float, x2: float) -> Callable[[MatLike], MatLike]:
    return lambda img: crop_x(img, x1, x2)  
