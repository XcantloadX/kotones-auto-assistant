"""ProduceSolutionsModel — QAbstractListModel 包装 ProduceSolutionService。

所有 CRUD 操作走 model，自动 emit 标准 Qt 信号让 QML 天然响应。
"""
import logging

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from kaa.application.services.produce_solution_service import ProduceSolutionService
from kaa.config.produce import ProduceSolution

logger = logging.getLogger(__name__)


class ProduceSolutionsModel(QAbstractListModel):
    def __init__(self, service: ProduceSolutionService, parent=None):
        super().__init__(parent)
        self._service = service
        self._solutions: list[ProduceSolution] = []
        self._reload()

    def _reload(self):
        self.beginResetModel()
        self._solutions = self._service.list_solutions()
        self.endResetModel()

    # ── 公开接口 ───────────────────────────────────────────

    def get_solution(self, solution_id: str) -> ProduceSolution | None:
        for s in self._solutions:
            if s.id == solution_id:
                return s
        try:
            return self._service.get_solution(solution_id)
        except Exception:
            return None

    def create_solution(self, name: str) -> ProduceSolution:
        sol = self._service.create_solution(name)
        self._reload()
        return sol

    def save_solution(self, solution: ProduceSolution) -> None:
        self._service.save_solution(solution)
        self._reload()

    def delete_solution(self, solution_id: str) -> None:
        self._service.delete_solution(solution_id)
        self._reload()

    def duplicate_solution(self, solution_id: str) -> ProduceSolution:
        sol = self._service.duplicate_solution(solution_id)
        self._reload()
        return sol

    def check_name_exists(self, name: str, exclude_id: str | None = None) -> bool:
        return self._service.check_name_exists(name, exclude_id)

    # ── QAbstractListModel 接口 ──────────────────────────

    IdRole = Qt.UserRole + 1  # type: ignore[attr-defined]
    NameRole = Qt.UserRole + 2  # type: ignore[attr-defined]
    DescriptionRole = Qt.UserRole + 3  # type: ignore[attr-defined]
    TextRole = Qt.UserRole + 4  # type: ignore[attr-defined]

    _roles = {
        IdRole: b'id',
        NameRole: b'name',
        DescriptionRole: b'description',
        TextRole: b'text',
    }

    def rowCount(self, parent=QModelIndex()):
        return len(self._solutions)

    def data(self, index, role=Qt.DisplayRole):  # type: ignore[attr-defined]
        if not index.isValid() or index.row() >= len(self._solutions):
            return None
        sol = self._solutions[index.row()]
        if role == self.IdRole:
            return sol.id
        if role == self.NameRole:
            return sol.name
        if role == self.DescriptionRole:
            return sol.description or ''
        if role == self.TextRole:
            text = sol.name
            if sol.description:
                text += ' - ' + sol.description
            return text
        if role == Qt.DisplayRole:  # type: ignore[attr-defined]
            return sol.name
        return None

    def roleNames(self):
        return self._roles
