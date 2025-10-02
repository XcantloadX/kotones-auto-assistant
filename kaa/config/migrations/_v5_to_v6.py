"""v5 -> v6 迁移脚本

重构培育配置：将原有的 ProduceConfig 中的培育参数迁移到新的 ProduceSolution 结构中。
"""
from __future__ import annotations

import logging
import os
import json
import uuid
import re
from typing import Any

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """
    清理文件名中的非法字符

    :param name: 原始名称
    :return: 清理后的文件名
    """
    # 替换 \/:*?"<>| 为下划线
    return re.sub(r'[\\/:*?"<>|]', '_', name)


def _create_default_solution(old_produce_config: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """
    根据旧的培育配置创建默认的培育方案

    :param old_produce_config: 旧的培育配置
    :return: (新的培育方案数据, 方案ID)
    """
    # 生成唯一ID
    solution_id = uuid.uuid4().hex

    # 构建培育数据
    produce_data = {
        "mode": old_produce_config.get("mode", "regular"),
        "idol": old_produce_config.get("idols", [None])[0] if old_produce_config.get("idols") else None,
        "memory_set": old_produce_config.get("memory_sets", [None])[0] if old_produce_config.get("memory_sets") else None,
        "support_card_set": old_produce_config.get("support_card_sets", [None])[0] if old_produce_config.get("support_card_sets") else None,
        "auto_set_memory": old_produce_config.get("auto_set_memory", False),
        "auto_set_support_card": old_produce_config.get("auto_set_support_card", False),
        "use_pt_boost": old_produce_config.get("use_pt_boost", False),
        "use_note_boost": old_produce_config.get("use_note_boost", False),
        "follow_producer": old_produce_config.get("follow_producer", False),
        "self_study_lesson": old_produce_config.get("self_study_lesson", "dance"),
        "prefer_lesson_ap": old_produce_config.get("prefer_lesson_ap", False),
        "actions_order": old_produce_config.get("actions_order", [
            "recommended", "visual", "vocal", "dance",
            "allowance", "outing", "study", "consult", "rest"
        ]),
        "recommend_card_detection_mode": old_produce_config.get("recommend_card_detection_mode", "normal"),
        "use_ap_drink": old_produce_config.get("use_ap_drink", False),
        "skip_commu": old_produce_config.get("skip_commu", True)
    }

    # 构建方案对象
    solution = {
        "type": "produce_solution",
        "id": solution_id,
        "name": "默认方案",
        "description": "从旧配置迁移的默认培育方案",
        "data": produce_data
    }

    return solution, solution_id


def _save_solution_to_file(solution: dict[str, Any]) -> None:
    """
    将培育方案保存到文件

    :param solution: 培育方案数据
    """
    solutions_dir = "conf/produce"
    os.makedirs(solutions_dir, exist_ok=True)

    safe_name = _sanitize_filename(solution["name"])
    file_path = os.path.join(solutions_dir, f"{safe_name}.json")

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(solution, f, ensure_ascii=False, indent=4)


def migrate(user_config: dict[str, Any]) -> str | None:  # noqa: D401
    """执行 v5→v6 迁移：重构培育配置结构。

    将原有的 ProduceConfig 中的培育参数迁移到新的 ProduceSolution 结构中。
    """
    options = user_config.get("options")
    if options is None:
        logger.debug("No 'options' in user_config, skip v5→v6 migration.")
        return None

    produce_conf = options.get("produce", {})
    if not produce_conf:
        logger.debug("No 'produce' config found, skip v5→v6 migration.")
        return None

    # 检查是否已经是新格式（有 selected_solution_id 字段）
    if "selected_solution_id" in produce_conf:
        logger.debug("Produce config already in v6 format, skip migration.")
        return None

    msg = ""

    try:
        # 创建默认培育方案
        solution, solution_id = _create_default_solution(produce_conf)

        # 保存方案到文件
        _save_solution_to_file(solution)

        # 更新配置为新格式
        new_produce_conf = {
            "enabled": produce_conf.get("enabled", False),
            "selected_solution_id": solution_id,
            "produce_count": produce_conf.get("produce_count", 1)
        }

        options["produce"] = new_produce_conf
        user_config["options"] = options

        msg = f"已将培育配置迁移到新的方案系统。默认方案已创建并保存为 '{solution['name']}'。"
        logger.info("Successfully migrated produce config to v6 format with solution ID: %s", solution_id)

    except Exception as e:
        logger.error("Failed to migrate produce config: %s", e)
        msg = f"培育配置迁移失败：{e}"

    return msg or None