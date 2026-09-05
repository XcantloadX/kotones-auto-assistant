"""TaskEnabledModel — QAbstractListModel 驱动的任务列表。

Roles:
  - name: 任务显示名
  - shortName: 短标签
  - path: config dot path
  - enabled: 是否启用 (可写)
  - running: 是否正在运行
  - statusText: 状态文字

setData(EnabledRole) → ConfigService.apply_field() 即时写入。
"""
import logging

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from kaa.application.services.config_service import ConfigService, _get_dot_path
from kaa.tasks import TASK_REGISTRY

logger = logging.getLogger(__name__)

# ── 快速设置短标签 ────────────────────────────────────────────────
_TASK_SHORT_NAMES: dict[str, str] = {
    'acquire_activity_funds': '活动费',
    'acquire_presents':       '礼物',
    'assignment':             '工作',
    'capsule_toys':           '扭蛋',
    'club_reward':            '社团',
    'contest':                '竞赛',
    'purchase':               '商店',
    'upgrade_support_card':   '支援卡',
    'produce':                '培育',
    'mission_reward':         '任务',
}

class TaskEnabledModel(QAbstractListModel):
    """任务启用模型。"""

    EnabledRole = Qt.UserRole + 1  # type: ignore[attr-defined]
    NameRole = Qt.UserRole + 2  # type: ignore[attr-defined]
    ShortNameRole = Qt.UserRole + 3  # type: ignore[attr-defined]
    PathRole = Qt.UserRole + 4  # type: ignore[attr-defined]

    _roles = {
        NameRole: b'name',
        ShortNameRole: b'shortName',
        PathRole: b'path',
        EnabledRole: b'enabled',
    }

    def __init__(self, cs: ConfigService, parent=None):
        super().__init__(parent)
        self._cs = cs
        self._items: list[dict] = []

        cs.bus().configChanged.connect(self._on_config_changed)
        self._rebuild()

    def _rebuild(self):
        config = self._cs.get_config()
        items = []
        for key, info in TASK_REGISTRY.items():
            config_name = info.config_name
            if config_name is None:
                continue
            task_obj = info.func.task
            name = task_obj.name
            path = 'tasks.%s.enabled' % config_name
            enabled = bool(_get_dot_path(config, path))
            items.append({
                'key': key,
                'name': name,
                'shortName': _TASK_SHORT_NAMES.get(key, name),
                'path': path,
                'enabled': enabled,
            })
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def _on_config_changed(self):
        config = self._cs.get_config()
        for row, item in enumerate(self._items):
            old_enabled = item['enabled']
            item['enabled'] = bool(_get_dot_path(config, item['path']))
            if item['enabled'] != old_enabled:
                idx = self.index(row, 0)
                self.dataChanged.emit(idx, idx, [self.EnabledRole])
    # QAbstractListModel 接口 ──────────────────────────────

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def data(self, index, role=Qt.DisplayRole):  # type: ignore[attr-defined]
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        if role == self.NameRole:
            return item['name']
        if role == self.ShortNameRole:
            return item['shortName']
        if role == self.PathRole:
            return item['path']
        if role == self.EnabledRole:
            return item['enabled']
        if role == Qt.DisplayRole:  # type: ignore[attr-defined]
            return item['shortName']
        return None

    def setData(self, index, value, role=Qt.EditRole):  # type: ignore[attr-defined]
        if not index.isValid() or index.row() >= len(self._items):
            return False
        if role == self.EnabledRole:
            item = self._items[index.row()]
            self._cs.apply_field(item['path'], bool(value))
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags  # type: ignore[attr-defined]
        return (
            Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEditable  # type: ignore[attr-defined]
        )

    def roleNames(self):
        return self._roles
