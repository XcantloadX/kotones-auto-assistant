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

# ── 任务 key → config dot path 映射 ──────────────────────────────
_TASK_CONFIG_PATHS: dict[str, str] = {
    'start_game':             'tasks.start_game.enabled',
    'acquire_activity_funds': 'tasks.activity_funds.enabled',
    'acquire_presents':       'tasks.presents.enabled',
    'assignment':             'tasks.assignment.enabled',
    'capsule_toys':           'tasks.capsule_toys.enabled',
    'club_reward':            'tasks.club_reward.enabled',
    'contest':                'tasks.contest.enabled',
    'purchase':               'tasks.purchase.enabled',
    'upgrade_support_card':   'tasks.upgrade_support_card.enabled',
    'produce':                'tasks.produce.enabled',
    'mission_reward':         'tasks.mission_reward.enabled',
}

# ── 快速设置短标签 ────────────────────────────────────────────────
_TASK_SHORT_NAMES: dict[str, str] = {
    'start_game':             '启动游戏',
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
    RunningRole = Qt.UserRole + 5  # type: ignore[attr-defined]
    StatusTextRole = Qt.UserRole + 6  # type: ignore[attr-defined]

    _roles = {
        NameRole: b'name',
        ShortNameRole: b'shortName',
        PathRole: b'path',
        EnabledRole: b'enabled',
        RunningRole: b'running',
        StatusTextRole: b'statusText',
    }

    def __init__(self, cs: ConfigService, parent=None):
        super().__init__(parent)
        self._cs = cs
        self._running_map: dict[str, str] = {}   # task_name → status
        self._items: list[dict] = []

        cs.bus().configChanged.connect(self._on_config_changed)
        self._rebuild()

    def _rebuild(self):
        config = self._cs.get_config()
        items = []
        for key, func in TASK_REGISTRY.items():
            dot_path = _TASK_CONFIG_PATHS.get(key)
            if dot_path is None:
                continue
            task_obj = func.task
            name = task_obj.name
            enabled = bool(_get_dot_path(config, dot_path))
            items.append({
                'key': key,
                'name': name,
                'shortName': _TASK_SHORT_NAMES.get(key, name),
                'path': dot_path,
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

    def update_running_status(self, name: str, status: str):
        for row, item in enumerate(self._items):
            if item['name'] == name:
                old_status = self._running_map.get(name)
                if old_status != status:
                    self._running_map[name] = status
                    idx = self.index(row, 0)
                    self.dataChanged.emit(idx, idx, [self.RunningRole, self.StatusTextRole])
                return

    def set_all_running_statuses(self, status_map: dict[str, str]):
        changed = False
        for item in self._items:
            s = status_map.get(item['name'], 'pending')
            old = self._running_map.get(item['name'])
            if old != s:
                self._running_map[item['name']] = s
                changed = True
        if changed:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._items) - 1, 0),
                [self.RunningRole, self.StatusTextRole],
            )

    # ── QAbstractListModel 接口 ──────────────────────────────

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
        if role == self.RunningRole:
            return self._running_map.get(item['name'], 'pending') == 'running'
        if role == self.StatusTextRole:
            return self._running_map.get(item['name'], 'pending')
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
