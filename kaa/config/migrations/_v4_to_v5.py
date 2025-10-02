"""v4 -> v5 迁移脚本

为 Windows 截图方式的配置统一设置 backend.type = 'dmm'。
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def migrate(user_config: dict[str, Any]) -> str | None:  # noqa: D401
    """执行 v4→v5 迁移：

    当截图方式为 windows / remote_windows 时，将 backend.type 统一设置为 'dmm'。
    """
    backend = user_config.get("backend", {})
    impl = backend.get("screenshot_impl")
    if impl in {"windows", "remote_windows"}:
        logger.info("Set backend type to dmm for screenshot_impl=%s", impl)
        backend["type"] = "dmm"
        user_config["backend"] = backend

    # v4→v5 无 options 结构更改，直接返回
    return None 