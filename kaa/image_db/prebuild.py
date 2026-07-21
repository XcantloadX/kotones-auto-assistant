import logging
import os
import shutil
from typing import Callable

from kaa.game_ui.idols_overview import build_db as _build_idols_db
from kaa.game_ui.drinks_overview import build_db as _build_drinks_db
from kaa.game_ui.skill_card_select import build_db as _build_dialog_cards_db
from kaa.tasks.produce.new.play_cards.ui import build_db as _build_skill_cards_db
from kaa.util import paths as kaa_paths

logger = logging.getLogger(__name__)

_BUILDERS = [
    ("idols",              "idols",              _build_idols_db),
    ("drinks",             "drinks",             _build_drinks_db),
    ("skill_cards",        "skill_cards",        _build_skill_cards_db),
    ("skill_cards_dialog", "skill_cards_dialog", _build_dialog_cards_db),
]


def ensure_all_image_dbs_built(
    status_cb: Callable[[str], None] | None = None,
    *,
    force: bool = False,
) -> bool:
    total = len(_BUILDERS)
    ok = 0
    for i, (name, cache_key, build_fn) in enumerate(_BUILDERS, 1):
        msg = f"构建图像数据索引 ({i}/{total}): {name}"
        logger.info(msg)
        if status_cb:
            status_cb(msg)

        cache_path = kaa_paths.cache(cache_key)
        if force and os.path.isdir(cache_path):
            shutil.rmtree(cache_path)

        def _status_cb(cur: int, tot: int) -> None:
            if status_cb:
                status_cb(f"构建图像数据索引（{i}/{total}）：{name}（{cur}/{tot}）")

        try:
            build_fn(progress_cb=_status_cb)
            ok += 1
            logger.info("Done: %s", name)
        except BaseException:
            logger.exception("Failed to build image db: %s", name)

    if status_cb:
        status_cb(f"图像数据索引构建完成 ({ok}/{total})")
    logger.info("Image db rebuild done: %d/%d", ok, total)
    return ok == total
