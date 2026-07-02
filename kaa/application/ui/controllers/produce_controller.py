"""ProduceController — 培育方案的 CRUD 控制器。

数据层只做 JSON 传输，QML 持有完整方案对象副本进行编辑。
"""
import json
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

if TYPE_CHECKING:
    from kaa.application.ui.kaa_session import KaaSession

logger = logging.getLogger(__name__)


class ProduceController(QObject):
    """培育方案的 CRUD 控制器，通过 JSON 与 QML 交换数据。"""

    solutionsChanged = Signal()
    dirtyChanged = Signal(bool)
    saveRequested = Signal()
    discardRequested = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, session: 'KaaSession', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session
        self._dirty: bool = False

    @property
    def _ps(self):
        return self._session.produce_solution_service

    # ── Dirty 状态 ───────────────────────────────────────

    @Slot()
    def markDirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit(True)

    @Slot()
    def markClean(self) -> None:
        if self._dirty:
            self._dirty = False
            self.dirtyChanged.emit(False)

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._dirty

    @Slot(result=bool)
    def save(self) -> bool:
        """通知 QML ProducePage 保存当前方案。"""
        if self._dirty:
            self.saveRequested.emit()
        return True

    @Slot()
    def discard(self) -> None:
        """通知 QML ProducePage 丢弃当前方案的编辑。"""
        self._dirty = False
        self.dirtyChanged.emit(False)
        self.discardRequested.emit()

    # ── 方案列表 ─────────────────────────────────────────

    @Slot(result=str)
    def solutionsJson(self) -> str:
        """返回所有方案的摘要列表 JSON。

        :return: ``[{"id": ..., "name": ..., "description": ...}, ...]``
        """
        try:
            if self._ps is None:
                return '[]'
            solutions = self._ps.list_solutions()
            return json.dumps([
                {
                    'id': s.id,
                    'name': s.name,
                    'description': s.description or '',
                }
                for s in solutions
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to list produce solutions")
            return '[]'

    @Slot(str, str, result=bool)
    def checkSolutionNameExists(self, name: str, exclude_id: str) -> bool:
        """检查方案名称是否已被其他方案使用。

        :param name: 要检查的名称。
        :param exclude_id: 排除的方案 ID（为空字符串时不排除）。
        :return: 名称已存在返回 True。
        """
        try:
            if self._ps is None:
                return False
            return self._ps.check_name_exists(name, exclude_id or None)
        except Exception:
            logger.exception("Failed to check solution name existence")
            return False

    # ── 单方案读写 ───────────────────────────────────────

    @Slot(str, result=str)
    def solutionJson(self, solution_id: str) -> str:
        """返回指定方案的完整 JSON。"""
        try:
            if self._ps is None:
                return '{}'
            solution = self._ps.get_solution(solution_id)
            return solution.model_dump_json()
        except Exception:
            logger.exception("Failed to get produce solution: %s", solution_id)
            return '{}'

    @Slot(str, result=bool)
    def saveSolution(self, json_str: str) -> bool:
        """保存方案（接收完整 ProduceSolution JSON，含 id）。

        :param json_str: 完整的 ProduceSolution JSON。
        :return: 成功返回 True。
        """
        try:
            if self._ps is None:
                return False
            from kaa.config.produce import ProduceSolution
            solution = ProduceSolution.model_validate_json(json_str)
            self._ps.save_solution(solution)
            self.solutionsChanged.emit()
            self.operationSucceeded.emit(f"方案 '{solution.name}' 已保存")
            return True
        except Exception as exc:
            logger.exception("Failed to save produce solution")
            self.operationFailed.emit(f"保存失败：{exc}")
            return False

    # ── CRUD ─────────────────────────────────────────────

    @Slot(str, result=str)
    def createSolution(self, name: str) -> str:
        """创建新方案，返回新方案的完整 JSON，emit solutionsChanged。"""
        try:
            if self._ps is None:
                return '{}'
            if not name:
                name = "新培育方案"
            solution = self._ps.create_solution(name)
            self.solutionsChanged.emit()
            self.operationSucceeded.emit(f"已创建方案: {name}")
            return solution.model_dump_json()
        except Exception as exc:
            logger.exception("Failed to create produce solution")
            self.operationFailed.emit(f"创建失败：{exc}")
            return '{}'

    @Slot(str, result=bool)
    def deleteSolution(self, solution_id: str) -> bool:
        """删除指定方案。"""
        try:
            if self._ps is None:
                return False
            # Prevent deleting the currently selected solution
            cs = self._session.config_service
            if cs is not None:
                selected_id = cs.get_config().tasks.produce.selected_solution_id
                if solution_id == selected_id:
                    self.operationFailed.emit("不可删除当前正在使用的培育方案。")
                    return False
            self._ps.delete_solution(solution_id)
            self.solutionsChanged.emit()
            self.operationSucceeded.emit("方案已删除")
            return True
        except ValueError as exc:
            self.operationFailed.emit(str(exc))
            return False
        except Exception as exc:
            logger.exception("Failed to delete produce solution: %s", solution_id)
            self.operationFailed.emit(f"删除失败：{exc}")
            return False

    @Slot(str, result=str)
    def duplicateSolution(self, solution_id: str) -> str:
        """复制方案，返回新方案的完整 JSON，emit solutionsChanged。"""
        try:
            if self._ps is None:
                return '{}'
            solution = self._ps.duplicate_solution(solution_id)
            self.solutionsChanged.emit()
            self.operationSucceeded.emit(f"已复制方案: {solution.name}")
            return solution.model_dump_json()
        except Exception as exc:
            logger.exception("Failed to duplicate produce solution: %s", solution_id)
            self.operationFailed.emit(f"复制失败：{exc}")
            return '{}'

    # ── 静态枚举数据 ─────────────────────────────────────

    @Slot(result=str)
    def idolCardsJson(self) -> str:
        """返回所有偶像卡数据 JSON。

        :return: ``[{"skin_id": ..., "name": ..., "another_name": ..., "is_another": bool, "character_id": ..., "character_name": ..., "image_path": ...}, ...]``
        """
        try:
            from kaa.db.idol_card import IdolCard
            from kaa.game_data.paths import sprites_path
            cards = IdolCard.all()
            sprite_dir = sprites_path('idol_cards')
            return json.dumps([
                {
                    'skin_id': c.skin_id,
                    'name': c.name,
                    'another_name': c.another_name,
                    'is_another': c.is_another,
                    'character_id': c.character_id,
                    'character_name': c.character_name,
                    'image_path': (sprite_dir / f'{c.skin_id}_0.png').resolve().as_uri(),
                }
                for c in cards
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to load idol cards")
            return '[]'

    @Slot(result=str)
    def produceActionsJson(self) -> str:
        """返回所有培育行动枚举 JSON。

        :return: ``[{"value": ..., "display_name": ...}, ...]``
        """
        try:
            from kaa.config.const import ProduceAction
            return json.dumps([
                {
                    'value': a.value,
                    'display_name': a.display_name,
                }
                for a in ProduceAction
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to load produce actions")
            return '[]'

    @Slot(result=str)
    def detectModesJson(self) -> str:
        """返回推荐卡检测模式枚举 JSON。

        :return: ``[{"value": ..., "display_name": ...}, ...]``
        """
        try:
            from kaa.config.const import RecommendCardDetectionMode
            return json.dumps([
                {
                    'value': m.value,
                    'display_name': m.display_name,
                }
                for m in RecommendCardDetectionMode
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to load detect modes")
            return '[]'
