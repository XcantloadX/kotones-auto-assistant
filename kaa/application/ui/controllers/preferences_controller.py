import copy
import json
import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from kaa.config import manager as config_manager
from kaa.config.shared import SharedConfig

logger = logging.getLogger(__name__)


def _set_dict_path(d: dict, dot_path: str, value) -> None:
    parts = dot_path.split('.')
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    d[parts[-1]] = value


def _get_dict_path(d: dict, dot_path: str):
    parts = dot_path.split('.')
    for part in parts:
        d = d[part]
    return d


class PreferencesController(QObject):
    configChanged = Signal()
    dirtyChanged = Signal(bool)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._base: dict = {}
        self._dirty: dict = {}
        self._reload()

    def _reload(self) -> None:
        shared = config_manager.read_shared()
        self._base = shared.model_dump(mode='json')
        if shared.notify.push.type == 'discord':
            pass
        self._dirty.clear()

    @Property('QVariantMap', notify=configChanged)
    def config(self) -> dict:
        merged = copy.deepcopy(self._base)
        for path, value in self._dirty.items():
            _set_dict_path(merged, path, value)
        return merged

    @Slot(str, 'QVariant')
    def setField(self, path: str, value) -> None:
        self._dirty[path] = value
        self.configChanged.emit()
        self.dirtyChanged.emit(self.isDirty())

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return len(self._dirty) > 0

    @Slot(result=bool)
    def save(self) -> bool:
        if not self._dirty:
            self.operationSucceeded.emit("没有需要保存的更改")
            return True
        try:
            merged = copy.deepcopy(self._base)
            for path, value in self._dirty.items():
                _set_dict_path(merged, path, value)
            candidate = SharedConfig.model_validate(merged)
            config_manager.write_shared(candidate)
            self._base = candidate.model_dump(mode='json')
            self._dirty.clear()
            self.configChanged.emit()
            self.dirtyChanged.emit(False)
            self.operationSucceeded.emit("偏好设置已保存")
            return True
        except Exception as exc:
            logger.exception("Failed to save preferences")
            self.operationFailed.emit(f"保存失败：{exc}")
            return False

    @Slot(result=bool)
    def discard(self) -> bool:
        if not self._dirty:
            return False
        self._dirty.clear()
        self.configChanged.emit()
        self.dirtyChanged.emit(False)
        return True
