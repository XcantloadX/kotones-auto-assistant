"""
Produce RPC 服务
处理方案的 CRUD 操作
"""
import logging
import os
import json
from typing import Any
from datetime import datetime
from ..rpc import registry

logger = logging.getLogger(__name__)

PRODUCE_DIR = 'conf/produce'


@registry.decorator('produce.list')
async def produce_list():
    """列出所有方案"""
    if not os.path.exists(PRODUCE_DIR):
        os.makedirs(PRODUCE_DIR, exist_ok=True)
        return []
    
    configs = []
    for filename in os.listdir(PRODUCE_DIR):
        if filename.endswith('.json'):
            config_id = filename[:-5]  # 移除 .json
            config_path = os.path.join(PRODUCE_DIR, filename)
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 获取文件时间
                stat = os.stat(config_path)
                
                configs.append({
                    'id': config_id,
                    'name': data.get('name', config_id),
                    'data': data,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'updated_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception as e:
                logger.error(f"Error loading produce config {filename}: {e}")
    
    return configs


@registry.decorator('produce.read')
async def produce_read(id: str):
    """读取指定方案"""
    config_path = os.path.join(PRODUCE_DIR, f'{id}.json')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Produce config not found: {id}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stat = os.stat(config_path)
    
    return {
        'id': id,
        'name': data.get('name', id),
        'data': data,
        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        'updated_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


@registry.decorator('produce.create')
async def produce_create(name: str):
    """创建新方案"""
    # 生成 ID
    config_id = name.lower().replace(' ', '_')
    config_path = os.path.join(PRODUCE_DIR, f'{config_id}.json')
    
    if os.path.exists(config_path):
        raise FileExistsError(f"Produce config already exists: {config_id}")
    
    os.makedirs(PRODUCE_DIR, exist_ok=True)
    
    # 创建默认配置
    data = {
        'name': name,
        # TODO: 添加默认方案配置
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created produce config: {config_id}")
    return await produce_read(config_id)


@registry.decorator('produce.update')
async def produce_update(id: str, data: dict[str, Any]):
    """更新方案"""
    config_path = os.path.join(PRODUCE_DIR, f'{id}.json')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Produce config not found: {id}")
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Updated produce config: {id}")
    return {"success": True, "message": "方案已更新"}


@registry.decorator('produce.delete')
async def produce_delete(id: str):
    """删除方案"""
    config_path = os.path.join(PRODUCE_DIR, f'{id}.json')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Produce config not found: {id}")
    
    os.remove(config_path)
    logger.info(f"Deleted produce config: {id}")
    return {"success": True, "message": "方案已删除"}

