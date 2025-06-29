import cv2
import numpy as np
from cv2.typing import MatLike

from kotonebot.primitives import Rect
from kotonebot.backend.core import Image
from kotonebot.backend.color import HsvColor
from kotonebot import action, color, image, device
from kotonebot.backend.preprocessor import HsvColorFilter


def filter_rectangles(
    img: MatLike,
    color_ranges: tuple[HsvColor, HsvColor],
    aspect_ratio_threshold: float,
    area_threshold: int,
    rect: Rect | None = None
) -> list[Rect]:
    """
    过滤出指定颜色，并执行轮廓查找，返回符合要求的轮廓的 bound box。
    返回结果按照 y 坐标排序。
    """
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    white_mask = cv2.inRange(img_hsv, np.array(color_ranges[0]), np.array(color_ranges[1]))
    contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result_rects: list[Rect] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # 如果不在指定范围内，跳过
        if rect is not None:
            rect_x1, rect_y1, rect_w, rect_h = rect.xywh
            rect_x2 = rect_x1 + rect_w
            rect_y2 = rect_y1 + rect_h
            if not (
                x >= rect_x1 and
                y >= rect_y1 and
                x + w <= rect_x2 and
                y + h <= rect_y2
            ):
                continue
        aspect_ratio = w / h
        area = cv2.contourArea(contour)
        if aspect_ratio >= aspect_ratio_threshold and area >= area_threshold:
            result_rects.append(Rect(x, y, w, h))
    result_rects.sort(key=lambda x: x.y1)
    return result_rects

@action('按钮是否禁用', screenshot_mode='manual-inherit')
def button_state(*, target: Image | None = None, rect: Rect | None = None) -> bool | None:
    """
    判断按钮是否处于禁用状态。

    :param rect: 按钮的矩形区域。必须包括文字或图标部分。
    :param target: 按钮目标模板。
    """
    img = device.screenshot()
    if rect is not None:
        _rect = rect
    elif target is not None:
        result = image.find(target)
        if result is None:
            return None
        _rect = result.rect
    else:
        raise ValueError('Either rect or target must be provided.')
    if color.find('#babcbd', rect=_rect):
        return False
    elif color.find('#ffffff', rect=_rect):
        return True
    else:
        raise ValueError(f'Unknown button state: {img}')


WHITE_LOW = (0, 0, 200)
WHITE_HIGH = (180, 30, 255)


class WhiteFilter(HsvColorFilter):
    """
    匹配时，只匹配图像和模板中的白色部分。

    此类用于识别空心/透明背景的白色图标或文字。
    """

    def __init__(self):
        super().__init__(WHITE_LOW, WHITE_HIGH)


if __name__ == '__main__':
    pass