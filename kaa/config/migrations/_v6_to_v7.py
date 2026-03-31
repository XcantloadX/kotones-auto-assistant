"""v6 -> v7 迁移脚本

移除已废弃的 adb_raw 截图实现，统一升级为 adb。
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def migrate(user_config: dict[str, Any]) -> str | None:  # noqa: D401
    """执行 v6→v7 迁移：

    当截图方式为 adb_raw 时，统一替换为 adb。
    """
    backend = user_config.get("backend")
    if not isinstance(backend, dict):
        logger.debug("No 'backend' config found, skip v6→v7 migration.")
        return None

    if backend.get("screenshot_impl") != "adb_raw":
        return None

    backend["screenshot_impl"] = "adb"
    user_config["backend"] = backend
    logger.info("Upgraded screenshot_impl from adb_raw to adb.")
    return "已将已废弃的 adb_raw 截图方式升级为 adb。"
