import os
import re
import time
from functools import cache
from datetime import datetime
from typing import Callable, TYPE_CHECKING, cast, overload, Any, TypeVar, Literal

from kotonebot.client.device.adb import AdbDevice

import cv2
if TYPE_CHECKING:
    from cv2.typing import MatLike

import kotonebot.backend.image as raw_image
from kotonebot.backend.image import CropResult, TemplateMatchResult, find_crop, expect, find
from kotonebot.backend.util import Rect
from kotonebot.client import DeviceProtocol
from kotonebot.backend.ocr import Ocr, OcrResult, jp, en, StringMatchFunction

OcrLanguage = Literal['jp', 'en']
T = TypeVar('T')

class ContextOcr:
    def __init__(self, context: 'Context'):
        self.context = context
        self.__engine = jp

    def raw(self, lang: OcrLanguage) -> Ocr:
        """
        返回 `kotonebot.backend.ocr` 中的 Ocr 对象。\n
        Ocr 对象与此对象的区别是，此对象会自动截图，而 Ocr 对象需要手动传入图像参数。
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
            return self.__engine.find(self.context.device.screenshot(), args[0])
        elif len(args) == 2 and len(kwargs) == 0:
            return self.__engine.find(args[0], args[1])
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
        return self.__engine.expect(self.context.device.screenshot(), pattern)
    
    def expect_wait(self, pattern: str | re.Pattern | StringMatchFunction, timeout: float = 10) -> OcrResult:
        """
        等待指定文本出现。
        """
        start_time = time.time()
        while True:
            result = self.find(pattern)
            if result is not None:
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

    def wait_for(self, template: str, mask: str | None = None, threshold: float = 0.9, timeout: float = 10) -> bool:
        """
        等待指定图像出现。
        """
        start_time = time.time()
        while True:
            if self.find(template, mask, threshold):
                return True
            if time.time() - start_time > timeout:
                return False
            time.sleep(0.1)

    def wait_for_any(self, templates: list[str], masks: list[str | None] | None = None, threshold: float = 0.9, timeout: float = 10):
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
                if self.find(template, mask, threshold):
                    return True
            if time.time() - start_time > timeout:
                return False
            time.sleep(0.1)

    def expect_wait(
            self,
            template: str,
            mask: str | None = None,
            threshold: float = 0.9,
            timeout: float = 10
        ) -> TemplateMatchResult:
        """
        等待指定图像出现。
        """
        start_time = time.time()
        while True:
            ret = self.find(template, mask, threshold)
            if ret is not None:
                return ret
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for {template}")
            time.sleep(0.1)

    def expect_wait_any(
            self,
            templates: list[str],
            masks: list[str | None] | None = None,
            threshold: float = 0.9,
            timeout: float = 10
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
                ret = self.find(template, mask, threshold)
                if ret is not None:
                    return ret
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for any of {templates}")
            time.sleep(0.1)


    def expect(self, template: str, mask: str | None = None, threshold: float = 0.9) -> TemplateMatchResult:
        """
        寻找指定图像。

        与 `find()` 的区别在于，`expect()` 未找到时会抛出异常。
        """
        return expect(self.context.device.screenshot(), template, mask, threshold=threshold)

    def find(self, template: str, mask: str | None = None, threshold: float = 0.9):
        """
        寻找指定图像。
        """
        return find(self.context.device.screenshot(), template, mask, threshold=threshold)

    def find_crop(
            self,
            template: str,
            mask: str | None = None,
            threshold: float = 0.999,
        ) -> list[CropResult]:
        """
        在当前设备画面中查找指定模板，并裁剪出结果。
        """
        return find_crop(
            self.context.device.screenshot(),
            template,
            mask,
            threshold=threshold,
        )

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


@cache
def _forward_from(getter: Callable[[], T]) -> T:
    class Forwarded:
        def __getattr__(self, name: str) -> Any:
            return getattr(getter(), name)

        def __repr__(self) -> str:
            return f"Forwarded({object})"
    return cast(T, Forwarded())  

class Context:
    def __init__(self):
        # HACK: 暂时写死
        from adbutils import adb
        adb.connect('127.0.0.1:16384')
        self.__device = AdbDevice(adb.device_list()[0])
        self.__ocr = ContextOcr(self)
        self.__image = ContextImage(self)
        self.__vars = ContextGlobalVars()
        self.__debug = ContextDebug(self)
        self.actions = []

    def inject_device(self, device: DeviceProtocol):
        self.__device = device

    @property
    def device(self) -> DeviceProtocol:
        return cast(DeviceProtocol, _forward_from(lambda: self.__device))

    @property
    def ocr(self) -> 'ContextOcr':
        return cast(ContextOcr, _forward_from(lambda: self.__ocr))
    
    @property
    def image(self) -> 'ContextImage':
        return cast(ContextImage, _forward_from(lambda: self.__image))

    @property
    def vars(self) -> 'ContextGlobalVars':
        return cast(ContextGlobalVars, _forward_from(lambda: self.__vars))
    
    @property
    def debug(self) -> 'ContextDebug':
        return cast(ContextDebug, _forward_from(lambda: self.__debug))

# 暴露 Context 的属性到模块级别
_c = Context()
device: DeviceProtocol = _c.device
"""当前正在执行任务的设备。"""
ocr: ContextOcr = _c.ocr
"""OCR 引擎。"""
image: ContextImage = _c.image
"""图像识别。"""
vars: ContextGlobalVars = _c.vars
"""全局变量。"""
debug: ContextDebug = _c.debug
"""调试工具。"""

# def __getattr__(name: str) -> Any:
#     return getattr(_c, name)

