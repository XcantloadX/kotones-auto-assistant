import logging
from typing_extensions import deprecated

from PySide6.QtCore import QObject, Signal

from kaa.config.schema import KaaConfig
from kaa.config.shared import SharedConfig
from kaa.config import manager
from kaa.config.validation import (
    ConfigIssue,
    ConfigValidationError,
    validate_profile_config,
)

logger = logging.getLogger(__name__)


class ConfigSignalBus(QObject):
    """信号总线，惰性构造在 GUI 线程，使信号 affinity 天然正确。"""
    configChanged = Signal()


def _set_dot_path(obj, dot_path: str, value) -> None:
    """按 dot path 设置嵌套属性。"""
    parts = dot_path.split('.')
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)


def _get_dot_path(obj, dot_path: str):
    """按 dot path 读取嵌套属性。"""
    parts = dot_path.split('.')
    for part in parts:
        obj = getattr(obj, part)
    return obj


def _set_dict_path(d: dict, dot_path: str, value) -> None:
    """按 dot path 设置嵌套字典值。"""
    parts = dot_path.split('.')
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    d[parts[-1]] = value


def _get_dict_path(d: dict, dot_path: str):
    """按 dot path 读取嵌套字典值。"""
    parts = dot_path.split('.')
    for part in parts:
        d = d[part]
    return d


class ConfigService:
    """
    Manages application configuration, including loading, saving, and validation.
    """

    def __init__(self, name: str = 'default'):
        self._name = name
        self._config: KaaConfig | None = None
        self._bus: ConfigSignalBus | None = None
        self.load()

    def bus(self) -> ConfigSignalBus:
        """惰性构造 ConfigSignalBus。首次调用应在 GUI 线程，affinity 自动正确。"""
        if self._bus is None:
            self._bus = ConfigSignalBus()
        return self._bus

    def load(self):
        """从磁盘加载 profile，若不存在则创建默认值。"""
        self._config = manager.read(self._name, not_exist='create')
        logger.info("Configuration '%s' loaded.", self._name)

    def reload(self):
        """从磁盘重新加载 profile。"""
        self.load()
        if self._bus:
            self._bus.configChanged.emit()
        logger.info("Configuration reloaded from disk.")

    def set_config(self, config: KaaConfig) -> None:
        """设置当前内存中的 profile 配置（不写盘）。"""
        self._config = config
        if self._bus:
            self._bus.configChanged.emit()

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

    def apply_field(self, dot_path: str, value) -> None:
        """即时写入：就地改 + 写盘 + emit。不校验。"""
        assert self._config is not None
        _set_dot_path(self._config, dot_path, value)
        manager.write(self._name, self._config)
        if self._bus:
            self._bus.configChanged.emit()

    def apply_fields(self, items: list[tuple[str, object]]) -> None:
        """批量即时写入：一次写盘 + 一次 emit。"""
        assert self._config is not None
        for path, value in items:
            _set_dot_path(self._config, path, value)
        manager.write(self._name, self._config)
        if self._bus:
            self._bus.configChanged.emit()

    def save(self):
        """校验并将当前配置写入磁盘。"""
        if self._config is None:
            raise RuntimeError("Config not loaded, cannot save.")
        self._raise_if_invalid(self._config)
        manager.write(self._name, self._config)
        if self._bus:
            self._bus.configChanged.emit()
        logger.info("Configuration '%s' saved successfully.", self._name)

    def collect_issues(self, config: KaaConfig | None = None) -> list[ConfigIssue]:
        """返回业务规则校验问题列表（不抛异常）。

        :param config: 待校验对象；为 None 时校验 live config。
        :return: ConfigIssue 列表，为空表示无问题。
        """
        return validate_profile_config(config or self._config)

    def validate(self, config: KaaConfig | None = None) -> None:
        """校验给定对象（默认 live config）；存在 error 级问题时抛 ConfigValidationError。"""
        self._raise_if_invalid(config or self._config)

    def _raise_if_invalid(self, config: KaaConfig) -> None:
        """若存在 error 级校验问题，聚合消息抛出 ConfigValidationError。"""
        errors = [i for i in validate_profile_config(config) if i.severity == 'error']
        if errors:
            raise ConfigValidationError('；'.join(i.message for i in errors))
