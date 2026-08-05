"""图像数据库注册中心。

所有图像数据库的构建规格（名称、资源分类、缓存 key、描述子、数据库类）
在此处集中定义，作为单一事实来源。替代原先散落在 prebuild.py 和各模块
``build_db()`` 中的硬编码。

模块级只依赖标准库，重依赖（ImageDatabase / 描述子 / CardImageDatabase）
均在调用时懒加载，避免 ``import kaa.image_db.registry`` 触发 kotonebot
等导入链。
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from kaa.image_db import ImageDatabase
    from kaa.image_db.descriptors.base import BaseDescriptor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageDbSpec:
    """描述一个图像数据库的构建规格。

    :param name: 数据库名称（全局唯一，同时是 get_db 的查找 key）
    :param resource_category: 对应的游戏数据资源分类（sprite 目录名，如 'idol_cards'）
    :param cache_key: 索引缓存目录名（位于 cache/ 下）
    :param descriptor_factory: 描述子工厂；零参可调用，返回描述子实例（懒加载）
    :param db_class: 数据库类；为 None 时使用默认的 :class:`ImageDatabase`。
        也可以传零参 callable（返回数据库类）以实现懒加载，如技能卡数据库
        （其所在模块触发 kotonebot 导入链）。
    :param version: 调用方指定的缓存版本号，写入 meta.pkl，与缓存不匹配时重建
    """

    name: str
    resource_category: str
    cache_key: str
    descriptor_factory: Callable[[], BaseDescriptor]
    db_class: type[ImageDatabase] | Callable[[], type[ImageDatabase]] | None = None
    version: int = 1


def _hist_descriptor() -> BaseDescriptor:
    """懒加载 HistDescriptor（避免模块级导入 cv2 等重依赖）。"""
    from kaa.image_db.descriptors.hist import HistDescriptor
    return HistDescriptor(8)


def _hog_descriptor() -> BaseDescriptor:
    """懒加载 HogDescriptor。"""
    from kaa.image_db.descriptors.hog import HogDescriptor
    return HogDescriptor()


def _sift_descriptor() -> BaseDescriptor:
    """懒加载 SiftDescriptor。"""
    from kaa.image_db.descriptors.sift import SiftDescriptor
    return SiftDescriptor(nfeatures=500)


def _card_image_db() -> type[ImageDatabase]:
    """懒加载 CardImageDatabase（位于 play_cards.ui，触发 kotonebot 导入链）。"""
    from kaa.tasks.produce.new.play_cards.ui import CardImageDatabase
    return CardImageDatabase


REGISTRY: tuple[ImageDbSpec, ...] = (
    ImageDbSpec(
        name='idols',
        resource_category='idol_cards',
        cache_key='idols',
        descriptor_factory=_hist_descriptor,
    ),
    ImageDbSpec(
        name='drinks',
        resource_category='drinks',
        cache_key='drinks',
        descriptor_factory=_hist_descriptor,
    ),
    ImageDbSpec(
        name='skill_cards',
        resource_category='skill_cards',
        cache_key='skill_cards',
        descriptor_factory=_hog_descriptor,
        db_class=_card_image_db,
    ),
    ImageDbSpec(
        name='skill_cards_dialog',
        resource_category='skill_cards',
        cache_key='skill_cards_dialog',
        descriptor_factory=_sift_descriptor,
    ),
)


def all_cache_keys() -> tuple[str, ...]:
    """所有图像索引缓存 key（按注册顺序）。"""
    return tuple(spec.cache_key for spec in REGISTRY)


def all_resource_categories() -> tuple[str, ...]:
    """所有游戏数据资源分类（去重保序）。"""
    return tuple(dict.fromkeys(spec.resource_category for spec in REGISTRY))


def get_spec(name: str) -> ImageDbSpec:
    """按名称查找构建规格，未找到时抛 KeyError。"""
    for spec in REGISTRY:
        if spec.name == name:
            return spec
    raise KeyError(name)


def _build_spec(
    spec: ImageDbSpec,
    source_dir: str | None = None,
    cache_dir: str | None = None,
    *,
    progress_cb: Callable[[int, int], None] | None = None,
) -> ImageDatabase:
    """按规格构建（或加载）单个图像数据库。

    重依赖在此处懒加载。

    :param spec: 构建规格
    :param source_dir: 数据源目录；为 None 时使用活跃游戏数据目录
    :param cache_dir: 索引缓存目录；为 None 时使用默认缓存目录
    :param progress_cb: 进度回调 (processed, total)
    """
    from kaa.image_db import ImageDatabase, FileDataSource
    from kaa.util import paths as kaa_paths

    db_class = spec.db_class
    if db_class is None:
        db_class = ImageDatabase
    elif not isinstance(db_class, type):
        # 懒加载工厂：返回实际数据库类
        db_class = db_class()

    descriptor = spec.descriptor_factory()
    source = FileDataSource(source_dir) if source_dir else FileDataSource(
        kaa_paths.resource(spec.resource_category)
    )
    db_dir = cache_dir if cache_dir else kaa_paths.cache(spec.cache_key)
    db = db_class(source, db_dir, descriptor, name=spec.name, version=spec.version)
    if not db.is_built:
        db.build(progress_cb=progress_cb)
    return db


# ── 内存实例缓存（线程安全懒加载） ──────────────────────────────────────────

_dbs: dict[str, ImageDatabase] = {}
_dbs_lock = threading.Lock()


def get_db(
    name: str,
    *,
    source_dir: str | None = None,
    cache_dir: str | None = None,
) -> ImageDatabase:
    """获取已构建的图像数据库实例，首次调用时自动构建。

    指定了 ``source_dir`` / ``cache_dir`` 时不走内存缓存（用于 staging 构建等
    自定义路径场景）。默认路径走双检锁懒加载缓存。

    :param name: 数据库名称（见 :data:`REGISTRY`）
    :param source_dir: 数据源目录；为 None 时使用活跃游戏数据目录
    :param cache_dir: 索引缓存目录；为 None 时使用默认缓存目录
    """
    if source_dir is not None or cache_dir is not None:
        return _build_spec(get_spec(name), source_dir, cache_dir)

    with _dbs_lock:
        if name in _dbs:
            return _dbs[name]
    # 双检锁：构建在锁外执行（耗时 IO），锁内只做读取与写入
    db = _build_spec(get_spec(name), None, None)
    with _dbs_lock:
        _dbs.setdefault(name, db)
    return _dbs[name]


def invalidate_all() -> None:
    """清空内存中的数据库实例缓存。

    游戏数据更新替换后调用，确保下一次 ``get_db`` 从新数据重新构建/加载。
    """
    with _dbs_lock:
        _dbs.clear()
