"""
选卡对话框中的技能卡匹配。

底层工具：给一张裁剪后的卡片图像，返回匹配的 SkillCard。
定位职责由 CardSelectContext.fetch_cards() 负责。
"""
import logging
from typing import Callable

from cv2.typing import MatLike

from kaa.db.constants import CharacterId
from kaa.db.skill_card import SkillCard
from kaa.image_db import ImageDatabase, FileDataSource
from kaa.image_db.descriptors.sift import SiftDescriptor
from kaa.util import paths

logger = logging.getLogger(__name__)

_db: ImageDatabase | None = None


def build_db(progress_cb: Callable[[int, int], None] | None = None):
    global _db
    path = paths.resource('skill_cards')
    db_dir = paths.cache('skill_cards_dialog')
    _db = ImageDatabase(FileDataSource(str(path)), db_dir, SiftDescriptor(nfeatures=100), name='skill_cards_dialog')
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


def match_card_region(crop: MatLike) -> SkillCard | None:
    """对裁剪出的卡片图像进行图像匹配，返回对应的 SkillCard。"""
    db = dialog_cards_db()
    results = db.query(crop, k=1, threshold=8000)
    if not results:
        return None
    match = results[0]
    asset_id = match.key.removesuffix('.png')
    for cid in CharacterId:
        suffix = '-' + cid.value
        if asset_id.endswith(suffix):
            asset_id = asset_id[:-len(suffix)]
            break
    return SkillCard.from_asset_id(asset_id)
