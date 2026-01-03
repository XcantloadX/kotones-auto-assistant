import logging
from typing import Any

from kaa.config.schema import BaseConfig
from kotonebot.config.base_config import BackendConfig, UserConfig
from kotonebot.config.manager import load_config, save_config, RootConfig

logger = logging.getLogger(__name__)


class ConfigValidationError(ValueError):
    """Custom exception for configuration validation errors."""
    pass


class ConfigService:
    """
    Manages application configuration, including loading, saving, and validation.
    """

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self._root_config: RootConfig[BaseConfig] | None = None
        self._current_user_config: UserConfig[BaseConfig] | None = None
        self.load()

    def load(self):
        """
        Loads the configuration from the specified config file.
        If the file does not exist or is empty, it creates and saves a default configuration.
        It populates the root configuration and sets the current user config.
        """
        self._root_config = load_config(self.config_path, type=BaseConfig, use_default_if_not_found=True)

        if not self._root_config.user_configs:
            logger.info("config.json not found or is empty, creating a default configuration.")
            default_config = UserConfig[BaseConfig](
                name="默认配置",
                category="default",
                description="默认配置",
                backend=BackendConfig(),
                options=BaseConfig()
            )
            self._root_config.user_configs.append(default_config)
            save_config(self._root_config, self.config_path)
            logger.info("New default configuration created at %s", self.config_path)

        self._current_user_config = self._root_config.user_configs[0]

    def reload(self):
        """Reloads configuration from disk."""
        self.load()
        logger.info("Configuration reloaded from disk.")

    def get_root_config(self) -> RootConfig[BaseConfig]:
        """Returns the entire root configuration object."""
        if not self._root_config:
            raise RuntimeError("Root config not loaded.")
        return self._root_config

    def get_current_user_config(self) -> UserConfig[BaseConfig]:
        """Returns the currently active user configuration."""
        if not self._current_user_config:
            raise RuntimeError("User config not loaded.")
        return self._current_user_config

    def set_current_user_config(self, config: UserConfig[BaseConfig]):
        assert self._root_config is not None, "Root config must be loaded before setting user config."
        self._current_user_config = config
        self._root_config.user_configs[0] = config

    def get_options(self) -> BaseConfig:
        """Returns the 'options' part of the current user configuration."""
        if not self._current_user_config:
            raise RuntimeError("User config not loaded.")
        return self._current_user_config.options

    def save(self):
        """
        Validates and saves the current configuration state to disk.
        """
        if not self._root_config or not self._current_user_config:
            raise RuntimeError("Config not loaded, cannot save.")

        self._validate(self._current_user_config.backend, self._current_user_config.options)
        save_config(self._root_config, self.config_path)
        logger.info("Configuration saved successfully to %s", self.config_path)

    def _validate(self, backend_config: BackendConfig, options: BaseConfig):
        """
        Performs validation checks on the configuration.
        Raises ConfigValidationError if any check fails.
        """
        # Rule 1: Validate screenshot method against the backend type
        valid_screenshot_methods = {
            'mumu12': ['adb', 'adb_raw', 'uiautomator2', 'nemu_ipc'],
            'mumu12v5': ['adb', 'adb_raw', 'uiautomator2', 'nemu_ipc'],
            'leidian': ['adb', 'adb_raw', 'uiautomator2'],
            'custom': ['adb', 'adb_raw', 'uiautomator2'],
            'dmm': ['remote_windows', 'windows']
        }
        if backend_config.screenshot_impl not in valid_screenshot_methods.get(backend_config.type, []):
            raise ConfigValidationError(
                f"截图方法 '{backend_config.screenshot_impl}' "
                f"不适用于当前选择的模拟器类型 '{backend_config.type}'。"
            )

        # Rule 2: Ensure a produce solution is selected if produce is enabled
        if options.produce.enabled and not options.produce.selected_solution_id:
            raise ConfigValidationError("启用培育时，必须选择培育方案。")

        # Rule 3: Ensure item lists are not empty if purchasing is enabled
        if options.purchase.ap_enabled and not options.purchase.ap_items:
            raise ConfigValidationError("启用AP购买时，AP商店购买物品不能为空。")

        if options.purchase.money_enabled and not options.purchase.money_items:
            raise ConfigValidationError("启用金币购买时，金币商店购买物品不能为空。")
