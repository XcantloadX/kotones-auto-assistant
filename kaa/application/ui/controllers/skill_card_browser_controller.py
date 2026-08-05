"""SkillCardBrowserController — 技能卡图鉴数据桥接（按需分页）。"""
from __future__ import annotations

import json
import logging
import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, Signal, Slot

if TYPE_CHECKING:
    from kaa.application.ui.skill_card_browser.view import SkillCardView

    class Qt:
        UserRole: int
        DisplayRole: int
else:
    from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

# 每页加载张数（无限滚动底层分页）
_PAGE_SIZE = 72

# QAbstractListModel 角色定义
_ROLE_KEYS = [
    'id', 'name', 'rarity', 'category', 'planType',
    'assetPath', 'isCharacterAsset', 'framePath',
    'costStamina', 'isRedStamina', 'costTypeName',
    'costTypeIcon', 'costTypeBg', 'costValue',
    'lessonValue', 'lessonMultiplier', 'blockValue',
    'upgradeCount', 'effectIcons', 'effectText',
    'descriptionSegments', 'evaluation', 'evaluationLabel',
    'unlockLevel', 'originIdol', 'originSupport', 'libraryHidden',
]
_ROLES: dict[int, bytes] = {
    Qt.UserRole + 1 + i: k.encode()
    for i, k in enumerate(_ROLE_KEYS)
}
_ROLE_NAME_TO_ID: dict[str, int] = {
    k: Qt.UserRole + 1 + i
    for i, k in enumerate(_ROLE_KEYS)
}


class SkillCardBrowserController(QAbstractListModel):
    """轻量索引 + QAbstractListModel 按页加载，供 QML 无限滚动。"""

    # 索引就绪（可筛选）
    indexReady = Signal()
    loadingChanged = Signal()
    # 筛选结果重置（仅用于 QML 滚回顶部）
    pageReset = Signal()
    staticIconsChanged = Signal()
    totalChanged = Signal()
    hasMoreChanged = Signal()
    loadingMoreChanged = Signal()
    # 跨线程批数据就绪（list, is_reset）
    _itemsBatchReady = Signal(list, bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._loading = False
        self._loading_more = False
        self._static_icons: dict[str, str] = {}
        self._lock = threading.Lock()
        self._index_loaded = False

        # id -> SkillCardView 实例
        self._card_by_id: dict[str, 'SkillCardView'] = {}
        # 轻量索引列表（可见卡）
        self._index: list[dict] = []
        # 当前筛选后的 id 列表
        self._filtered_ids: list[str] = []
        # 已渲染缓存 id -> dict
        self._render_cache: dict[str, dict] = {}
        # QAbstractListModel 数据
        self._items: list[dict] = []
        # 分页游标
        self._offset = 0
        self._has_more = False

        self._itemsBatchReady.connect(self._on_batch_ready)

        # 当前筛选条件
        self._filter = {
            'rarities': set(),
            'categories': set(),
            'planTypes': set(),
            'grades': set(),
            'search': '',
        }

    # ── QAbstractListModel ──────────────────────────────────────────────

    def roleNames(self):
        return _ROLES

    def data(self, index, role):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == Qt.DisplayRole:
            return item
        key = _ROLES.get(role)
        if key is None:
            return None
        return item.get(key.decode())

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    # ── Properties ────────────────────────────────────────────────────

    def _get_loading(self) -> bool:
        return self._loading

    loading = Property(bool, _get_loading, notify=loadingChanged)

    def _get_loading_more(self) -> bool:
        return self._loading_more

    loadingMore = Property(bool, _get_loading_more, notify=loadingMoreChanged)

    def _get_total(self) -> int:
        return len(self._filtered_ids)

    totalCount = Property(int, _get_total, notify=totalChanged)

    def _get_has_more(self) -> bool:
        return self._has_more

    hasMore = Property(bool, _get_has_more, notify=hasMoreChanged)

    def _get_index_loaded(self) -> bool:
        return self._index_loaded

    indexLoaded = Property(bool, _get_index_loaded, notify=indexReady)

    # ── Slots ─────────────────────────────────────────────────────────

    @Slot()
    def ensureLoaded(self) -> None:
        """后台构建轻量索引（很快）；完成后发 indexReady。"""
        if self._index_loaded or self._loading:
            return
        self._loading = True
        self.loadingChanged.emit()
        threading.Thread(target=self._load_index_worker, daemon=True).start()

    def _load_index_worker(self) -> None:
        try:
            from kaa.db.skill_card import SkillCard
            from kaa.game_data.paths import skill_card_index
            from kaa.application.ui.skill_card_browser import assets
            from kaa.application.ui.skill_card_browser.view import SkillCardView

            skill_card_index()  # warm up downloaded asset index
            icons = assets.static_icons_json()
            all_cards = SkillCard.all()

            index: list[dict] = []
            by_id: dict[str, 'SkillCardView'] = {}
            for card in all_cards:
                if card.library_hidden:
                    continue
                if card.upgrade_count:  # None / 0 → 基础；1,2,3 → 跳过强化版本
                    continue
                view = SkillCardView(card)
                by_id[card._id] = view
                try:
                    index.append(view.to_index_dict())
                except Exception:
                    logger.exception('index failed %s', card._id)

            with self._lock:
                self._static_icons = icons
                self._card_by_id = by_id
                self._index = index
                self._index_loaded = True
                self._loading = False
                # 默认无筛选：全部 id
                self._filtered_ids = [x['id'] for x in index]
                self._offset = 0
                self._has_more = len(self._filtered_ids) > 0

            self.staticIconsChanged.emit()
            self.indexReady.emit()
            self.totalChanged.emit()
            self.hasMoreChanged.emit()
            self.loadingChanged.emit()

            # 自动加载第一页
            self._emit_page(reset=True)
        except Exception:
            logger.exception('Failed to load skill card index')
            with self._lock:
                self._loading = False
                self._index_loaded = True
            self.loadingChanged.emit()
            self.indexReady.emit()

    @Slot(result=str)
    def staticIconsJson(self) -> str:
        with self._lock:
            return json.dumps(self._static_icons, ensure_ascii=False)

    @Slot(str, str, str, str, str)
    def applyFilter(
        self,
        rarities_csv: str,
        categories_csv: str,
        plan_types_csv: str,
        search: str,
        grades_csv: str,
    ) -> None:
        """更新筛选并重置为第一页（后台渲染首包）。"""
        rarities = {x.strip() for x in rarities_csv.split(',') if x.strip()}
        categories = {x.strip() for x in categories_csv.split(',') if x.strip()}
        plan_types = {x.strip() for x in plan_types_csv.split(',') if x.strip()}
        grades = {int(x.strip()) for x in grades_csv.split(',') if x.strip().isdigit()}
        q = search.strip().lower()

        with self._lock:
            self._filter = {
                'rarities': rarities,
                'categories': categories,
                'planTypes': plan_types,
                'grades': grades,
                'search': q,
            }
            if not self._index_loaded:
                return
            self._filtered_ids = self._compute_filtered_ids_unlocked()
            self._offset = 0
            self._has_more = len(self._filtered_ids) > 0

        self.totalChanged.emit()
        self.hasMoreChanged.emit()
        threading.Thread(target=lambda: self._emit_page(reset=True), daemon=True).start()

    def _compute_filtered_ids_unlocked(self) -> list[str]:
        f = self._filter
        rarities = f['rarities']
        categories = f['categories']
        plan_types = f['planTypes']
        grades = f['grades']
        q = f['search']
        out: list[str] = []
        for item in self._index:
            if rarities and item.get('rarity') not in rarities:
                continue
            if categories and item.get('category') not in categories:
                continue
            if plan_types and item.get('planType') not in plan_types:
                continue
            if grades and int(item.get('upgradeCount') or 0) not in grades:
                continue
            if q:
                name = (item.get('name') or '').lower()
                cid = (item.get('id') or '').lower()
                text = (item.get('effectText') or '').lower()
                if q not in name and q not in cid and q not in text:
                    continue
            out.append(item['id'])
        return out

    @Slot()
    def loadMore(self) -> None:
        """无限滚动：追加下一页。"""
        with self._lock:
            if not self._index_loaded or not self._has_more or self._loading_more:
                return
            self._loading_more = True
        self.loadingMoreChanged.emit()
        threading.Thread(target=lambda: self._emit_page(reset=False), daemon=True).start()

    # ── 后台渲染 + 主线程模型更新 ─────────────────────────────────

    def _emit_page(self, *, reset: bool) -> None:
        try:
            with self._lock:
                ids = self._filtered_ids
                start = 0 if reset else self._offset
                end = min(start + _PAGE_SIZE, len(ids))
                page_ids = ids[start:end]
                card_by_id = self._card_by_id
                cache = self._render_cache

            rendered: list[dict] = []
            new_cache: dict[str, dict] = {}
            for cid in page_ids:
                hit = cache.get(cid)
                if hit is not None:
                    rendered.append(hit)
                    continue
                view = card_by_id.get(cid)
                if view is None:
                    continue
                try:
                    d = view.to_render_dict()
                    new_cache[cid] = d
                    rendered.append(d)
                except Exception:
                    logger.exception('render failed %s', cid)

            with self._lock:
                self._render_cache.update(new_cache)
                self._offset = end
                self._has_more = end < len(self._filtered_ids)
                # _loading_more 在 _on_batch_ready 中主线程重置

            self._itemsBatchReady.emit(rendered, reset)
        except Exception:
            logger.exception('emit page failed')
            with self._lock:
                self._loading_more = False
            self.loadingMoreChanged.emit()

    @Slot(list, bool)
    def _on_batch_ready(self, items: list[dict], is_reset: bool) -> None:
        """在主线程收到渲染批数据后，安全地更新 QAbstractListModel。"""
        if is_reset:
            self.beginResetModel()
            self._items = items
            self.endResetModel()
            self.pageReset.emit()
        else:
            n = len(self._items)
            self.beginInsertRows(QModelIndex(), n, n + len(items) - 1)
            self._items.extend(items)
            self.endInsertRows()
        with self._lock:
            self._loading_more = False
        self.hasMoreChanged.emit()
        self.loadingMoreChanged.emit()
