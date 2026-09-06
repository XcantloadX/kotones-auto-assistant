"""PreferencesControllerBase — 偏好（全局配置）草稿控制器基类。"""
import copy
import logging
from abc import abstractmethod
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

logger = logging.getLogger(__name__)


def _set_dict_path(d: dict, dot_path: str, value: Any) -> None:
    parts = dot_path.split('.')
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    d[parts[-1]] = value


def _get_dict_path(d: dict, dot_path: str) -> Any:
    parts = dot_path.split('.')
    for part in parts:
        d = d[part]
    return d


class PreferencesControllerBase(QObject):
    """偏好控制器抽象基类：dot-path 草稿 + 保存时校验。

    下游子类实现 :meth:`_load_config`（读取全量配置 map）与
    :meth:`_commit_config`（校验并持久化全量配置 map）。
    Shell 保留键：``interface.color_scheme`` / ``interface.theme_color`` /
    ``interface.window_style``（见 AppearanceSettingsStore）。
    """

    configChanged = Signal()
    dirtyChanged = Signal(bool)
    saved = Signal()
    """保存成功后发射；ShellApp 借此触发外观实时应用。"""
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._base: dict = {}
        self._dirty: dict[str, Any] = {}
        self._reload()

    @abstractmethod
    def _load_config(self) -> dict:
        """读取全量偏好配置 map（dict 嵌套结构，QML 边界载荷）。"""

    @abstractmethod
    def _commit_config(self, merged: dict) -> None:
        """校验并持久化全量偏好配置 map。

        :param merged: base + 草稿合并后的配置 map
        :raises Exception: 校验或持久化失败时抛出（由 save 转为 operationFailed）
        """

    def _reload(self) -> None:
        self._base = self._load_config()
        self._dirty.clear()

    @Property('QVariantMap', notify=configChanged)  # type: ignore[arg-type]
    def config(self) -> dict:
        """草稿视图：base + dirty 合并。"""
        merged = copy.deepcopy(self._base)
        for path, value in self._dirty.items():
            _set_dict_path(merged, path, value)
        return merged

    @Slot(str, 'QVariant')  # type: ignore
    def setField(self, path: str, value: Any) -> None:
        """写入草稿字段。

        :param path: dot path（如 ``interface.color_scheme``）
        :param value: 字段值
        """
        self._dirty[path] = value
        self.configChanged.emit()
        self.dirtyChanged.emit(self.isDirty())

    @Slot(result=bool)
    def isDirty(self) -> bool:
        """返回是否有未保存草稿。"""
        return len(self._dirty) > 0

    @Slot(result=bool)
    def save(self) -> bool:
        """提交草稿并持久化；成功后发射 saved。"""
        if not self._dirty:
            self.operationSucceeded.emit('没有需要保存的更改')
            return True
        try:
            merged = copy.deepcopy(self._base)
            for path, value in self._dirty.items():
                _set_dict_path(merged, path, value)
            self._commit_config(merged)
            self._base = merged
            self._dirty.clear()
            self.configChanged.emit()
            self.dirtyChanged.emit(False)
            self.saved.emit()
            self.operationSucceeded.emit('偏好设置已保存')
            return True
        except Exception as exc:
            logger.exception('Failed to save preferences')
            self.operationFailed.emit(f'保存失败：{exc}')
            return False

    @Slot(result=bool)
    def discard(self) -> bool:
        """丢弃未保存草稿；返回是否有更改被丢弃。"""
        if not self._dirty:
            return False
        self._dirty.clear()
        self.configChanged.emit()
        self.dirtyChanged.emit(False)
        return True
