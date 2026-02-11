import os
from typing import Type, TypeVar

from .base_config import RootConfig

T = TypeVar('T')

def load_config(
    config_path: str,
    *,
    type: Type[T],
    use_default_if_not_found: bool = True
) -> RootConfig[T]:
    """
    从指定路径读取配置文件

    :param config_path: 配置文件路径
    :param use_default_if_not_found: 如果配置文件不存在，是否使用默认配置
    """
    if not os.path.exists(config_path):
        if use_default_if_not_found:
            return RootConfig[type]()
        else:
            raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return RootConfig[type].model_validate_json(f.read())

def save_config(
    config: RootConfig[T],
    config_path: str,
):
    """将配置保存到指定路径"""
    RootConfig[T].model_validate(config)
    with open(config_path, 'w+', encoding='utf-8') as f:
        f.write(config.model_dump_json(indent=4))
