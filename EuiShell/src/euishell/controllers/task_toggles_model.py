"""TaskTogglesModel — 快速开关列表模型（只读角色 + QML 展示）。"""
import logging

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt

from euishell.session import TaskTogglesSource

logger = logging.getLogger(__name__)

_ROOT_INDEX = QModelIndex()
"""rowCount 默认入参单例（避免在默认参数中调用构造函数）。"""


class TaskTogglesModel(QAbstractListModel):
    """快速开关数据模型。

    Roles:
      - key: 开关唯一标识
      - label: 显示文本
      - enabled: 是否启用

    数据来自 :class:`TaskTogglesSource`，通过 refresh() 全量刷新。
    """

    KeyRole = Qt.UserRole + 1  # type: ignore[attr-defined]
    LabelRole = Qt.UserRole + 2  # type: ignore[attr-defined]
    EnabledRole = Qt.UserRole + 3  # type: ignore[attr-defined]

    def __init__(self, source: TaskTogglesSource, parent: QObject | None = None) -> None:
        """
        :param source: 快速开关数据源
        :param parent: Qt 父对象
        """
        super().__init__(parent)
        self._source = source
        # 条目以 tuple (key, label, enabled) 保存，避免在模型内散落 dict
        self._entries: list[tuple[str, str, bool]] = []
        self._reload()

    def refresh(self) -> None:
        """从数据源全量刷新模型。"""
        self.beginResetModel()
        self._reload()
        self.endResetModel()

    def _reload(self) -> None:
        try:
            self._entries = [(t.key, t.label, t.enabled) for t in self._source.toggles()]
        except Exception:
            logger.exception('Failed to load task toggles')
            self._entries = []

    def rowCount(self, parent: QModelIndex = _ROOT_INDEX) -> int:
        if parent.isValid():
            return 0
        return len(self._entries)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not (0 <= index.row() < len(self._entries)):
            return None
        key, label, enabled = self._entries[index.row()]
        if role == self.KeyRole:
            return key
        if role == self.LabelRole:
            return label
        if role == self.EnabledRole:
            return enabled
        return None

    def roleNames(self) -> dict:  # type: ignore[override]
        return {
            self.KeyRole: b'key',
            self.LabelRole: b'label',
            self.EnabledRole: b'enabled',
        }
