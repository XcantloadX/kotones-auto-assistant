"""
选卡对话框中的技能卡匹配。

底层工具：给一张裁剪后的卡片图像，返回匹配的 SkillCard。
定位职责由 CardSelectContext.fetch_cards() 负责。

匹配策略（B3 + min_votes 护栏）：
1. SIFT 1-NN 按 key 计票（见 ImageDatabase.query 局部描述子路径）
2. 去掉角色后缀后按 base asset 聚合票数
3. 票数优先、min_dist 作并列打破
4. 最高 base 票数 < MIN_VOTES 时拒绝匹配（防单票爆击）
"""
import logging
from typing import Callable

import cv2
import numpy as np
from cv2.typing import MatLike
from kotonebot.primitives import Rect
from kotonebot.util import cv2_imread

from kaa.db.constants import CharacterId
from kaa.db.skill_card import SkillCard
from kaa.game_data.paths import skill_card_path
from kaa.image_db import ImageDatabase, FileDataSource
from kaa.image_db.descriptors.sift import SiftDescriptor
from kaa.util import paths

logger = logging.getLogger(__name__)

_db: ImageDatabase | None = None

# 最低 base 聚合票数；低于此值视为不可靠匹配
MIN_VOTES = 3


def build_db(
    progress_cb: Callable[[int, int], None] | None = None,
    *,
    source_dir: str | None = None,
    cache_dir: str | None = None,
):
    """构建选卡对话框技能卡图像数据库索引。

    :param progress_cb: 进度回调 (processed, total)
    :param source_dir: 数据源目录；为 None 时使用活跃游戏数据目录
    :param cache_dir: 索引缓存目录；为 None 时使用默认缓存目录
    """
    global _db
    path = source_dir or paths.resource('skill_cards')
    db_dir = cache_dir or paths.cache('skill_cards_dialog')
    _db = ImageDatabase(FileDataSource(str(path)), db_dir, SiftDescriptor(nfeatures=500), name='skill_cards_dialog', version=1)
    if not _db.is_built:
        _db.build(progress_cb=progress_cb)


def dialog_cards_db() -> ImageDatabase:
    """选卡对话框专用的卡片图像数据库。"""
    global _db
    if _db is None:
        logger.info('Loading skill card dialog database...')
        build_db()
        logger.debug('Skill card dialog database loaded.')
    assert _db is not None
    return _db


def strip_character_suffix(asset_id: str) -> str:
    """去掉角色专属资源后缀（如 -ssmk / -fktn），得到 base asset_id。"""
    for cid in CharacterId:
        suffix = '-' + cid.value
        if asset_id.endswith(suffix):
            return asset_id[: -len(suffix)]
    return asset_id


def draw_debug(screenshot: MatLike, cards: list[tuple[SkillCard, Rect]]) -> MatLike:
    """生成调试图：左侧原图，右侧同尺寸白底并按 rect 绘制匹配到的技能卡。"""
    h, w = screenshot.shape[:2]
    right = np.full((h, w, 3), 255, dtype=np.uint8)

    for card, rect in cards:
        if not card._asset_id:
            continue
        path = skill_card_path(card._asset_id)
        if not path:
            logger.warning('Skill card asset not found: %s', card._asset_id)
            continue
        card_img = cv2_imread(path)
        if card_img is None:
            logger.warning('Failed to read skill card image: %s', path)
            continue

        x1, y1, x2, y2 = rect.x1, rect.y1, rect.x2, rect.y2
        x1 = max(0, min(x1, w))
        x2 = max(0, min(x2, w))
        y1 = max(0, min(y1, h))
        y2 = max(0, min(y2, h))
        rw, rh = x2 - x1, y2 - y1
        if rw <= 0 or rh <= 0:
            continue

        resized = cv2.resize(card_img, (rw, rh))
        right[y1:y2, x1:x2] = resized
        cv2.rectangle(right, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = card._asset_id or card._id
        cv2.putText(
            right,
            label,
            (x1, max(0, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )

    left = screenshot if screenshot.ndim == 3 else cv2.cvtColor(screenshot, cv2.COLOR_GRAY2BGR)
    return np.hstack([left, right])


def match_card_region(
    crop: MatLike,
    *,
    min_votes: int = MIN_VOTES,
) -> SkillCard | None:
    """对裁剪出的卡片图像进行图像匹配，返回对应的 SkillCard。

    :param crop: 卡片区域 BGR 图像
    :param min_votes: base asset 最低票数门槛，默认 :data:`MIN_VOTES`
    :return: 匹配到的 SkillCard；无可靠匹配时返回 None
    """
    db = dialog_cards_db()
    # 取全部候选；不用 min_dist 阈值（与票数排序不对齐）
    results = db.query(crop, k=len(db), threshold=None)
    if not results:
        return None

    base_votes: dict[str, int] = {}
    base_min_dist: dict[str, float] = {}
    for r in results:
        asset_id = strip_character_suffix(r.key.removesuffix('.png'))
        base_votes[asset_id] = base_votes.get(asset_id, 0) + r.votes
        if asset_id not in base_min_dist or r.distance < base_min_dist[asset_id]:
            base_min_dist[asset_id] = r.distance

    if not base_votes:
        return None

    ranked = sorted(
        base_votes.keys(),
        key=lambda b: (-base_votes[b], base_min_dist[b]),
    )
    best = ranked[0]
    best_votes = base_votes[best]
    if best_votes < min_votes:
        logger.debug(
            'Skill card match rejected: asset=%s votes=%d < min_votes=%d (min_dist=%.1f)',
            best,
            best_votes,
            min_votes,
            base_min_dist[best],
        )
        return None

    if len(ranked) >= 2:
        second = ranked[1]
        logger.debug(
            'Skill card match: %s votes=%d min_dist=%.1f (second=%s votes=%d)',
            best,
            best_votes,
            base_min_dist[best],
            second,
            base_votes[second],
        )
    else:
        logger.debug(
            'Skill card match: %s votes=%d min_dist=%.1f',
            best,
            best_votes,
            base_min_dist[best],
        )

    return SkillCard.from_asset_id(best)
