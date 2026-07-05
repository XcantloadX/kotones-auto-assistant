"""ProduceController — 培育方案的 CRUD 控制器。

用共享 ProduceSolutionsModel，通过 Q_PROPERTY 暴露给 QML。
"""
import json
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Property, Signal, Slot

if TYPE_CHECKING:
    from kaa.application.ui.kaa_session import KaaSession

logger = logging.getLogger(__name__)


class ProduceController(QObject):
    """培育方案的 CRUD 控制器，共享 ProduceSolutionsModel。"""

    solutionsChanged = Signal()
    dirtyChanged = Signal(bool)
    saveRequested = Signal()
    discardRequested = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    selectedSolutionIdChanged = Signal()

    def __init__(self, session: 'KaaSession', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session
        self._dirty: bool = False
        self._model_ref = None

        ps = session.produce_solution_service
        if ps is not None:
            from kaa.application.ui.models.produce_solutions_model import ProduceSolutionsModel
            self._model_ref = ProduceSolutionsModel(ps)

        cs = session.config_service
        if cs is not None:
            cs.bus().configChanged.connect(self.selectedSolutionIdChanged)

    @property
    def _model(self):
        return self._model_ref

    @property
    def _ps(self):
        return self._session.produce_solution_service

    # ── Q_PROPERTY: selectedSolutionId ─────────────────────

    def _get_selected_solution_id(self) -> str:
        cs = self._session.config_service
        if cs is None:
            return ''
        return cs.get_config().tasks.produce.selected_solution_id or ''

    def _set_selected_solution_id(self, sid: str) -> None:
        cs = self._session.config_service
        if cs is None:
            return
        cs.apply_field('tasks.produce.selected_solution_id', sid)

    selectedSolutionId = Property(str, _get_selected_solution_id, _set_selected_solution_id, notify=selectedSolutionIdChanged)

    # ── Q_PROPERTY: solutionsModel ─────────────────────────

    @Property(QObject, constant=True)
    def solutionsModel(self):
        return self._model

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
        if self._dirty:
            self.saveRequested.emit()
        return True

    @Slot()
    def discard(self) -> None:
        self._dirty = False
        self.dirtyChanged.emit(False)
        self.discardRequested.emit()

    # ── 方案列表 ─────────────────────────────────────────

    @Slot(result=str)
    def solutionsJson(self) -> str:
        try:
            if self._ps is None:
                return '[]'
            solutions = self._ps.list_solutions()
            return json.dumps([
                {'id': s.id, 'name': s.name, 'description': s.description or ''}
                for s in solutions
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to list produce solutions")
            return '[]'

    @Slot(str, str, result=bool)
    def checkSolutionNameExists(self, name: str, exclude_id: str) -> bool:
        try:
            if self._model is None:
                return False
            return self._model.check_name_exists(name, exclude_id or None)
        except Exception:
            logger.exception("Failed to check solution name existence")
            return False

    # ── 单方案读写 ───────────────────────────────────────

    @Slot(str, result=str)
    def solutionJson(self, solution_id: str) -> str:
        try:
            if self._model is None:
                return '{}'
            sol = self._model.get_solution(solution_id)
            if sol is None:
                return '{}'
            return sol.model_dump_json()
        except Exception:
            logger.exception("Failed to get produce solution: %s", solution_id)
            return '{}'

    @Slot(str, result=bool)
    def saveSolution(self, json_str: str) -> bool:
        try:
            if self._model is None:
                return False
            from kaa.config.produce import ProduceSolution
            solution = ProduceSolution.model_validate_json(json_str)
            self._model.save_solution(solution)
            self.solutionsChanged.emit()
            self.operationSucceeded.emit(f"方案 '{solution.name}' 已保存")
            self.selectedSolutionIdChanged.emit()
            return True
        except Exception as exc:
            logger.exception("Failed to save produce solution")
            self.operationFailed.emit(f"保存失败：{exc}")
            return False

    # ── CRUD ─────────────────────────────────────────────

    @Slot(str, result=str)
    def createSolution(self, name: str) -> str:
        try:
            if self._model is None:
                return '{}'
            if not name:
                name = "新培育方案"
            solution = self._model.create_solution(name)
            self.solutionsChanged.emit()
            self.operationSucceeded.emit(f"已创建方案: {name}")
            return solution.model_dump_json()
        except Exception as exc:
            logger.exception("Failed to create produce solution")
            self.operationFailed.emit(f"创建失败：{exc}")
            return '{}'

    @Slot(str, result=bool)
    def deleteSolution(self, solution_id: str) -> bool:
        try:
            if self._model is None:
                return False
            if solution_id == self._get_selected_solution_id():
                self.operationFailed.emit("不可删除当前正在使用的培育方案。")
                return False
            self._model.delete_solution(solution_id)
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
        try:
            if self._model is None:
                return '{}'
            solution = self._model.duplicate_solution(solution_id)
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
        try:
            from kaa.config.const import ProduceAction
            return json.dumps([
                {'value': a.value, 'display_name': a.display_name}
                for a in ProduceAction
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to load produce actions")
            return '[]'

    @Slot(result=str)
    def detectModesJson(self) -> str:
        try:
            from kaa.config.const import RecommendCardDetectionMode
            return json.dumps([
                {'value': m.value, 'display_name': m.display_name}
                for m in RecommendCardDetectionMode
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to load detect modes")
            return '[]'
