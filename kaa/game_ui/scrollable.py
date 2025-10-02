import logging
import time
from typing import Literal

import cv2
import numpy as np
from cv2.typing import MatLike

from kotonebot import device, action
from kotonebot.primitives import Rect
from kotonebot.backend.core import HintBox
from kotonebot.primitives.geometry import RectTuple

logger = logging.getLogger(__name__)

# 暗色系滚动条阈值。bitwise_not = True
# 例：金币商店、金币扭蛋页面
THRESHOLD_DARK_FULL = 240 # 滚动条+滚动条背景
THRESHOLD_DARK_FOREGROUND = 190 # 仅滚动条

# 亮色系滚动条阈值。bitwise_not = False
# 例：每日任务、音乐播放器选歌页面
THRESHOLD_LIGHT_FULL = 140 # 滚动条+滚动条背景（效果不佳）
THRESHOLD_LIGHT_FOREGROUND = 220 # 仅滚动条

def find_scroll_bar(img: MatLike, threshold: int, bitwise_not: bool = False) -> Rect | None:
    """
    寻找给定图像中的滚动条。
    基于二值化+轮廓查找实现。

    :param img: 输入图像。图像必须中存在滚动条，否则无法保证结果是什么。
    :param threshold: 二值化阈值。
    :param bitwise_not: 是否对二值化结果取反。
    :return: 滚动条的矩形区域 `(x, y, w, h)`，如果未找到则返回 None。
    """
    # 灰度、二值化、查找轮廓
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    if bitwise_not:
        binary = cv2.bitwise_not(binary)
    # cv2.imshow('binary', binary)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 找出所有可能是滚动条的轮廓：
    # 宽高比 < 0.5，且形似矩形
    filtered_contours = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        contour_area = cv2.contourArea(contour)
        rect_area = w * h
        if w/h < 0.5 and contour_area / rect_area > 0.6:
            filtered_contours.append((contour, (x, y, w, h)))
    
    # 找出最长的轮廓
    if filtered_contours:
        longest_contour = max(filtered_contours, key=lambda c: c[1][3])
        return longest_contour[1]
    return None

def find_scroll_bar2(img: MatLike) -> Rect | None:
    """
    寻找给定图像中的滚动条。
    基于边缘检测+轮廓查找实现。

    :param img: 输入图像。图像必须中存在滚动条，否则无法保证结果是什么。
    :return: 滚动条的矩形区域 `(x, y, w, h)`，如果未找到则返回 None。
    """
    # 高斯模糊、边缘检测
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 70)
    # cv2.imshow('edges', cv2.resize(edges, (0, 0), fx=0.5, fy=0.5))
    # 膨胀
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=1)
    # cv2.imshow('dilated', cv2.resize(dilated, (0, 0), fx=0.5, fy=0.5))
    # 轮廓检测
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 找出最可能是滚动条的轮廓：
    # 宽高比 < 0.5，且形似矩形，且最长
    rects: list[RectTuple] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        contour_area = cv2.contourArea(contour)
        rect_area = w * h
        if w/h < 0.5 and contour_area / rect_area > 0.6:
            rects.append((x, y, w, h))
    if rects:
        longest_rect = max(rects, key=lambda r: r[2] * r[3])
        return Rect(xywh=longest_rect)
    return None

class ScrollableIterator:
    def __init__(
            self,
            scrollable: 'Scrollable',
            delta_pixels: int,
            start: float | None,
            end: float,
            skip_first: bool
        ):
        self.scrollable = scrollable
        self.delta_pixels = delta_pixels
        self.start = start
        self.end = end
        self.skip_first = skip_first

    def __iter__(self):
        if self.start is not None:
            self.scrollable.to(self.start)
        return self
    
    def __next__(self):
        if self.skip_first:
            self.skip_first = False
            return self.scrollable.position
        if self.scrollable.position >= self.end:
            raise StopIteration
        self.scrollable.by(pixels=self.delta_pixels)
        return self.scrollable.position

class Scrollable:
    """
    此类用于处理游戏内的可滚动容器。

    例：
    ```python
    sc = Scrollable()
    sc.to(0) # 滚动到最开始
    sc.to(0.5) # 滚动到中间
    sc.to(1) # 滚动到最后

    sc.by(0.1) # 滚动10%
    sc.by(pixels=100) # 滚动100px

    sc.page_count # 滚动页数
    sc.position # 当前滚动位置

    # 以步长 10% 开始滚动，直到滚动到最后
    for _ in sc(0.1):
        print(sc.position)
    ```
    """
    def __init__(
        self,
        scrollbar_rect: HintBox | None = None,
        color_schema: Literal['light', 'dark'] = 'light',
        *,
        at_start_threshold: float = 0.01,
        at_end_threshold: float = 0.99,
        auto_update: bool = True
    ):
        """
        :param auto_update: 在每次滑动后是否自动更新滚动数据。
        """
        self.color_schema = color_schema
        self.scrollbar_rect = scrollbar_rect
        self.position: float = 0
        """当前滚动位置。范围 [0, 1]"""
        self.thumb_height: int | None = None
        """滚动条把手高度"""
        self.thumb_position: tuple[int, int] | None = None
        """滚动条把手位置"""
        self.track_position: tuple[int, int] | None = None
        """滚动轨道位置"""
        self.track_height: int | None = None
        """滚动轨道高度"""
        self.page_count: int | None = None
        """滚动页数"""
        self.auto_update = auto_update
        """是否自动更新滚动数据"""
        self.at_start_threshold = at_start_threshold
        self.at_end_threshold = at_end_threshold

        if color_schema == 'dark':
            raise NotImplementedError('Dark color schema is not implemented yet.')

    @action('滚动.更新数据', screenshot_mode='manual-inherit')
    def update(self) -> bool:
        """
        立即更新滚动数据。

        :return: 是否更新成功。
        """
        img = device.screenshot()
        if self.scrollbar_rect is None:
            logger.debug('Finding scrollbar rect...')
            self.scrollbar_rect = find_scroll_bar2(img)
        if self.scrollbar_rect is None:
            logger.warning('Unable to find scrollbar. (1)')
            return False

        x, y, w, h = self.scrollbar_rect.xywh
        logger.debug(f'Scrollbar rect found. x/y/w/h: {x}/{y}/{w}/{h}')

        scroll_img = img[y:y+h, x:x+w]
        # 灰度、二值化
        gray = cv2.cvtColor(scroll_img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        # 0 = 滚动条，255 = 背景

        # 计算滚动位置
        positions = np.where(binary == 0)[0]
        if len(positions) > 0:
            self.track_position = (int(x + w / 2), int(y))
            self.track_height = int(h)
            self.thumb_height = int(positions[-1] - positions[0])
            self.thumb_position = (int(x + w / 2), int(y + positions[0]))
            self.position = float(positions[-1] / h)
            self.page_count = int(h / self.thumb_height)
            logger.debug(f'Scrollbar height: {self.thumb_height}, position: {self.position}')
            if self.position < self.at_start_threshold:
                self.position = 0
            elif self.position > self.at_end_threshold:
                self.position = 1
            return True
        else:
            logger.warning('Unable to find scrollbar. (2)')
            return False

    @action('滚动.下一页', screenshot_mode='manual-inherit')
    def next(self, *, page: float) -> bool:
        """
        滚动到下一页。

        :param page: 滚动页数。
        :return: 是否滚动成功。
        """
        logger.debug('Scrolling to next page.')
        if not self.thumb_height:
            self.update()
        if not self.thumb_height or not self.thumb_position:
            logger.warning('Unable to update scrollbar data.')
            return False
        if self.position >= 1:
            logger.debug('Already at the end of the scrollbar.')
            return False

        delta = int(self.thumb_height * page)
        self.by(pixels=delta)
        return True

    @action('滚动.滚动', screenshot_mode='manual-inherit')
    def by(self, percentage: float | None = None, *, pixels: int | None = None) -> bool:
        """
        滚动指定距离。
        
        :param percentage: 滚动距离，范围 [-1, 1]。
        :param pixels: 滚动距离，单位为像素。此参数优先级高于 percentage。
        :return: 是否滚动成功。
        """
        if percentage is not None and (percentage > 1 or percentage < -1):
            raise ValueError('percentage must be in range [-1, 1].')
        if pixels is not None and pixels < 0:
            raise ValueError('pixels must be positive.')
        if not self.thumb_height or not self.thumb_position or not self.track_height:
            self.update()
        if not self.thumb_height or not self.thumb_position or not self.track_height:
            logger.warning('Unable to update scrollbar data.')
            return False

        x, src_y = self.thumb_position
        src_y += self.thumb_height // 2
        if pixels is not None:
            dst_y = src_y + pixels
            logger.debug(f'Scrolling by {pixels} px...')
        elif percentage is not None:
            logger.debug(f'Scrolling by {percentage}...')
            dst_y = src_y + int(self.track_height * percentage)
        else:
            raise ValueError('Either percentage or pixels must be provided.')
        device.swipe(x, src_y, x, dst_y, 0.3)
        time.sleep(0.2)
        if self.auto_update:
            self.update()
        return True
    
    @action('滚动.滚动到', screenshot_mode='manual-inherit')
    def to(self, position: float) -> bool:
        """
        滚动到指定位置。

        :param position: 目标位置，范围 [0, 1]。
        :return: 是否滚动成功。
        """
        if position > 1 or position < 0:
            raise ValueError('position must be in range [0, 1].')
        logger.debug(f'Scrolling to {position}...')
        if not self.thumb_height or not self.thumb_position or not self.track_height or not self.track_position:
            self.update()
        if not self.thumb_height or not self.thumb_position or not self.track_height or not self.track_position:
            logger.warning('Unable to update scrollbar data.')
            return False

        x, y = self.track_position
        tx, ty = self.thumb_position
        ty += self.thumb_height // 2
        target_y = y + int(self.track_height * position)
        device.swipe(tx, ty, x, target_y, 0.3)
        time.sleep(0.2)
        if self.auto_update:
            self.update()
        return True
    
    def __call__(self,
            step: float,
            *,
            start: float | None = 0,
            end: float = 1,
            skip_first: bool = True
        ) -> ScrollableIterator:
        """
        以指定步长滚动。

        :param step: 步长，范围 [-1, 1]。
        :param start: 起始位置，范围 [0, 1]。默认为 None。
            若为 None，表示使用当前位置。
        :param end: 结束位置，范围 [0, 1]。默认为 1。
        :param skip_first: 是否跳过第一次滚动。默认为 True。
            若为 True，第一次滚动在第一次循环后执行。
            若为 False，第一次滚动在第一次循环前执行。
        :return: 一个迭代器，迭代时滚动指定步长。
        """
        if not self.track_height:
            self.update()
        if not self.track_height:
            raise ValueError('Unable to update scrollbar data.')
        return ScrollableIterator(self, int(self.track_height * step), start, end, skip_first)

if __name__ == '__main__':
    import cv2
    import time
    logger.setLevel(logging.DEBUG)

    device.screenshot()
    sc = Scrollable(color_schema='light')
    sc.update()
    sc.to(0)
    print(sc.page_count)
    pg = sc.page_count
    assert pg is not None
    for _ in sc(4 / (pg * 12) * 0.8):
        print(sc.position)

    cv2.waitKey(0)
    cv2.destroyAllWindows()

