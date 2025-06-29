import cv2
import numpy as np
from typing import Optional
from cv2.typing import MatLike

from kotonebot import action, image, device
from kotonebot.backend.core import Image
from kotonebot.backend.image import TemplateMatchResult


def primary_button_state(img: MatLike) -> Optional[bool]:
    """
    分析按钮图像并根据红色通道直方图返回按钮状态

    :param img: 输入的按钮图像 (BGR格式)
    :return: True - 启用状态
             False - 禁用状态
             None - 未知状态或输入无效
    """
    # 确保图像有效
    if img is None or img.size == 0:
        return None

    # 计算红色通道直方图（五箱）
    _, _, r = cv2.split(img)
    hist = cv2.calcHist([r], [0], None, [5], [0, 256])
    # 归一化并找出红色集中在哪一箱
    hist = hist.ravel() / hist.sum()
    max_idx = np.argmax(hist)

    if max_idx == 3:
        return False
    elif max_idx == 4:
        return True
    else:
        return None

@action('寻找按钮', screenshot_mode='manual-inherit')
def find_button(template: MatLike | Image, state: Optional[bool] = None) -> Optional[bool]:
    """
    在图像中寻找按钮并返回其状态

    :param template: 按钮模板图像 (BGR格式)
    :param state: 按钮状态 (True - 启用, False - 禁用, None - 任意)
    :return: True - 启用状态
             False - 禁用状态
             None - 未找到按钮或状态未知
    """
    img = device.screenshot()
    result = image.find(template)
    if result is None:
        return None
    x, y, w, h = result.rect.xywh
    button_img = img[y:y+h, x:x+w]
    return primary_button_state(button_img)
