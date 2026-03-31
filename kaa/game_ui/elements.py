from dataclasses import dataclass, replace
from typing import Optional
from typing_extensions import override

import cv2
import numpy as np
from cv2.typing import MatLike
from kotonebot.backend.context.context import vars
from kotonebot.core import BoundPrefab, GameObject, TemplateMatchPrefab, TemplateMatchQuery

def primary_button_state(img: MatLike | None) -> Optional[bool]:
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

def secondary_button_state(img: MatLike | None) -> Optional[bool]:
    raise NotImplementedError

class GakumasPrimaryButtonObject(GameObject):
    @property
    def enabled(self) -> bool | None:
        img = vars.screenshot_data
        if img is None:
            return None
        return primary_button_state(img[self.rect.y1:self.rect.y2, self.rect.x1:self.rect.x2])

    @property
    def disabled(self) -> bool | None:
        _enabled = self.enabled
        if _enabled is None:
            return _enabled
        else:
            return not _enabled


@dataclass(frozen=True, slots=True)
class GakumasPrimaryButtonQuery(TemplateMatchQuery[GakumasPrimaryButtonObject]):
    enabled: bool | None = None


class GakumasPrimaryButtonPrefab(TemplateMatchPrefab[GakumasPrimaryButtonObject]):
    """Primary 按钮（橙色按钮）"""
    Query = GakumasPrimaryButtonQuery

    class _Editor(TemplateMatchPrefab._Editor):
        icon = "widget-button"
        name = "主按钮"
        description = "游戏界面中的主按钮，通常为橙色，用于确认操作等。"

    @classmethod
    def _normalize_query(cls, query: GakumasPrimaryButtonQuery) -> GakumasPrimaryButtonQuery:
        if query.enabled is None:
            return query

        predicate = query.predicate

        def enabled_predicate(obj: GakumasPrimaryButtonObject) -> bool:
            if obj.enabled != query.enabled:
                return False
            return predicate(obj) if predicate is not None else True

        return replace(query, predicate=enabled_predicate)

    @override
    @classmethod
    def q(
        cls,
        query: GakumasPrimaryButtonQuery | None = None,
        *,
        threshold: float | None = None,
        colored: bool | None = None,
        region=None,
        enabled: bool | None = None,
    ) -> BoundPrefab[GakumasPrimaryButtonObject, GakumasPrimaryButtonQuery]:
        if query is None:
            query = GakumasPrimaryButtonQuery(
                threshold=threshold,
                colored=colored,
                region=region,
                enabled=enabled,
            )
        return BoundPrefab(cls, cls._normalize_query(query))

class GakumasSecondaryButtonObject(GameObject):
    @property
    def enabled(self) -> bool | None:
        img = vars.screenshot_data
        if img is None:
            return None
        return primary_button_state(img[self.rect.y1:self.rect.y2, self.rect.x1:self.rect.x2])

    @property
    def disabled(self) -> bool | None:
        _enabled = self.enabled
        if _enabled is None:
            return _enabled
        else:
            return not _enabled


@dataclass(frozen=True, slots=True)
class GakumasSecondaryButtonQuery(TemplateMatchQuery[GakumasSecondaryButtonObject]):
    enabled: bool | None = None


class GakumasSecondaryButtonPrefab(TemplateMatchPrefab[GakumasSecondaryButtonObject]):
    """Secondary 按钮（白色按钮）"""
    Query = GakumasSecondaryButtonQuery

    class _Editor(TemplateMatchPrefab._Editor):
        name = "次按钮"
        description = "游戏界面中的次按钮，通常为白色，用于取消操作等。"

    @classmethod
    def _normalize_query(cls, query: GakumasSecondaryButtonQuery) -> GakumasSecondaryButtonQuery:
        if query.enabled is None:
            return query

        predicate = query.predicate

        def enabled_predicate(obj: GakumasSecondaryButtonObject) -> bool:
            if obj.enabled != query.enabled:
                return False
            return predicate(obj) if predicate is not None else True

        return replace(query, predicate=enabled_predicate)

    @override
    @classmethod
    def q(
        cls,
        query: GakumasSecondaryButtonQuery | None = None,
        *,
        threshold: float | None = None,
        colored: bool | None = None,
        region=None,
        enabled: bool | None = None,
    ) -> BoundPrefab[GakumasSecondaryButtonObject, GakumasSecondaryButtonQuery]:
        if query is None:
            query = GakumasSecondaryButtonQuery(
                threshold=threshold,
                colored=colored,
                region=region,
                enabled=enabled,
            )
        return BoundPrefab(cls, cls._normalize_query(query))

class GakumasCheckboxPrefab(TemplateMatchPrefab):
    """复选框按钮"""
    @property
    def checked(self) -> bool | None:
        pass

    class _Editor(TemplateMatchPrefab._Editor):
        icon = "form"
        name = "复选框"
        description = "游戏界面中的复选框按钮，用于多选操作等。"
