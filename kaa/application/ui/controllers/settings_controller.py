"""SettingsController — 配置读写的 Qt 桥接。

Python 持有活的 Pydantic 模型，通过 Q_PROPERTY 暴露给 QML。
QML 通过 commitConfig() 提交每次编辑，saveConfig() 只做持久化。
"""
import json
import logging
import threading

from PySide6.QtCore import Property, QObject, Signal, Slot

from kaa.application.ui.kaa_session import KaaSession


logger = logging.getLogger(__name__)


class SettingsController(QObject):
    """配置控制器：响应式活状态 + Python-only 副作用 Slot。"""

    configChanged = Signal()   # live config 更新（Q_PROPERTY 的 notify 信号）
    configLoaded = Signal()    # 从磁盘重新加载完成（供 SettingsPage 重置 dirty）
    dirtyChanged = Signal(bool)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    emulatorInstancesReady = Signal(str, str)   # (emulator_type, json)
    emulatorNotInstalled = Signal(str)           # (emulator_type)
    gameDataProgress = Signal(str)
    gameDataResult = Signal(str)
    gameDataDone = Signal()

    def __init__(self, session: KaaSession, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = session
        self._live_cfg: dict = {}
        self._dirty: bool = False

    # ── 核心读写 ─────────────────────────────────────────────────

    @Property('QVariantMap', notify=configChanged)
    def config(self) -> dict:
        """当前活状态快照，结构：{"profile": {...}, "shared": {...}}。"""
        return self._live_cfg

    @Slot()
    def loadConfig(self) -> None:
        """从磁盘加载 config 到活状态，并通知 QML 所有绑定重算。"""
        cs = self._session.config_service
        if cs is None:
            return
        try:
            config_obj = cs.get_config()
            shared = cs.get_shared()
            self._live_cfg = {
                'profile': config_obj.model_dump(mode='json'),
                'shared': shared.model_dump(mode='json'),
            }
            self._dirty = False
            self.configChanged.emit()
            self.configLoaded.emit()
            self.dirtyChanged.emit(False)
        except Exception:
            logger.exception("Failed to load config")

    @Slot(str)
    def commitConfig(self, json_str: str) -> None:
        """接收 QML 编辑后的完整 config JSON，更新活状态。不写盘。"""
        self._live_cfg = json.loads(json_str)
        self.configChanged.emit()

    @Slot()
    def markDirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit(True)

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._dirty

    @Slot(result=bool)
    def saveConfig(self) -> bool:
        """将活状态 Pydantic 校验后写盘。校验失败时 emit operationFailed，返回 False。"""
        cs = self._session.config_service
        if cs is None:
            self.operationFailed.emit("会话尚未初始化")
            return False
        try:
            data = self._live_cfg
            from kaa.config.schema import KaaConfig
            from kaa.config.shared import SharedConfig

            config = KaaConfig.model_validate(data['profile'])
            config.name = self._session.profile_name
            cs.set_config(config)
            cs.save()

            if 'shared' in data:
                shared = SharedConfig.model_validate(data['shared'])
                cs.save_shared(shared)

            self._dirty = False
            self.configChanged.emit()
            self.dirtyChanged.emit(False)
            self.operationSucceeded.emit("设置已保存并应用！")
            return True
        except Exception as e:
            logger.exception("Failed to save config")
            self.operationFailed.emit(str(e))
            return False

    @Slot(result=bool)
    def save(self) -> bool:
        """保存配置；失败时回滚到磁盘状态。"""
        if self.saveConfig():
            return True
        self.loadConfig()
        return False

    @Slot(result=bool)
    def discard(self) -> bool:
        """丢弃未保存更改，重新从磁盘加载。"""
        self.loadConfig()
        return True

    # ── Python-only 副作用 Slots ─────────────────────────────────

    @Slot(str)
    def listEmulatorInstancesAsync(self, emulator_type: str) -> None:
        """后台线程枚举多开实例（调平台 SDK），完成后 emit emulatorInstancesReady。"""
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
        """枚举模拟器多开实例。

        返回格式：``[{"id": ..., "name": ...}, ...]``
        """
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
        """触发游戏资源检查，完成后 emit gameDataResult。"""
        def _run() -> None:
            result = "完成"
            try:
                from kaa.game_data.updater import GameDataUpdater
                updater = GameDataUpdater()
                last_msg = ""
                def progress_cb(text: str) -> None:
                    nonlocal last_msg
                    last_msg = text
                    self.gameDataProgress.emit(text)
                updated = updater.check_and_update(progress_cb=progress_cb)
                if updated:
                    result = "游戏数据更新完成"
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
        """重置游戏窗口位置。"""
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

    # ── 商店枚举数据 ─────────────────────────────────────────────

    @Slot(result=str)
    def moneyShopItemsJson(self) -> str:
        """返回金币商店物品枚举 JSON（文本+值，含所有碎片）。"""
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
        """返回 AP 商店物品枚举 JSON。"""
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
        """返回社团奖励笔记枚举 JSON（过滤出笔记类物品）。"""
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
