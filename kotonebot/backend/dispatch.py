import time
import uuid
import logging
import inspect
from logging import Logger
from types import CodeType
from dataclasses import dataclass
from typing import Annotated, Any, Callable, Concatenate, Sequence, TypeVar, ParamSpec, Literal, Protocol, cast
from typing_extensions import deprecated

from dataclasses import dataclass

from kotonebot.backend.ocr import StringMatchFunction
from kotonebot.primitives import Rect, is_rect

from .core import Image

logger = logging.getLogger(__name__)
P = ParamSpec('P')
R = TypeVar('R')
ThenAction = Literal['click', 'log']
DoAction = Literal['click']
# TODO: 需要找个地方统一管理这些属性名
ATTR_DISPATCHER_MARK = '__kb_dispatcher_mark'
ATTR_ORIGINAL_FUNC = '_kb_inner'


class DispatchFunc: pass

wrapper_to_func: dict[Callable, Callable] = {}

class DispatcherContext:
    def __init__(self):
        self.finished: bool = False
        self._first_run: bool = True
    
    def finish(self):
        """标记已完成 dispatcher 循环。循环将在下次条件检测时退出。"""
        self.finished = True

    def expand(self, func: Annotated[Callable[[], Any], DispatchFunc], ignore_finish: bool = True):
        """
        调用其他 dispatcher 函数。

        使用 `expand` 和直接调用的区别是：
        * 直接调用会执行 while 循环，直到满足结束条件
        * 而使用 `expand` 则只会执行一次。效果类似于将目标函数里的代码直接复制粘贴过来。
        """
        # 获取原始函数
        original_func = func
        while not getattr(original_func, ATTR_DISPATCHER_MARK, False):
            original_func = getattr(original_func, ATTR_ORIGINAL_FUNC)
        original_func = getattr(original_func, ATTR_ORIGINAL_FUNC)

        if not original_func:
            raise ValueError(f'{repr(func)} is not a dispatcher function.')
        elif not callable(original_func):
            raise ValueError(f'{repr(original_func)} is not callable.')
        original_func = cast(Callable[[DispatcherContext], Any], original_func)

        old_finished = self.finished
        ret = original_func(self)
        if ignore_finish:
            self.finished = old_finished
        return ret

    @property
    def beginning(self) -> bool:
        """是否为第一次运行"""
        return self._first_run
    
    @property
    def finishing(self) -> bool:
        """是否即将结束运行"""
        return self.finished

@deprecated('使用 SimpleDispatcher 类或 while 循环替代')
def dispatcher(
        func: Callable[Concatenate[DispatcherContext, P], R],
        *,
        fragment: bool = False
    ) -> Annotated[Callable[P, R], DispatchFunc]:
    """
    注意：\n
    此装饰器必须在应用 @action/@task 装饰器后再应用，且 `screenshot_mode='manual'` 参数必须设置。
    或者也可以使用 @action/@task 装饰器中的 `dispatcher=True` 参数，
    那么就没有上面两个要求了。

    :param fragment:
        片段模式，默认不启用。
        启用后，被装饰函数将会只执行依次，
        而不会一直循环到 ctx.finish() 被调用。
    """
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        ctx = DispatcherContext()
        while not ctx.finished:
            from kotonebot import device
            device.screenshot()
            ret = func(ctx, *args, **kwargs)
            ctx._first_run = False
        return ret
    def fragment_wrapper(*args: P.args, **kwargs: P.kwargs):
        ctx = DispatcherContext()
        from kotonebot import device
        device.screenshot()
        return func(ctx, *args, **kwargs)
    setattr(wrapper, ATTR_ORIGINAL_FUNC, func)
    setattr(fragment_wrapper, ATTR_ORIGINAL_FUNC, func)
    setattr(wrapper, ATTR_DISPATCHER_MARK, True)
    setattr(fragment_wrapper, ATTR_DISPATCHER_MARK, True)
    wrapper_to_func[wrapper] = func
    if fragment:
        return fragment_wrapper

    else:
        return wrapper

@dataclass
class ClickParams:
    finish: bool = False
    log: str | None = None

class ClickCenter:
    def __init__(self, sd: 'SimpleDispatcher', target: Image | str | StringMatchFunction | Literal['center'], *, params: ClickParams = ClickParams()):
        self.target = target
        self.params = params
        self.sd = sd

    def __call__(self):
        from kotonebot import device
        if self.params.log:
            self.sd.logger.info(self.params.log)
        device.click_center()
        if self.params.finish:
            self.sd.finished = True

class ClickImage:
    def __init__(self, sd: 'SimpleDispatcher', image: Image, *, params: ClickParams = ClickParams()):
        self.image = image
        self.params = params
        self.sd = sd

    def __call__(self):
        from kotonebot import device, image
        if image.find(self.image):
            if self.params.log:
                self.sd.logger.info(self.params.log)
            device.click()
            if self.params.finish:
                self.sd.finished = True

class ClickImageAny:
    def __init__(self, sd: 'SimpleDispatcher', images: list[Image], params: ClickParams = ClickParams()):
        self.images = images
        self.params = params
        self.sd = sd
    
    def __call__(self):
        from kotonebot import device, image
        if image.find_multi(self.images):
            if self.params.log:
                self.sd.logger.info(self.params.log)
            device.click()
            if self.params.finish:
                self.sd.finished = True

class ClickText:
    def __init__(
            self,
            sd: 'SimpleDispatcher',
            text: str | StringMatchFunction,
            params: ClickParams = ClickParams()
        ):
        self.text = text
        self.params = params
        self.sd = sd

    def __call__(self):
        from kotonebot import device, ocr
        if ocr.find(self.text):
            if self.params.log:
                self.sd.logger.info(self.params.log)
            device.click()
            if self.params.finish:
                self.sd.finished = True

class ClickRect:
    def __init__(self, sd: 'SimpleDispatcher', rect: Rect, *, params: ClickParams = ClickParams()):
        self.rect = rect
        self.params = params
        self.sd = sd

    def __call__(self):
        from kotonebot import device
        if device.click(self.rect):
            if self.params.log:
                self.sd.logger.info(self.params.log)
            if self.params.finish:
                self.sd.finished = True

class UntilText:
    def __init__(
            self,
            sd: 'SimpleDispatcher',
            text: str | StringMatchFunction,
            *,
            rect: Rect | None = None,
            result: Any | None = None
        ):
        self.text = text
        self.sd = sd
        self.rect = rect
        self.result = result

    def __call__(self):
        from kotonebot import ocr
        if ocr.find(self.text, rect=self.rect):
            self.sd.finished = True
            self.sd.result = self.result

class UntilImage:
    def __init__(
            self,
            sd: 'SimpleDispatcher',
            image: Image,
            *,
            rect: Rect | None = None,
            result: Any | None = None
        ):
        self.image = image
        self.sd = sd
        self.rect = rect
        self.result = result

    def __call__(self):
        from kotonebot import image
        if self.rect:
            logger.warning(f'UntilImage with rect is deprecated. Use UntilText instead.')
        if image.find(self.image):
            self.sd.finished = True
            self.sd.result = self.result

class SimpleDispatcher:
    def __init__(self, name: str, *, min_interval: float = 0.3):
        self.name = name
        self.logger = logging.getLogger(f'SimpleDispatcher of {name}')
        self.blocks: list[Callable] = []
        self.finished: bool = False
        self.result: Any | None = None
        self.min_interval = min_interval
        self.timeout_value: float | None = None
        self.timeout_critical: bool = False
        self.__last_run_time: float = 0

    def click(
        self,
        target: Image | StringMatchFunction | Literal['center'] | Rect,
        *,
        finish: bool = False,
        log: str | None = None
    ):
        params = ClickParams(finish=finish, log=log)
        if isinstance(target, Image):
            self.blocks.append(ClickImage(self, target, params=params))
        elif is_rect(target):
            self.blocks.append(ClickRect(self, target, params=params))
        elif callable(target):
            self.blocks.append(ClickText(self, target, params=params))
        elif target == 'center':
            self.blocks.append(ClickCenter(self, target='center', params=params))
        else:
            raise ValueError(f'Invalid target: {target}')
        return self

    def click_any(
        self,
        target: list[Image],
        *,
        finish: bool = False,
        log: str | None = None
    ):
        params = ClickParams(finish=finish, log=log)
        self.blocks.append(ClickImageAny(self, target, params))
        return self

    def until(
        self,
        text: StringMatchFunction | Image,
        *,
        rect: Rect | None = None,
        result: Any | None = None
    ):
        if isinstance(text, Image):
            self.blocks.append(UntilImage(self, text, rect=rect, result=result))
        else:
            self.blocks.append(UntilText(self, text, rect=rect, result=result))
        return self

    def timeout(self, timeout: float, *, critical: bool = False, result: Any | None = None):
        self.timeout_value = timeout
        self.timeout_critical = critical
        self.timeout_result = result
        return self

    def run(self):
        from kotonebot import device, sleep
        while True:
            logger.debug(f'Running dispatcher "{self.name}"')
            time_delta = time.time() - self.__last_run_time
            if time_delta < self.min_interval:
                sleep(self.min_interval - time_delta)
            # 依次执行 block
            done = False
            for block in self.blocks:
                block()
                if self.finished:
                    done = True
                    break
            if done:
                break

            self.__last_run_time = time.time()
            if self.timeout_value and time.time() - self.__last_run_time > self.timeout_value:
                if self.timeout_critical:
                    raise TimeoutError(f'Dispatcher "{self.name}" timed out.')
                else:
                    self.logger.warning(f'Dispatcher "{self.name}" timed out.')
                    self.result = self.timeout_result
                    break
            device.screenshot()
        return self.result