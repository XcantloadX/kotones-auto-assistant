from typing import Literal, overload

from kotonebot.backend.image import TemplateMatchResult

from ..tasks import R
from .common import WhiteFilter
from kotonebot import action, device, image

@overload
def toolbar_home(critical: Literal[False] = False) -> TemplateMatchResult | None:
    """寻找工具栏上的首页按钮。"""
    ...

@overload
def toolbar_home(critical: Literal[True]) -> TemplateMatchResult:
    """寻找工具栏上的首页按钮。若未找到，则抛出异常。"""
    ...

@action('工具栏按钮.寻找首页', screenshot_mode='manual-inherit')
def toolbar_home(critical: bool = False):
    device.screenshot()
    if critical:
        return image.expect_wait(R.Common.ButtonToolbarHome, preprocessors=[WhiteFilter()])
    else:
        return image.find(R.Common.ButtonToolbarHome, preprocessors=[WhiteFilter()])

@overload
def toolbar_menu(critical: Literal[False] = False) -> TemplateMatchResult | None:
    """寻找工具栏上的菜单按钮。"""
    ...

@overload
def toolbar_menu(critical: Literal[True]) -> TemplateMatchResult:
    """寻找工具栏上的菜单按钮。若未找到，则抛出异常。"""
    ...

_TOOLBAR_THRESHOLD = 0.6
@action('工具栏按钮.寻找菜单', screenshot_mode='manual-inherit')
def toolbar_menu(critical: bool = False):
    device.screenshot()
    if critical:
        return image.expect_wait(R.Common.ButtonToolbarMenu, preprocessors=[WhiteFilter()], threshold=_TOOLBAR_THRESHOLD)
    else:
        return image.find(R.Common.ButtonToolbarMenu, preprocessors=[WhiteFilter()], threshold=_TOOLBAR_THRESHOLD)