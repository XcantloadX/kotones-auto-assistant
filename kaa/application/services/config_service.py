import logging
from typing_extensions import deprecated

from kaa.config.schema import KaaConfig
from kaa.config.base_config import BackendConfig
from kaa.config.shared import SharedConfig
from kaa.config import manager

logger = logging.getLogger(__name__)


class ConfigValidationError(ValueError):
    """Custom exception for configuration validation errors."""
    pass


class ConfigService:
    """
    Manages application configuration, including loading, saving, and validation.
    """

    def __init__(self, name: str = 'default'):
        self._name = name
        self._config: KaaConfig | None = None
        self.load()

    def load(self):
        """从磁盘加载 profile，若不存在则创建默认值。"""
        self._config = manager.read(self._name, not_exist='create')
        logger.info("Configuration '%s' loaded.", self._name)

    def reload(self):
        """从磁盘重新加载 profile。"""
        self.load()
        logger.info("Configuration reloaded from disk.")

    def set_config(self, config: KaaConfig) -> None:
        """设置当前内存中的 profile 配置（不写盘）。"""
        self._config = config

    def get_config(self) -> KaaConfig:
        """返回当前 profile 配置。"""
        if self._config is None:
            raise RuntimeError("Config not loaded.")
        return self._config

    # 兼容旧调用方
    @deprecated("use get_config() instead")
    def get_options(self) -> KaaConfig:
        return self.get_config()

    @deprecated("use get_config() instead")
    def get_current_user_config(self) -> KaaConfig:
        return self.get_config()

    def get_shared(self) -> SharedConfig:
        """返回 _shared.json 配置（含 misc）。"""
        return manager.read_shared()

    def save_shared(self, shared: SharedConfig) -> None:
        """将 shared config 写入磁盘。"""
        manager.write_shared(shared)
        logger.info("Shared configuration saved successfully.")

    def save(self):
        """校验并将当前配置写入磁盘。"""
        if self._config is None:
            raise RuntimeError("Config not loaded, cannot save.")
        self._validate(self._config)
        manager.write(self._name, self._config)
        logger.info("Configuration '%s' saved successfully.", self._name)

    def _validate(self, config: KaaConfig) -> None:
        """对配置执行业务规则校验。"""
        valid_screenshot_methods = {
            'mumu12': ['adb', 'uiautomator2', 'nemu_ipc'],
            'mumu12v5': ['adb', 'uiautomator2', 'nemu_ipc'],
            'leidian': ['adb', 'uiautomator2'],
            'custom': ['adb', 'uiautomator2'],
            'dmm': ['windows', 'windows_native', 'windows_background'],
            'playcover': ['macos'],
        }
        backend = config.backend
        lc_type = backend.lifecycle.type
        if backend.screenshot_impl not in valid_screenshot_methods.get(lc_type, []):
            raise ConfigValidationError(
                f"截图方法 '{backend.screenshot_impl}' "
                f"不适用于当前选择的模拟器类型 '{lc_type}'。"
            )

        if config.tasks.produce.enabled and not config.tasks.produce.selected_solution_id:
            raise ConfigValidationError("启用培育时，必须选择培育方案。")

        if config.tasks.purchase.ap_enabled and not config.tasks.purchase.ap_items:
            raise ConfigValidationError("启用AP购买时，AP商店购买物品不能为空。")

        if config.tasks.purchase.money_enabled and not config.tasks.purchase.money_items:
            raise ConfigValidationError("启用金币购买时，金币商店购买物品不能为空。")
