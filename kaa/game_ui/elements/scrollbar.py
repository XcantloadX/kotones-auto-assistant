import logging
import time
from dataclasses import dataclass, replace
from typing import overload
from kotonebot.primitives import Rect
from typing_extensions import override

import cv2
import numpy as np
from cv2.typing import MatLike

from kotonebot import device, action
from kotonebot.core import BoundPrefab, FindQuery, GameObject, Prefab
from kotonebot.devtools import EditorMetadata
from kotonebot.backend.context.context import vars
from kotonebot.devtools.project.schema import RectProp

logger = logging.getLogger(__name__)


def analyze_scrollbar_track(track_img: MatLike) -> dict | None:
    """
    分析滚动条轨道切图，提取把手位置、高度等信息。

    检测逻辑基于把手像素灰度值（约 140–142）做水平投影，
    取最长连续白色区域作为 thumb 本身的位置与高度。
    track 高度始终取输入图像（即 Prefab.rect）的高度。

    :param track_img: 滚动条轨道区域的 BGR 图像
    :return: 包含 thumb_start, thumb_end, thumb_height, track_height, position, page_count 的字典，
             若无法识别则返回 None
    """
    if track_img is None or track_img.size == 0:
        return None

    gray = cv2.cvtColor(track_img, cv2.COLOR_BGR2GRAY)
    # 把手像素灰度约 140–142
    binary = cv2.inRange(gray, 140, 142)

    # 水平投影：每行平均值，再阈值化得到把手所在行
    bar = cv2.reduce(binary, dim=1, rtype=cv2.REDUCE_AVG, dtype=cv2.CV_8U)
    bar = cv2.inRange(bar, 100, 255)

    # 搜索最长的连续白色区域作为 thumb
    contours, _ = cv2.findContours(bar, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    longest_c = max(contours, key=lambda c: cv2.boundingRect(c)[3])
    _, y, _, h = cv2.boundingRect(longest_c)
    if h <= 0:
        return None

    thumb_start = int(y)
    thumb_height = int(h)
    thumb_end = thumb_start + thumb_height
    # track 高度视为 Prefab.rect 的高度（即输入切图高度）
    track_height = int(track_img.shape[0])
    position = float(thumb_end / track_height)
    page_count = max(1, int(track_height / thumb_height))

    return {
        'thumb_start': thumb_start,
        'thumb_end': thumb_end,
        'thumb_height': thumb_height,
        'track_height': track_height,
        'position': position,
        'page_count': page_count,
    }


class GakumasScrollbarObject(GameObject):
    """游戏界面中的滚动条对象。"""

    def _get_analysis(self) -> dict | None:
        """基于当前 vars.screenshot_data 分析滚动条（不主动截图）。"""
        try:
            return self._cached_analysis
        except AttributeError:
            img = vars.screenshot_data
            if img is None or self.rect is None:
                return None
            track = img[self.rect.y1:self.rect.y2, self.rect.x1:self.rect.x2]
            result = analyze_scrollbar_track(track)
            self._cached_analysis = result
            return result

    def _refresh_analysis(self) -> dict | None:
        """截取最新画面并重新分析。"""
        self._clear_cache()
        device.screenshot()
        return self._get_analysis()

    @property
    def position(self) -> float | None:
        """当前滚动位置，范围 [0, 1]。"""
        data = self._get_analysis()
        return data['position'] if data else None

    @property
    def page_count(self) -> int | None:
        """滚动页数。"""
        data = self._get_analysis()
        return data['page_count'] if data else None

    @property
    def thumb_height(self) -> int | None:
        """滚动条把手高度。"""
        data = self._get_analysis()
        return data['thumb_height'] if data else None

    @property
    def track_height(self) -> int | None:
        """滚动条轨道高度。"""
        data = self._get_analysis()
        return data['track_height'] if data else None

    @property
    def at_start(self) -> bool:
        """是否在顶部。"""
        pos = self.position
        return pos is not None and pos < 0.01

    @property
    def at_end(self) -> bool:
        """是否在底部。"""
        pos = self.position
        return pos is not None and pos > 0.99

    @action('滚动条.更新数据', screenshot_mode='manual-inherit')
    def update(self) -> bool:
        """立即截图并更新滚动数据。"""
        return self._refresh_analysis() is not None

    @action('滚动条.滚动到', screenshot_mode='manual-inherit')
    def to(self, position: float) -> bool:
        """滚动到指定位置。

        :param position: 目标位置，范围 [0, 1]。
        """
        if position < 0 or position > 1:
            raise ValueError('position must be in range [0, 1].')
        data = self._refresh_analysis()
        if data is None:
            logger.warning('Failed to analyze scrollbar.')
            return False

        x = self.rect.center_x
        src_y = self.rect.y1 + data['thumb_start'] + data['thumb_height'] // 2
        target_y = self.rect.y1 + int(data['track_height'] * position)

        device.swipe(x, src_y, x, target_y, 0.3)
        time.sleep(0.2)
        self._clear_cache()
        return True

    @action('滚动条.滚动', screenshot_mode='manual-inherit')
    def by(self, percentage: float | None = None, *, pixels: int | None = None) -> bool:
        """滚动指定距离。

        :param percentage: 滚动百分比，范围 [-1, 1]。
            此参数与 pixels 二选一。
        :param pixels: 滚动像素值。
        """
        if percentage is not None and (percentage < -1 or percentage > 1):
            raise ValueError('percentage must be in range [-1, 1].')
        if pixels is not None and pixels < 0:
            raise ValueError('pixels must be positive.')
        if percentage is None and pixels is None:
            raise ValueError('Either percentage or pixels must be provided.')

        data = self._refresh_analysis()
        if data is None:
            logger.warning('Failed to analyze scrollbar.')
            return False

        x = self.rect.center_x
        src_y = self.rect.y1 + data['thumb_start'] + data['thumb_height'] // 2

        if pixels is not None:
            dst_y = src_y + pixels
        else:
            dst_y = src_y + int(data['track_height'] * percentage)

        device.swipe(x, src_y, x, dst_y, 0.3)
        time.sleep(0.2)
        self._clear_cache()
        return True

    @action('滚动条.下一页', screenshot_mode='manual-inherit')
    def next(self, *, page: float = 1.0) -> bool:
        """滚动到下一页。

        :param page: 滚动的页数。
        """
        data = self._refresh_analysis()
        if data is None:
            logger.warning('Failed to analyze scrollbar.')
            return False

        if data['position'] >= 1.0:
            logger.debug('Already at the end of the scrollbar.')
            return False

        delta = int(data['thumb_height'] * page)
        # by() 会再次截图；此处直接滑动，避免重复截图
        x = self.rect.center_x
        src_y = self.rect.y1 + data['thumb_start'] + data['thumb_height'] // 2
        device.swipe(x, src_y, x, src_y + delta, 0.3)
        time.sleep(0.2)
        self._clear_cache()
        return True

    def _clear_cache(self):
        try:
            del self._cached_analysis
        except AttributeError:
            pass

    def __call__(
        self,
        step: float,
        *,
        start: float | None = 0,
        end: float = 1,
        skip_first: bool = True,
    ) -> 'GakumasScrollbarIterator':
        """以指定步长迭代滚动。

        :param step: 步长百分比，范围 (0, 1]。
        :param start: 起始位置，范围 [0, 1]。为 None 时不移动。
        :param end: 结束位置，范围 [0, 1]。
        :param skip_first: 是否跳过第一次滚动前的读取。为 True 时先在当前位置读取一次。
        """
        return GakumasScrollbarIterator(self, step, start, end, skip_first)


@dataclass(frozen=True, slots=True)
class GakumasScrollbarQuery(FindQuery[GakumasScrollbarObject]):
    """滚动条查询参数。"""
    position: float | None = None
    """滚动位置 [0, 1]。"""
    at_start: bool | None = None
    """是否在顶部。"""
    at_end: bool | None = None
    """是否在底部。"""


class GakumasScrollbarPrefab(Prefab[GakumasScrollbarObject]):
    """滚动条

    Prefab 总是视为存在：``rect`` 即滚动条轨道区域。
    运行时在 ``rect`` 内检测 thumb 的位置与高度；track 高度取 ``rect`` 高度。
    """
    Query = GakumasScrollbarQuery

    rect: Rect

    class _Editor(EditorMetadata):
        shortcut = None
        name = '滚动条'
        description = '游戏界面中的滚动条。'
        icon = 'scrollbar'
        primary_prop = 'rect'
        props = {
            'rect': RectProp(label='滚动条区域', description='滚动条轨道在屏幕上的区域。必须足够精确紧贴，否则可能识别不到或错误识别。', default_value=None),
        }

    @classmethod
    def _normalize_query(cls, query: GakumasScrollbarQuery) -> GakumasScrollbarQuery:
        if query.position is None and query.at_start is None and query.at_end is None:
            return query

        predicate = query.predicate

        def combined_predicate(obj: GakumasScrollbarObject) -> bool:
            if query.position is not None and obj.position != query.position:
                return False
            if query.at_start is not None and obj.at_start != query.at_start:
                return False
            if query.at_end is not None and obj.at_end != query.at_end:
                return False
            return predicate(obj) if predicate is not None else True

        return replace(query, predicate=combined_predicate)

    @override
    @classmethod
    def _find_impl(cls, query: GakumasScrollbarQuery) -> GakumasScrollbarObject | None:
        # Prefab 总是视为存在，直接使用定义的轨道 rect
        obj = GakumasScrollbarObject()
        obj.rect = cls.rect
        obj.prefab = cls
        if query.predicate is not None and not query.predicate(obj):
            return None
        return obj

    @override
    @classmethod
    def _find_all_impl(cls, query: GakumasScrollbarQuery) -> list[GakumasScrollbarObject]:
        obj = cls._find_impl(query)
        return [obj] if obj is not None else []

    @overload
    @classmethod
    def q(cls, query: GakumasScrollbarQuery) -> BoundPrefab[GakumasScrollbarObject, GakumasScrollbarQuery]: ...
    @overload
    @classmethod
    def q(
        cls,
        *,
        position: float | None = None,
        at_start: bool | None = None,
        at_end: bool | None = None,
    ) -> BoundPrefab[GakumasScrollbarObject, GakumasScrollbarQuery]: ...
    @override
    @classmethod
    def q(
        cls,
        query: GakumasScrollbarQuery | None = None,
        *,
        position: float | None = None,
        at_start: bool | None = None,
        at_end: bool | None = None,
    ) -> BoundPrefab[GakumasScrollbarObject, GakumasScrollbarQuery]:
        if query is None:
            query = GakumasScrollbarQuery(
                position=position,
                at_start=at_start,
                at_end=at_end,
            )
        return BoundPrefab(cls, cls._normalize_query(query))


class GakumasScrollbarIterator:
    """滚动条步进迭代器。"""

    def __init__(
        self,
        scrollbar: GakumasScrollbarObject,
        step: float,
        start: float | None,
        end: float,
        skip_first: bool,
    ):
        self.scrollbar = scrollbar
        self.step = step
        self.start = start
        self.end = end
        self.skip_first = skip_first

    def __iter__(self):
        if self.start is not None:
            self.scrollbar.to(self.start)
        return self

    def __next__(self):
        if self.skip_first:
            self.skip_first = False
            return self.scrollbar.position
        pos = self.scrollbar.position
        if pos is not None and pos >= self.end:
            raise StopIteration
        self.scrollbar.by(self.step)
        return self.scrollbar.position
