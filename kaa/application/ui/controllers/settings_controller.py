"""SettingsController — 配置读写的 Qt 桥接。

用 ConfigDraft 管理 SettingsPage 草稿，控制页/模型即时写入分开。
"""
import json
import logging
import threading

from PySide6.QtCore import Property, QObject, Signal, Slot

from kaa.application.ui.kaa_session import KaaSession
from kaa.application.ui.config_draft import ConfigDraft
from kaa.application.ui.controllers.shared_settings_controller import SharedSettingsController

logger = logging.getLogger(__name__)


class SettingsController(QObject):
    """配置控制器：草稿模式 + Python-only 副作用 Slot。"""

    configChanged = Signal()
    dirtyChanged = Signal(bool)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    emulatorInstancesReady = Signal(str, str)
    emulatorNotInstalled = Signal(str)
    gameDataProgress = Signal(str)
    gameDataResult = Signal(str)
    gameDataDone = Signal()

    def __init__(self, session: KaaSession, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session
        self._draft = None
        self._shared_ctrl = SharedSettingsController(session, self)
        cs = session.config_service
        if cs is not None:
            self._draft = ConfigDraft(cs)
            cs.bus().configChanged.connect(self._on_external)
            self._shared_ctrl.configChanged.connect(self._on_shared_changed)

    @Property(QObject, constant=True)
    def sharedCtrl(self):
        return self._shared_ctrl

    # ── 核心读写 ─────────────────────────────────────────────

    @Property('QVariantMap', notify=configChanged)  # type: ignore[arg-type]
    def config(self) -> dict:
        """草稿视图：base + dirty 合并，shared 从缓存读（不读盘）。"""
        profile = self._draft.view() if self._draft is not None else {}
        shared = self._draft.view_shared() if self._draft is not None else {}
        return {'profile': profile, 'shared': shared}

    @Slot(str, 'QVariant')
    def setField(self, path: str, value) -> None:
        """profile 字段进草稿。path 不含前缀，相对 profile 根。"""
        if self._draft is None:
            return
        self._draft.set(path, value)
        self.configChanged.emit()
        self.dirtyChanged.emit(self._draft.is_dirty())

    @Slot(str, 'QVariantList')
    def setListField(self, path: str, value) -> None:
        """profile 列表字段进草稿。QML 数组应走此 Slot 以触发 Qt 类型转换。"""
        if self._draft is None:
            return
        self._draft.set(path, list(value))
        self.configChanged.emit()
        self.dirtyChanged.emit(self._draft.is_dirty())

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._draft is not None and self._draft.is_dirty()

    @Slot(result=bool)
    def save(self) -> bool:
        """草稿提交：merge-save + 校验。"""
        if self._draft is None:
            self.operationFailed.emit("会话尚未初始化")
            return False
        if not self._draft.is_dirty():
            self.operationSucceeded.emit("没有需要保存的更改")
            return True
        if self._draft.commit():
            self.dirtyChanged.emit(False)
            self.operationSucceeded.emit("设置已保存并应用！")
            return True
        self.operationFailed.emit("校验失败，请检查联动字段")
        return False

    @Slot(result=bool)
    def discard(self) -> bool:
        """丢弃未保存编辑。"""
        if self._draft is None:
            return False
        self._draft.discard()
        self.configChanged.emit()
        self.dirtyChanged.emit(False)
        return True

    def _on_external(self):
        """外部 configChanged → 刷新 draft base，保留 dirty。"""
        if self._draft is None:
            return
        self._draft.refresh()
        self.configChanged.emit()
        self.dirtyChanged.emit(self._draft.is_dirty())

    def _on_shared_changed(self):
        """SharedSettingsController 变更 → 刷新 draft shared 缓存。"""
        if self._draft is None:
            return
        self._draft.refresh()
        self.configChanged.emit()

    # ── 枚举数据 ─────────────────────────────────────────────

    @Slot(result=str)
    def produceSolutionsJson(self) -> str:
        """返回方案摘要列表 JSON，用于设置页的方案选择下拉。"""
        try:
            ps = self._session.produce_solution_service
            if ps is None:
                return '[]'
            solutions = ps.list_solutions()
            def _text(s):
                return s.name + (' - ' + s.description if s.description else '')
            return json.dumps([
                {'id': s.id, 'text': _text(s)}
                for s in solutions
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to list produce solutions")
            return '[]'

    @Slot(result=str)
    def moneyShopItemsJson(self) -> str:
        try:
            from kaa.config.const import DailyMoneyShopItems
            return json.dumps([
                {'text': DailyMoneyShopItems.to_ui_text(item), 'value': item.value}
                for item in DailyMoneyShopItems
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to load money shop items")
            return '[]'

    @Slot(result=str)
    def apShopItemsJson(self) -> str:
        try:
            from kaa.config.const import APShopItems
            ITEMS_MAP = {
                APShopItems.PRODUCE_PT_UP: "支援强化点数提升",
                APShopItems.PRODUCE_NOTE_UP: "笔记数提升",
                APShopItems.RECHALLENGE: "重新挑战券",
                APShopItems.REGENERATE_MEMORY: "回忆再生成券",
            }
            return json.dumps([
                {'text': ITEMS_MAP[item], 'value': item.value}
                for item in APShopItems
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to load AP shop items")
            return '[]'

    @Slot(result=str)
    def noteItemsJson(self) -> str:
        try:
            from kaa.config.const import DailyMoneyShopItems
            return json.dumps([
                {'text': DailyMoneyShopItems.to_ui_text(item), 'value': item.value}
                for item in DailyMoneyShopItems
                if DailyMoneyShopItems._is_note(item)
            ], ensure_ascii=False)
        except Exception:
            logger.exception("Failed to load note items")
            return '[]'

    # ── Python-only 副作用 Slots ─────────────────────────────

    @Slot(str)
    def listEmulatorInstancesAsync(self, emulator_type: str) -> None:
        def _run() -> None:
            try:
                instances = self._enumerate_instances(emulator_type)
                self.emulatorInstancesReady.emit(
                    emulator_type,
                    json.dumps(instances, ensure_ascii=False),
                )
            except Exception as e:
                from kotonebot.errors import EmulatorNotFoundError
                if isinstance(e, EmulatorNotFoundError) or (isinstance(e, RuntimeError) and 'not installed' in str(e).lower()):
                    self.emulatorNotInstalled.emit(emulator_type)
                else:
                    logger.exception("Failed to enumerate emulator instances")
                self.emulatorInstancesReady.emit(
                    emulator_type,
                    json.dumps([], ensure_ascii=False),
                )
        threading.Thread(target=_run, daemon=True).start()

    def _enumerate_instances(self, emulator_type: str) -> list:
        from kotonebot.errors import EmulatorNotFoundError
        try:
            if emulator_type in ('mumu12', 'mumu12v5'):
                from kotonebot.client.host.mumu12_host import Mumu12Host, Mumu12V5Host
                host_cls = Mumu12V5Host if emulator_type == 'mumu12v5' else Mumu12Host
                instances = host_cls.list()
                return [{'id': str(i.id) if hasattr(i, 'id') else '', 'name': str(getattr(i, 'name', '') or '')} for i in instances]
            if emulator_type == 'leidian':
                from kotonebot.client.host.leidian_host import LeidianHost
                instances = LeidianHost.list()
                return [{'id': str(i.id) if hasattr(i, 'id') else '', 'name': str(getattr(i, 'name', '') or '')} for i in instances]
        except EmulatorNotFoundError:
            raise
        except RuntimeError as e:
            if 'not installed' in str(e).lower():
                raise
            logger.exception("Failed to enumerate instances for %s", emulator_type)
        except Exception:
            logger.exception("Failed to enumerate instances for %s", emulator_type)
        return []

    @Slot()
    def checkGameDataAsync(self) -> None:
        def _run() -> None:
            result = "完成"
            try:
                from kaa.game_data.updater import GameDataUpdater, UpdateOutcome
                updater = GameDataUpdater()
                last_msg = ""
                def progress_cb(text: str) -> None:
                    nonlocal last_msg
                    last_msg = text
                    self.gameDataProgress.emit(text)
                outcome = updater.check_and_update(progress_cb=progress_cb)
                if outcome == UpdateOutcome.UPDATED:
                    self.gameDataProgress.emit("正在构建图像数据索引，可能需要若干分钟")
                    from kaa.image_db.prebuild import ensure_all_image_dbs_built
                    ensure_all_image_dbs_built(status_cb=self.gameDataProgress.emit, force=True)
                    result = "游戏数据更新完成"
                elif outcome == UpdateOutcome.CANCELLED:
                    result = "已跳过本次更新，将使用当前已安装的游戏资源。"
                elif outcome == UpdateOutcome.CHECK_FAILED:
                    result = "检查失败，无法获取游戏资源版本信息。"
                elif last_msg:
                    result = last_msg
                else:
                    result = "目前已是最新版本，无需更新。"
            except Exception as e:
                result = f"检查失败：{e}"
            finally:
                self.gameDataResult.emit(result)
                self.gameDataDone.emit()
        threading.Thread(target=_run, daemon=True).start()

    @Slot()
    def resetGameWindow(self) -> None:
        inst = self._session.instance_service
        if inst is None:
            self.operationFailed.emit("会话尚未初始化")
            return
        try:
            inst.reset_game_window()
            self.operationSucceeded.emit("已重置游戏窗口位置")
        except Exception as e:
            logger.exception("Failed to reset game window")
            self.operationFailed.emit(str(e))
