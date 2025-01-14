import os
import re
import time
from datetime import datetime
from typing import (
    Callable,
    cast,
    overload,
    Any,
    TypeVar,
    Literal,
    ParamSpec,
    Concatenate,
)

import cv2
from cv2.typing import MatLike

from kotonebot.client import DeviceABC
from kotonebot.backend.util import Rect
import kotonebot.backend.image as raw_image
from kotonebot.client.device.adb import AdbDevice
from kotonebot.backend.image import (
    CropResult,
    TemplateMatchResult,
    MultipleTemplateMatchResult,
    find_crop,
    expect,
    find,
    find_any,
    find_many,
)
from kotonebot.backend.color import find_rgb
from kotonebot.backend.ocr import Ocr, OcrResult, jp, en, StringMatchFunction

OcrLanguage = Literal['jp', 'en']

# https://stackoverflow.com/questions/74714300/paramspec-for-a-pre-defined-function-without-using-generic-callablep
T = TypeVar('T')
P = ParamSpec('P')
ContextClass = TypeVar("ContextClass")
def context(
    _: Callable[Concatenate[MatLike, P], T] # 输入函数
) -> Callable[
    [Callable[Concatenate[ContextClass, P], T]], # 被装饰函数
    Callable[Concatenate[ContextClass, P], T] # 结果函数
]:
    """
    用于标记 Context 类方法的装饰器。
    此装饰器仅用于辅助类型标注，运行时无实际功能。

    装饰器输入的函数类型为 `(img: MatLike, a, b, c, ...) -> T`，
    被装饰的函数类型为 `(self: ContextClass, *args, **kwargs) -> T`，
    结果类型为 `(self: ContextClass, a, b, c, ...) -> T`。

    也就是说，`@context` 会把输入函数的第一个参数 `img: MatLike` 删除，
    然后再添加 `self` 作为第一个参数。

    【例】
    ```python
    def find_image(
        img: MatLike,
        mask: MatLike,
        threshold: float = 0.9
    ) -> TemplateMatchResult | None:
        ...
    ```
    ```python
    class ContextImage:
        @context(find_image)
        def find_image(self, *args, **kwargs):
            return find_image(
                self.context.device.screenshot(),
                *args,
                **kwargs
            )

    ```
    ```python

    c = ContextImage()
    c.find_image()
    # 此函数类型推断为 (
    #   self: ContextImage,
    #   img: MatLike,
    #   mask: MatLike,
    #   threshold: float = 0.9
    # ) -> TemplateMatchResult | None
    ```
    """
    def _decorator(func):
        return func
    return _decorator

class ContextOcr:
    def __init__(self, context: 'Context'):
        self.context = context
        self.__engine = jp

    def raw(self, lang: OcrLanguage = 'jp') -> Ocr:
        """
        返回 `kotonebot.backend.ocr` 中的 Ocr 对象。\n
        Ocr 对象与此对象（ContextOcr）的区别是，此对象会自动截图，而 Ocr 对象需要手动传入图像参数。
        """
        match lang:
            case 'jp':
                return jp
            case 'en':
                return en
            case _:
                raise ValueError(f"Invalid language: {lang}")

    @overload
    def ocr(self) -> list[OcrResult]:
        """OCR 当前设备画面。"""
        ...

    @overload
    def ocr(self, img: 'MatLike') -> list[OcrResult]:
        """OCR 指定图像。"""
        ...

    def ocr(self, img: 'MatLike | None' = None) -> list[OcrResult]:
        """OCR 当前设备画面或指定图像。"""
        if img is None:
            return self.__engine.ocr(self.context.device.screenshot())
        return self.__engine.ocr(img)
    
    @overload
    def find(self, pattern: str | re.Pattern | StringMatchFunction) -> OcrResult | None:
        ...

    @overload
    def find(self, img: 'MatLike', pattern: str | re.Pattern | StringMatchFunction) -> OcrResult | None:
        ...
    
    def find(self, *args, **kwargs) -> OcrResult | None:
        """检查指定图像是否包含指定文本。"""
        if len(args) == 1 and len(kwargs) == 0:
            ret = self.__engine.find(self.context.device.screenshot(), args[0])
            self.context.device.last_find = ret
            return ret
        elif len(args) == 2 and len(kwargs) == 0:
            ret = self.__engine.find(args[0], args[1])
            self.context.device.last_find = ret
            return ret
        else:
            raise ValueError("Invalid arguments")
    
    def expect(
            self,
            pattern: str | re.Pattern | StringMatchFunction
        ) -> OcrResult:
        """
        检查当前设备画面是否包含指定文本。

        与 `find()` 的区别在于，`expect()` 未找到时会抛出异常。
        """
        ret = self.__engine.expect(self.context.device.screenshot(), pattern)
        self.context.device.last_find = ret
        return ret
    
    def expect_wait(self, pattern: str | re.Pattern | StringMatchFunction, timeout: float = 10) -> OcrResult:
        """
        等待指定文本出现。
        """
        start_time = time.time()
        while True:
            result = self.find(pattern)
            if result is not None:
                self.context.device.last_find = result
                return result
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for {pattern}")
            time.sleep(0.1)

    def wait_for(self, pattern: str | re.Pattern | StringMatchFunction, timeout: float = 10) -> OcrResult | None:
        """
        等待指定文本出现。
        """
        start_time = time.time()
        while True:
            result = self.find(pattern)
            if result is not None:
                self.context.device.last_find = result
                return result
            if time.time() - start_time > timeout:
                return None
            time.sleep(0.1)


class ContextImage:
    def __init__(self, context: 'Context', crop_rect: Rect | None = None):
        self.context = context
        self.crop_rect = crop_rect

    def raw(self):
        return raw_image

    def wait_for(
            self,
            template: MatLike | str,
            mask: MatLike | str | None = None,
            threshold: float = 0.9,
            timeout: float = 10,
            colored: bool = False,
            interval: float = 0.1,
            *,
            transparent: bool = False
        ) -> TemplateMatchResult | None:
        """
        等待指定图像出现。
        """
        start_time = time.time()
        while True:
            ret = self.find(template, mask, transparent=transparent, threshold=threshold, colored=colored)
            if ret is not None:
                self.context.device.last_find = ret
                return ret
            if time.time() - start_time > timeout:
                return None
            time.sleep(interval)

    def wait_for_any(
            self,
            templates: list[str],
            masks: list[str | None] | None = None,
            threshold: float = 0.9,
            timeout: float = 10,
            colored: bool = False,
            *,
            transparent: bool = False
        ):
        """
        等待指定图像中的任意一个出现。
        """
        if masks is None:
            _masks = [None] * len(templates)
        else:
            _masks = masks
        start_time = time.time()
        while True:
            for template, mask in zip(templates, _masks):
                if self.find(template, mask, transparent=transparent, threshold=threshold, colored=colored):
                    return True
            if time.time() - start_time > timeout:
                return False
            time.sleep(0.1)

    def expect_wait(
            self,
            template: str,
            mask: str | None = None,
            threshold: float = 0.9,
            timeout: float = 10,
            colored: bool = False,
            *,
            transparent: bool = False
        ) -> TemplateMatchResult:
        """
        等待指定图像出现。
        """
        start_time = time.time()
        while True:
            ret = self.find(template, mask, transparent=transparent, threshold=threshold, colored=colored)
            if ret is not None:
                self.context.device.last_find = ret
                return ret
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for {template}")
            time.sleep(0.1)

    def expect_wait_any(
            self,
            templates: list[str],
            masks: list[str | None] | None = None,
            threshold: float = 0.9,
            timeout: float = 10,
            colored: bool = False,
            *,
            transparent: bool = False
        ) -> TemplateMatchResult:
        """
        等待指定图像中的任意一个出现。
        """
        if masks is None:
            _masks = [None] * len(templates)
        else:
            _masks = masks
        start_time = time.time()
        while True:
            for template, mask in zip(templates, _masks):
                ret = self.find(template, mask, transparent=transparent, threshold=threshold, colored=colored)
                if ret is not None:
                    self.context.device.last_find = ret
                    return ret
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for any of {templates}")
            time.sleep(0.1)

    @context(expect)
    def expect(self, *args, **kwargs):
        ret = expect(self.context.device.screenshot(), *args, **kwargs)
        self.context.device.last_find = ret
        return ret

    @context(find)
    def find(self, *args, **kwargs):
        ret = find(self.context.device.screenshot(), *args, **kwargs)
        self.context.device.last_find = ret
        return ret

    @context(find_many)
    def find_many(self, *args, **kwargs):
        return find_many(self.context.device.screenshot(), *args, **kwargs)

    @context(find_any)
    def find_any(self, *args, **kwargs):
        ret = find_any(self.context.device.screenshot(), *args, **kwargs)
        self.context.device.last_find = ret
        return ret

    @context(find_crop)
    def find_crop_many(self, *args, **kwargs):
        return find_crop(self.context.device.screenshot(), *args, **kwargs)
    

class ContextGlobalVars:
    def __init__(self):
        self.auto_collect: bool = False
        """遇到未知P饮料/卡片时，是否自动截图并收集"""
        self.debug: bool = True


class ContextDebug:
    def __init__(self, context: 'Context'):
        self.__context = context
        self.save_images: bool = False
        self.save_images_dir: str = "debug_images"
    
    def show(self, img: 'MatLike', title: str = "Debug"):
        if not self.__context.vars.debug:
            return
        if self.save_images:
            if not os.path.exists(self.save_images_dir):
                os.makedirs(self.save_images_dir)
            now = datetime.now()
            time_str = now.strftime("%Y-%m-%d %H-%M-%S") + f".{now.microsecond // 1000:03d}"
            cv2.imwrite(f"{self.save_images_dir}/{title}_{time_str}.png", img)
        cv2.imshow(title, img)
        cv2.waitKey(1)


class ContextColor:
    def __init__(self, context: 'Context'):
        self.context = context

    @context(find_rgb)
    def find_rgb(self, *args, **kwargs):
        return find_rgb(self.context.device.screenshot(), *args, **kwargs)


class Forwarded:
    def __init__(self, getter: Callable[[], T] | None = None, name: str | None = None):
        self._FORWARD_getter = getter
        self._FORWARD_name = name

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_FORWARD_'):
            return object.__getattribute__(self, name)
        if self._FORWARD_getter is None:
            raise ValueError(f"Forwarded object {self._FORWARD_name} called before initialization.")
        return getattr(self._FORWARD_getter(), name)
    
    def __setattr__(self, name: str, value: Any):
        if name.startswith('_FORWARD_'):
            return object.__setattr__(self, name, value)
        if self._FORWARD_getter is None:
            raise ValueError(f"Forwarded object {self._FORWARD_name} called before initialization.")
        setattr(self._FORWARD_getter(), name, value)

class Context:
    def __init__(self):
        # HACK: 暂时写死
        from adbutils import adb
        adb.connect('127.0.0.1:5555')
        self.__device = AdbDevice(adb.device_list()[0])
        # self.__device = None
        self.__ocr = ContextOcr(self)
        self.__image = ContextImage(self)
        self.__color = ContextColor(self)
        self.__vars = ContextGlobalVars()
        self.__debug = ContextDebug(self)
        self.actions = []

    def inject_device(self, device: DeviceABC):
        self.__device = device

    @property
    def device(self) -> DeviceABC:
        return self.__device

    @property
    def ocr(self) -> 'ContextOcr':
        return self.__ocr
    
    @property
    def image(self) -> 'ContextImage':
        return self.__image

    @property
    def color(self) -> 'ContextColor':
        return self.__color

    @property
    def vars(self) -> 'ContextGlobalVars':
        return self.__vars
    
    @property
    def debug(self) -> 'ContextDebug':
        return self.__debug

# 暴露 Context 的属性到模块级别
_c: Context | None = None
device: DeviceABC = cast(DeviceABC, Forwarded(name="device"))
"""当前正在执行任务的设备。"""
ocr: ContextOcr = cast(ContextOcr, Forwarded(name="ocr"))
"""OCR 引擎。"""
image: ContextImage = cast(ContextImage, Forwarded(name="image"))
"""图像识别。"""
color: ContextColor = cast(ContextColor, Forwarded(name="color"))
"""颜色识别。"""
vars: ContextGlobalVars = cast(ContextGlobalVars, Forwarded(name="vars"))
"""全局变量。"""
debug: ContextDebug = cast(ContextDebug, Forwarded(name="debug"))
"""调试工具。"""

def init_context():
    global _c, device, ocr, image, color, vars, debug
    _c = Context()
    device._FORWARD_getter = lambda: _c.device # type: ignore
    ocr._FORWARD_getter = lambda: _c.ocr # type: ignore
    image._FORWARD_getter = lambda: _c.image # type: ignore
    color._FORWARD_getter = lambda: _c.color # type: ignore
    vars._FORWARD_getter = lambda: _c.vars # type: ignore
    debug._FORWARD_getter = lambda: _c.debug # type: ignore

