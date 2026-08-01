import logging
import shutil
from pathlib import Path
from typing import Callable

from kaa.game_ui.idols_overview import build_db as _build_idols_db
from kaa.game_ui.drinks_overview import build_db as _build_drinks_db
from kaa.game_ui.skill_card_select import build_db as _build_dialog_cards_db
from kaa.tasks.produce.new.play_cards.ui import build_db as _build_skill_cards_db
from kaa.util import paths as kaa_paths

logger = logging.getLogger(__name__)

_BUILDERS = [
    # (name, resource_category, cache_key, build_fn)
    ("idols",              "idol_cards",  "idols",              _build_idols_db),
    ("drinks",             "drinks",       "drinks",             _build_drinks_db),
    ("skill_cards",        "skill_cards",  "skill_cards",        _build_skill_cards_db),
    ("skill_cards_dialog", "skill_cards",  "skill_cards_dialog", _build_dialog_cards_db),
]


def ensure_all_image_dbs_built(
    status_cb: Callable[[str], None] | None = None,
    *,
    force: bool = False,
    source_base: Path | None = None,
    cache_base: Path | None = None,
    progress_cb: Callable[[int, int, str, int, int], None] | None = None,
) -> bool:
    """确保所有图像数据库索引已构建。

    :param status_cb: 状态文本回调
    :param force: 为 True 时删除已有缓存目录后重建
    :param source_base: 数据源基目录；为 None 时使用活跃游戏数据目录
    :param cache_base: 索引缓存基目录；为 None 时使用默认缓存目录
    :param progress_cb: 结构化进度回调 (builder_index, builder_total, name, file_cur, file_total)；
        每个 builder 完成时会额外回调 (i, total, name, 1, 1) 表示该 builder 进度 100%
    """
    total = len(_BUILDERS)
    ok = 0
    for i, (name, res_cat, cache_key, build_fn) in enumerate(_BUILDERS, 1):
        msg = f"构建图像数据索引 ({i}/{total}): {name}"
        logger.info(msg)
        if status_cb:
            status_cb(msg)

        source_dir = str(source_base / res_cat) if source_base else None
        cache_dir = str(cache_base / cache_key) if cache_base else None
        target_cache = Path(cache_dir) if cache_dir else Path(kaa_paths.cache(cache_key))
        if force and target_cache.exists():
            shutil.rmtree(target_cache)

        def _status_cb(cur: int, tot: int) -> None:
            if status_cb:
                status_cb(f"构建图像数据索引（{i}/{total}）：{name}（{cur}/{tot}）")
            if progress_cb:
                progress_cb(i, total, name, cur, tot)

        try:
            build_fn(progress_cb=_status_cb, source_dir=source_dir, cache_dir=cache_dir)
            ok += 1
            # 该 builder 结束（即使无文件进度）也回调一次 100%，保证整体进度单调前进
            if progress_cb:
                progress_cb(i, total, name, 1, 1)
            logger.info("Done: %s", name)
        except BaseException:
            logger.exception("Failed to build image db: %s", name)

    if status_cb:
        status_cb(f"图像数据索引构建完成 ({ok}/{total})")
    logger.info("Image db rebuild done: %d/%d", ok, total)
    return ok == total


def build_image_dbs_from_staging(
    staging_dir: Path,
    staging_cache_dir: Path,
    status_cb: Callable[[str], None] | None = None,
    progress_cb: Callable[[int, int, str, int, int], None] | None = None,
) -> bool:
    """从 staging 目录构建图像索引到 staging cache 目录。

    :param staging_dir: staging 游戏数据目录（含各 sprite category 子目录）
    :param staging_cache_dir: staging 图像索引缓存目录
    :param status_cb: 状态文本回调
    :param progress_cb: 结构化进度回调，透传给 ensure_all_image_dbs_built
    """
    return ensure_all_image_dbs_built(
        status_cb=status_cb,
        force=True,
        source_base=staging_dir,
        cache_base=staging_cache_dir,
        progress_cb=progress_cb,
    )
