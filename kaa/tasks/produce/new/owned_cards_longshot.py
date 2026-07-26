"""持有技能卡对话框：长截图拼接后检框识别。

生产主路径与 ``tools/owned_cards_longshot_test.py`` 识别段一致：

  strips → stitch_strips → detect_card_rects(长图) → match

同 id 多份由几何实例天然保留，不依赖按身份去重。
检框：threshold / Canny / 面积 / 宽高比（与原先单帧版本一致）。
"""
from __future__ import annotations

from typing import Callable, TypeVar

import cv2
import numpy as np
from cv2.typing import MatLike
from kotonebot.primitives import Rect

SIZE = 80  # 技能卡 bbox 尺寸
MAX_SIZE = 200

TCard = TypeVar('TCard')


def crop_rect(img: MatLike, rect: Rect) -> np.ndarray:
    """从 ``img`` 裁切 ``rect``（返回拷贝）。"""
    return img[rect.y1:rect.y2, rect.x1:rect.x2].copy()


def estimate_scroll_dy(
    prev: MatLike,
    curr: MatLike,
    *,
    min_score: float = 0.45,
) -> tuple[float, float]:
    """用多条带 ``matchTemplate`` 估计内容滚动位移 dy。

    dy > 0 表示向下滚动（画面上特征上移）。
    返回 ``(dy, best_score)``；不可靠或无进度时 ``dy == 0``。
    """
    if prev.shape[:2] != curr.shape[:2]:
        h = min(prev.shape[0], curr.shape[0])
        w = min(prev.shape[1], curr.shape[1])
        prev = prev[:h, :w]
        curr = curr[:h, :w]
    h, w = prev.shape[:2]
    prev_g = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY) if prev.ndim == 3 else prev
    curr_g = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY) if curr.ndim == 3 else curr

    band_fracs = (0.40, 0.50, 0.60)
    band_h = max(int(h * 0.18), 40)
    search_h = int(h * 0.85)
    dys: list[float] = []
    scores: list[float] = []

    for frac in band_fracs:
        band_y = int(h * frac)
        if band_y + band_h >= h:
            continue
        band = prev_g[band_y:band_y + band_h, :]
        search = curr_g[:search_h, :]
        if search.shape[0] < band.shape[0] or search.shape[1] < band.shape[1]:
            continue
        res = cv2.matchTemplate(search, band, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        dy = float(band_y - max_loc[1])
        scores.append(float(max_val))
        if max_val >= min_score and dy >= -2:
            dys.append(max(dy, 0.0))

    if not dys:
        return 0.0, (max(scores) if scores else 0.0)

    dys_sorted = sorted(dys)
    mid = len(dys_sorted) // 2
    if len(dys_sorted) % 2:
        dy_med = dys_sorted[mid]
    else:
        dy_med = 0.5 * (dys_sorted[mid - 1] + dys_sorted[mid])
    return float(dy_med), float(max(scores))


def stitch_strips(strips: list[MatLike]) -> tuple[np.ndarray, list[dict]]:
    """将视口条带拼成一张长图。

    每条按累计滚动位移放置。重叠区用中心权重「胜者全取」（不做平均），
    以保持卡牌边框清晰，便于轮廓检框。

    返回 ``(长图, stitch_meta)``，meta 记录每条的 global_y / dy。
    """
    if not strips:
        raise ValueError('stitch_strips requires at least one strip')
    if len(strips) == 1:
        return np.ascontiguousarray(strips[0].copy()), [
            {'index': 0, 'global_y': 0.0, 'dy': 0.0, 'score': 1.0},
        ]

    offsets = [0.0]
    meta: list[dict] = [{'index': 0, 'global_y': 0.0, 'dy': 0.0, 'score': 1.0}]
    for i in range(1, len(strips)):
        dy, score = estimate_scroll_dy(strips[i - 1], strips[i])
        if dy < 1.0:
            offsets.append(offsets[-1])
        else:
            offsets.append(offsets[-1] + dy)
        meta.append({'index': i, 'global_y': offsets[-1], 'dy': dy, 'score': score})

    total_h = int(round(offsets[-1] + strips[-1].shape[0]))
    w = min(s.shape[1] for s in strips)
    canvas = np.zeros((total_h, w, 3), dtype=np.uint8)
    best_w = np.zeros((total_h, w), dtype=np.float32)

    for strip, g in zip(strips, offsets):
        g_i = int(round(g))
        strip_w = strip[:, :w]
        if strip_w.ndim == 2:
            strip_w = cv2.cvtColor(strip_w, cv2.COLOR_GRAY2BGR)
        h = strip_w.shape[0]
        ys = np.arange(h, dtype=np.float32)
        # 优先视口中心；裁切边缘权重近 0，半张卡会被完整帧覆盖
        edge_dist = np.minimum(ys, (h - 1) - ys)
        row_w = edge_dist / max(float(edge_dist.max()), 1.0)
        # 极小底数：仅边缘独有内容仍可画到空白画布
        row_w = np.maximum(row_w, 0.01)
        wts = np.broadcast_to(row_w[:, None], (h, w))

        y1 = g_i
        y2 = g_i + h
        if y2 > total_h:
            cut = y2 - total_h
            strip_w = strip_w[: h - cut]
            wts = wts[: h - cut]
            y2 = total_h
            h = strip_w.shape[0]

        region_w = best_w[y1:y2]
        take = wts > region_w
        if not np.any(take):
            continue
        canvas[y1:y2][take] = strip_w[take]
        region_w[take] = wts[take]
        best_w[y1:y2] = region_w

    return canvas, meta


def is_card_bbox(w: int, h: int) -> bool:
    """判断轮廓 bbox 是否像技能卡格子。"""
    if w * h < SIZE * SIZE:
        return False
    if w < SIZE or h < SIZE or w > MAX_SIZE or h > MAX_SIZE:
        return False
    return abs(w / h - 1) <= 0.1


def detect_card_rects(img: MatLike) -> list[Rect]:
    """检测技能卡格子（threshold / Canny / 面积 / 宽高比）。"""
    binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY)[1]
    edges = cv2.Canny(binary, 100, 200)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rects: list[Rect] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if not is_card_bbox(w, h):
            continue
        rects.append(Rect(x, y, w, h))
    rects.sort(key=lambda r: (r.y1, r.x1))
    return rects


def recognize_cards_on_image(
    img: MatLike,
    match_fn: Callable[[MatLike], TCard | None],
    *,
    on_fail: Callable[[Rect], None] | None = None,
) -> list[TCard]:
    """在 ``img`` 上检框，并对每个裁切调用 ``match_fn``。

    匹配失败则跳过；若提供 ``on_fail`` 则回调通知。
    """
    cards: list[TCard] = []
    for rect in detect_card_rects(img):
        crop = img[rect.y1:rect.y2, rect.x1:rect.x2]
        card = match_fn(crop)
        if card is None:
            if on_fail is not None:
                on_fail(rect)
            continue
        cards.append(card)
    return cards


def recognize_owned_from_strips(
    strips: list[MatLike],
    match_fn: Callable[[MatLike], TCard | None],
    *,
    on_fail: Callable[[Rect], None] | None = None,
) -> tuple[list[TCard], np.ndarray, list[dict], list[Rect]]:
    """生产主路径：与测试工具 ``run_once`` 识别段严格一致。

    ``strips → stitch_strips → detect_card_rects(长图) → match_fn``

    返回 ``(cards, long_img, stitch_meta, rects)``。
    ``cards`` 仅含匹配成功的实例；``rects`` 为全部检出框（含未匹配）。
    """
    if not strips:
        raise ValueError('recognize_owned_from_strips requires at least one strip')

    long_img, meta = stitch_strips(strips)
    rects = detect_card_rects(long_img)
    cards: list[TCard] = []
    for rect in rects:
        crop = long_img[rect.y1:rect.y2, rect.x1:rect.x2]
        card = match_fn(crop)
        if card is None:
            if on_fail is not None:
                on_fail(rect)
            continue
        cards.append(card)
    return cards, long_img, meta, rects
