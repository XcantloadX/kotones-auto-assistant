"""v3 -> v4 迁移脚本

修正游戏包名错误。
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def migrate(user_config: dict[str, Any]) -> str | None:  # noqa: D401
    """执行 v3→v4 迁移：修正错误的游戏包名。"""
    options = user_config.get("options")
    if options is None:
        logger.debug("No 'options' in user_config, skip v3→v4 migration.")
        return None

    start_conf = options.get("start_game", {})
    old_pkg = start_conf.get("game_package_name")
    if old_pkg == "com.bandinamcoent.idolmaster_gakuen":
        start_conf["game_package_name"] = "com.bandainamcoent.idolmaster_gakuen"
        logger.info("Corrected game package name to com.bandainamcoent.idolmaster_gakuen")

    options["start_game"] = start_conf
    user_config["options"] = options

    return None 