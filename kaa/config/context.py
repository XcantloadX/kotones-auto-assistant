import logging
from typing import Any, Type, TypeVar, Generic, cast

from .manager import load_config, save_config
from .base_config import UserConfig
from .schema import BaseConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')
V = TypeVar('V')

class ContextConfig:
    def __init__(self, config_path: str = 'config.json'):
        self.config_path: str = config_path
        self.current_key: int | str = 0
        self.root = load_config(self.config_path, type=BaseConfig)

    def create(self, config: UserConfig[BaseConfig]):
        """创建新用户配置"""
        self.root.user_configs.append(config)
        self.save()

    def get(self, key: str | int | None = None) -> UserConfig[BaseConfig] | None:
        """
        获取指定或当前用户配置数据。

        :param key: 用户配置 ID 或索引（从 0 开始），为 None 时获取当前用户配置
        :return: 用户配置数据
        """
        if isinstance(key, int):
            if key < 0 or key >= len(self.root.user_configs):
                return None
            return self.root.user_configs[key]
        elif isinstance(key, str):
            for user in self.root.user_configs:
                if user.id == key:
                    return user
            else:
                return None
        else:
            return self.get(self.current_key)

    def save(self):
        """保存所有配置数据到本地"""
        save_config(self.root, self.config_path)

    def load(self):
        """从本地加载所有配置数据"""
        self.root = load_config(self.config_path, type=BaseConfig)

    def switch(self, key: str | int):
        """切换到指定用户配置"""
        self.current_key = key

    @property
    def current(self) -> UserConfig[BaseConfig]:
        """
        当前配置数据。

        如果当前配置不存在，则使用默认值自动创建一个新配置。
        （不推荐，建议在 UI 中启动前要求用户手动创建，或自行创建一个默认配置。）
        """
        c = self.get(self.current_key)
        if c is None:
            logger.warning("No config found, creating a new one using default values. (NOT RECOMMENDED)")
            c = BaseConfig()
            u = UserConfig(options=c)
            self.create(u)
            c = u
        return c