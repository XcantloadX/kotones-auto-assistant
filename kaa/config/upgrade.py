import os
import json
import logging
import shutil
from typing import Any

logger = logging.getLogger(__name__)

def upgrade_config() -> str | None:
    """检查并升级 `config.json` 到最新版本。

    若配置已是最新版本，则返回 ``None``；否则返回合并后的迁移提示信息。
    """
    # 避免循环依赖，这里再进行本地导入
    from .migrations import MIGRATION_REGISTRY, LATEST_VERSION  # pylint: disable=import-outside-toplevel

    config_path = "config.json"
    if not os.path.exists(config_path):
        logger.debug("config.json not found. Skip upgrade.")
        return None

    # 读取配置
    with open(config_path, "r", encoding="utf-8") as f:
        root: dict[str, Any] = json.load(f)

    version: int = root.get("version", 1)
    if version >= LATEST_VERSION:
        logger.info("Config already at latest version (v%s).", version)
        return None

    logger.info("Start upgrading config: current v%s → target v%s", version, LATEST_VERSION)

    messages: list[str] = []

    # 循环依次升级
    while version < LATEST_VERSION:
        migrator = MIGRATION_REGISTRY.get(version)
        if migrator is None:
            logger.warning("No migrator registered for version v%s. Abort upgrade.", version)
            break

        # 备份文件
        backup_path = f"config.v{version}.json"
        shutil.copy(config_path, backup_path)
        logger.info("Backup saved: %s", backup_path)

        # 对每个 user_config 应用迁移
        for user_cfg in root.get("user_configs", []):
            msg = migrator(user_cfg)
            if msg:
                messages.append(f"v{version} → v{version+1}:\n{msg}")

        # 更新版本号并写回
        version += 1
        root["version"] = version
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(root, f, ensure_ascii=False, indent=4)

    logger.info("Config upgrade finished. Now at v%s", version)

    return "\n---\n".join(messages) if messages else None