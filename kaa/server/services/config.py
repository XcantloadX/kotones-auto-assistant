"""
Config RPC 服务
处理配置的读取、保存和重载
"""
import logging
import json
from typing import Any
from ..rpc import registry
from ..adapters.kaa_runtime import get_runtime

logger = logging.getLogger(__name__)


@registry.decorator('config.get')
async def config_get():
    """获取当前配置"""
    runtime = get_runtime()
    
    # 读取配置文件
    with open(runtime.config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config


@registry.decorator('config.save')
async def config_save(options: dict[str, Any]):
    """保存配置"""
    runtime = get_runtime()
    
    # TODO: 添加配置验证
    # 1. 验证必需字段
    # 2. 验证配置格式
    # 3. 验证配置值的合法性
    
    # 保存配置
    with open(runtime.config_path, 'w', encoding='utf-8') as f:
        json.dump(options, f, indent=2, ensure_ascii=False)
    
    logger.info("Configuration saved")
    return {"success": True, "message": "配置已保存"}


@registry.decorator('config.reload')
async def config_reload():
    """重新加载配置"""
    runtime = get_runtime()
    
    # 重新初始化 Kaa（会重新加载配置）
    # 注意：这会中断当前运行的任务
    if runtime._is_running or runtime._is_single_task_running:
        raise RuntimeError("Cannot reload config while tasks are running")
    
    # 重新初始化
    runtime._kaa = None
    runtime.initialize()
    
    logger.info("Configuration reloaded")
    return {"success": True, "message": "配置已重新加载"}



