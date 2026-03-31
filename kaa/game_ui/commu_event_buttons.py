from dataclasses import dataclass
from typing import Sequence

from kotonebot.primitives import Rect, RectTuple
from kotonebot.backend.core import HintBox
from kotonebot.backend.color import HsvColor
from kotonebot import action, device, ocr, sleep
from .common import filter_rectangles, WHITE_LOW, WHITE_HIGH

@dataclass
class EventButton:
    rect: Rect
    selected: bool
    description: str
    title: str

def web2cv(hsv: HsvColor):
    return (int(hsv[0]/360*180), int(hsv[1]/100*255), int(hsv[2]/100*255))



PINK_TARGET = (335, 78, 95)
PINK_LOW = (300, 70, 90)
PINK_HIGH = (350, 80, 100)

BLUE_TARGET = (210, 88, 93)
BLUE_LOW = (200, 80, 90)
BLUE_HIGH = (220, 90, 100)

YELLOW_TARGET = (39, 81, 97)
YELLOW_LOW = (30, 70, 90)
YELLOW_HIGH = (45, 90, 100)

ORANGE_RANGE = ((14, 178, 229), (16, 229, 255))

DEFAULT_COLORS = [
    (web2cv(PINK_LOW), web2cv(PINK_HIGH)),
    (web2cv(YELLOW_LOW), web2cv(YELLOW_HIGH)),
    (web2cv(BLUE_LOW), web2cv(BLUE_HIGH)),
    ORANGE_RANGE
]

# 参考图片：
# [screenshots/produce/action_study3.png]
# TODO: CommuEventButtonUI 需要能够识别不可用的按钮
class CommuEventButtonUI:
    """
    此类用于识别培育中交流中出现的事件/效果里的按钮。

    例如外出（おでかけ）、冲刺周课程选择这两个页面的选择按钮。
    """
    def __init__(
        self,
        selected_colors: Sequence[tuple[HsvColor, HsvColor]] = DEFAULT_COLORS,
        rect: HintBox | None = None
    ):
        """
        :param selected_colors: 按钮选中后的主题色。
        :param rect: 识别范围
        """
        from ..tasks import R
        self.color_ranges = selected_colors
        self.rect = rect or R.InPurodyuusu.BoxCommuEventButtonsArea

    @action('交流事件按钮.识别选中', screenshot_mode='manual-inherit')
    def selected(self, description: bool = True, title: bool = False) -> EventButton | None:
        img = device.screenshot()
        for i, color_range in enumerate(self.color_ranges):
            rects = filter_rectangles(img, color_range, 7, 500, rect=self.rect)
            if len(rects) > 0:
                desc_text = self.description() if description else ''
                title_text = ocr.ocr(rect=rects[0]).squash().text if title else ''
                return EventButton(rects[0], True, desc_text, title_text)
        return None

    @action('交流事件按钮.识别按钮', screenshot_mode='manual-inherit')
    def all(self, description: bool = True, title: bool = False) -> list[EventButton]:
        """
        识别所有按钮的位置以及选中后的描述文本

        前置条件：当前显示了交流事件按钮\n
        结束状态：-

        :param description: 是否识别描述文本。
        :param title: 是否识别标题。
        """
        img = device.screenshot()
        rects = filter_rectangles(img, (WHITE_LOW, WHITE_HIGH), 7, 500, rect=self.rect)
        if not rects:
            return []
        selected = self.selected()
        result: list[EventButton] = []
        for rect in rects:
            desc_text = ''
            title_text = ''
            if title:
                title_text = ocr.ocr(rect=rect).squash().text
            if description:
                device.click(rect)
                sleep(0.15)
                device.screenshot()
                desc_text = self.description()
            result.append(EventButton(rect, False, desc_text, title_text))
        # 修改最后一次点击的按钮为 selected 状态
        if len(result) > 0:
            result[-1].selected = True
        if selected is not None:
            result.append(selected)
            selected.selected = False
        result.sort(key=lambda x: x.rect.y1)
        return result

    @action('交流事件按钮.识别描述', screenshot_mode='manual-inherit')
    def description(self) -> str:
        """
        识别当前选中按钮的描述文本

        前置条件：有选中按钮\n
        结束状态：-
        """
        img = device.screenshot()
        rects = filter_rectangles(img, (WHITE_LOW, WHITE_HIGH), 3, 1000, rect=self.rect)
        rects.sort(key=lambda x: x.y1)
        # TODO: 这里 rects 可能为空，需要加入判断重试
        ocr_result = ocr.raw().ocr(img, rect=rects[0])
        return ocr_result.squash().text
