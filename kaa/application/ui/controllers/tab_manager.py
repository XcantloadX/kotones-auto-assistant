"""TabManager — 管理多 profile tab 生命周期。

每个 tab 对应一个 KaaSession（内含 Kaa 实例和所有服务）。
TabManager 负责 tab 的创建/关闭/激活/批量运行，并通过 Qt Signals 通知 QML。
"""
import json
import logging
import threading
import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, Property, Signal, Slot

from kaa.application.ui.kaa_session import KaaSession
from .run_controller import RunController
from .settings_controller import SettingsController
from .progress_bridge import ProgressBridge
from .log_bridge import LogBridge
from .produce_controller import ProduceController
from .update_controller import UpdateController
from .feedback_controller import FeedbackController

logger = logging.getLogger(__name__)


@dataclass
class _TabEntry:
    session: KaaSession
    run_ctrl: RunController | None = None  # 惰性创建（主线程）
    settings_ctrl: SettingsController | None = None  # 惰性创建（主线程）
    progress_bridge: ProgressBridge | None = None  # 惰性创建（主线程）
    log_bridge: LogBridge | None = None  # 惰性创建（主线程）
    produce_ctrl: ProduceController | None = None  # 惰性创建（主线程）
    update_ctrl: UpdateController | None = None  # 惰性创建（主线程）
    feedback_ctrl: FeedbackController | None = None  # 惰性创建（主线程）

    @property
    def config_name(self) -> str:
        return self.session.profile_name

    @property
    def is_running(self) -> bool:
        return self.session.is_running


class TabManager(QObject):
    """管理多 profile tab 生命周期，并向 QML 暴露 tab 列表和状态。"""

    tabsChanged = Signal()
    activeTabChanged = Signal()
    batchModeChanged = Signal()
    closeTabBlocked = Signal(str)          # reason
    readyToCloseTab = Signal(int)          # index
    tabOpenFailed = Signal(str)            # error
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    capturePageRequested = Signal(int)     # capture mode: navigate to page index

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tabs: list[_TabEntry] = []
        self._active_index: int = 0
        self._batch_mode: str = ''          # '' | 'sequential' | 'parallel'
        self._stop_all_busy: bool = False
        self._seq_cancel: threading.Event | None = None
        self._lock = threading.Lock()

    # ── 内部工具 ──────────────────────────────────────────────────────

    def _create_entry(self, config_name: str) -> _TabEntry:
        session = KaaSession(config_name)
        return _TabEntry(session=session)

    def _destroy_entry(self, entry: _TabEntry) -> None:
        try:
            if entry.progress_bridge is not None:
                entry.progress_bridge.uninstall()
        except Exception:
            logger.exception("Failed to uninstall progress bridge for '%s'", entry.config_name)
        try:
            if entry.log_bridge is not None:
                entry.log_bridge.close()
        except Exception:
            logger.exception("Failed to close log bridge for '%s'", entry.config_name)
        try:
            entry.session.destroy()
        except Exception:
            logger.exception("Failed to destroy session for '%s'", entry.config_name)

    def _save_tabs(self) -> None:
        try:
            from kaa.config import manager
            shared = manager.read_shared()
            shared.profiles.open_tabs = [t.config_name for t in self._tabs]
            active = self._active_entry()
            shared.profiles.last_used = active.config_name if active is not None else None
            manager.write_shared(shared)
        except Exception:
            logger.exception('Failed to save tab list')

    def _run_entry_tasks(self, entry: _TabEntry) -> None:
        """初始化 session 并启动所有任务，阻塞至完成。"""
        try:
            entry.session.initialize()
            ts = entry.session.task_service
            if ts is None:
                return
            ts.start_all_tasks()
            # 等待任务完成
            while entry.is_running:
                time.sleep(0.5)
        except Exception:
            logger.exception("Run tasks failed for '%s'", entry.config_name)

    def restore_tabs(self) -> None:
        """从 shared config 恢复已保存的 tabs，在后台线程中调用。"""
        try:
            from kaa.config import manager
            shared = manager.read_shared()
            names = shared.profiles.open_tabs or []
            last_used = shared.profiles.last_used
            available = set(manager.list_profiles())

            names = [n for n in names if n in available]
            entries: list[_TabEntry] = []
            for name in names:
                try:
                    session = KaaSession(name)
                    session.initialize()
                    entries.append(_TabEntry(session=session))
                except Exception:
                    logger.exception('Failed to restore tab: %s', name)

            with self._lock:
                self._tabs = entries
                if last_used and any(t.config_name == last_used for t in self._tabs):
                    self._active_index = next(
                        i for i, t in enumerate(self._tabs) if t.config_name == last_used
                    )
                else:
                    self._active_index = 0 if self._tabs else 0

            self.tabsChanged.emit()
            self.activeTabChanged.emit()
        except Exception:
            logger.exception('Failed to restore tabs')

    def _active_entry(self) -> _TabEntry | None:
        if 0 <= self._active_index < len(self._tabs):
            return self._tabs[self._active_index]
        return None

    def get_active_task_service(self):
        """获取当前活跃 tab 的 task_service，无活跃 tab 时返回 None。"""
        entry = self._active_entry()
        if entry is None:
            return None
        return entry.session.task_service

    # ── QML Slots ─────────────────────────────────────────────────────

    @Slot(str)
    def openTab(self, config_name: str) -> None:
        """在新 tab 中打开指定配置。同一配置不能重复打开。"""
        if any(t.config_name == config_name for t in self._tabs):
            self.operationFailed.emit(f'配置 "{config_name}" 已在某个 Tab 中打开')
            return
        try:
            entry = self._create_entry(config_name)
            self._tabs.append(entry)
            self._active_index = len(self._tabs) - 1
            self._save_tabs()
            self.tabsChanged.emit()
            self.activeTabChanged.emit()

            # 后台线程初始化 session
            def _init_and_notify():
                try:
                    entry.session.initialize()
                    # session 初始化完毕，通知 RunController 刷新任务列表
                    # （避免 QML 页面在初始化前已创建好，导致任务列表为空）
                    if entry.run_ctrl is not None:
                        entry.run_ctrl.tasksChanged.emit()
                except Exception:
                    logger.exception('Failed to initialize tab: %s', config_name)
                    self.tabOpenFailed.emit(str(config_name))
                    return
                self.tabsChanged.emit()
            threading.Thread(target=_init_and_notify, daemon=True).start()
        except Exception as e:
            logger.exception('Failed to open tab: %s', config_name)
            self.tabOpenFailed.emit(str(e))

    @Slot(int)
    def setActiveTab(self, index: int) -> None:
        if index < 0 or index >= len(self._tabs):
            return
        if index == self._active_index:
            return
        self._active_index = index
        self._save_tabs()
        self.activeTabChanged.emit()

    @Slot(int)
    def requestCloseTab(self, index: int) -> None:
        """请求关闭 tab。若 running 则阻断；否则 emit readyToCloseTab。"""
        if index < 0 or index >= len(self._tabs):
            return
        entry = self._tabs[index]
        if entry.is_running:
            self.closeTabBlocked.emit('请先停止正在运行的任务')
            return
        self.readyToCloseTab.emit(index)

    @Slot(int)
    def closeTab(self, index: int) -> None:
        """无条件关闭 tab。"""
        if index < 0 or index >= len(self._tabs):
            return
        entry = self._tabs.pop(index)
        self._destroy_entry(entry)

        if self._active_index >= len(self._tabs):
            self._active_index = len(self._tabs) - 1
        elif self._active_index > index:
            self._active_index -= 1

        self._save_tabs()
        self.tabsChanged.emit()
        self.activeTabChanged.emit()

    @Slot(str, result=bool)
    def closeTabForConfig(self, config_name: str) -> bool:
        """ConfigManagerDialog 删除配置前调用。"""
        for i, entry in enumerate(self._tabs):
            if entry.config_name == config_name:
                if entry.is_running:
                    return False
                if len(self._tabs) <= 1:
                    return False
                removed = self._tabs.pop(i)
                self._destroy_entry(removed)
                if self._active_index >= len(self._tabs):
                    self._active_index = len(self._tabs) - 1
                elif self._active_index > i:
                    self._active_index -= 1
                self._save_tabs()
                self.tabsChanged.emit()
                self.activeTabChanged.emit()
                return True
        return True

    @Slot(str, result=bool)
    def isTabOpen(self, config_name: str) -> bool:
        return any(t.config_name == config_name for t in self._tabs)

    @Slot(str, result=bool)
    def createProfile(self, name: str) -> bool:
        """创建新配置并打开对应 tab。"""
        try:
            from kaa.config import manager
            manager.create(name, exist='ok')
            self.openTab(name)
            self.operationSucceeded.emit(f'已创建配置: {name}')
            return True
        except Exception as exc:
            self.operationFailed.emit(f'创建失败：{exc}')
            return False

    @Slot(str, str, result=bool)
    def renameProfile(self, old_name: str, new_name: str) -> bool:
        """重命名配置文件。若该配置有打开的 tab，先关闭再用新名重新打开。"""
        try:
            from kaa.config import manager
            manager.rename(old_name, new_name)
            was_open = self.isTabOpen(old_name)
            if was_open:
                for i, entry in enumerate(self._tabs):
                    if entry.config_name == old_name:
                        self.closeTab(i)
                        break
                self.openTab(new_name)
            self.operationSucceeded.emit(f'已将配置重命名为: {new_name}')
            return True
        except FileExistsError:
            self.operationFailed.emit(f'配置 "{new_name}" 已存在')
            return False
        except FileNotFoundError:
            self.operationFailed.emit(f'配置 "{old_name}" 不存在')
            return False
        except Exception as exc:
            self.operationFailed.emit(f'重命名失败：{exc}')
            return False

    @Slot(str, result=bool)
    def deleteProfile(self, name: str) -> bool:
        """删除配置文件。调用前应先通过 closeTabForConfig 关闭 tab。"""
        try:
            from kaa.config import manager
            manager.remove(name, not_exist='ok')
            self.operationSucceeded.emit(f'已删除配置: {name}')
            self.tabsChanged.emit()
            return True
        except Exception as exc:
            self.operationFailed.emit(f'删除失败：{exc}')
            return False

    # ── 批量运行 ───────────────────────────────────────────────────────

    @Slot()
    def startAllSequential(self) -> None:
        """在后台线程中依次启动所有 tab。"""
        cancel = threading.Event()
        self._seq_cancel = cancel
        self._batch_mode = 'sequential'
        self.batchModeChanged.emit()

        tabs = list(self._tabs)

        def _run() -> None:
            for entry in tabs:
                if cancel.is_set():
                    break
                if entry.is_running:
                    continue
                self._run_entry_tasks(entry)

            if not cancel.is_set():
                self._batch_mode = ''
                self.batchModeChanged.emit()
                

        threading.Thread(target=_run, daemon=True).start()

    @Slot()
    def startAllParallel(self) -> None:
        """同时启动所有 tab。"""
        self._batch_mode = 'parallel'
        self.batchModeChanged.emit()

        threads = []
        for entry in list(self._tabs):
            if entry.is_running:
                continue
            t = threading.Thread(
                target=self._run_entry_tasks,
                args=(entry,),
                daemon=True,
            )
            t.start()
            threads.append(t)

        def _watch() -> None:
            for t in threads:
                t.join()
            if not self._stop_all_busy:
                self._batch_mode = ''
                self.batchModeChanged.emit()
                

        threading.Thread(target=_watch, daemon=True).start()

    @Slot()
    def stopAll(self) -> None:
        """停止所有 tab。"""
        if self._stop_all_busy:
            return
        self._stop_all_busy = True
        self.batchModeChanged.emit()

        # 取消连续执行循环
        if self._seq_cancel is not None:
            self._seq_cancel.set()

        for entry in self._tabs:
            kaa = entry.session.kaa
            if kaa is None:
                logger.warning("Tab '%s' has no Kaa instance", entry.config_name)
                continue
            try:
                kaa.stop()
            except Exception:
                logger.exception("Failed to stop '%s'", entry.config_name)

        self._batch_mode = ''
        self._stop_all_busy = False
        self.batchModeChanged.emit()
        

    # ── JSON 序列化 ───────────────────────────────────────────────────

    @Slot(result=str)
    def allConfigsJson(self) -> str:
        """返回所有配置（含未打开的），带 tabIndex / isActive / isRunning。"""
        try:
            from kaa.config import manager
            all_names = manager.list_profiles()
            open_map = {t.config_name: i for i, t in enumerate(self._tabs)}
            running_map = {t.config_name: t.is_running for t in self._tabs}
            return json.dumps([
                {
                    'configName': name,
                    'tabIndex': open_map.get(name, -1),
                    'isActive': open_map.get(name, -1) == self._active_index and name in open_map,
                    'isRunning': running_map.get(name, False),
                }
                for name in all_names
            ], ensure_ascii=False)
        except Exception:
            return '[]'

    @Slot(result=str)
    def tabsJson(self) -> str:
        return json.dumps([
            {'configName': t.config_name, 'index': i, 'isActive': i == self._active_index}
            for i, t in enumerate(self._tabs)
        ], ensure_ascii=False)

    @Slot(result=str)
    def availableConfigsJson(self) -> str:
        """返回未在任何 tab 中打开的配置列表。"""
        try:
            from kaa.config import manager
            all_configs = manager.list_profiles()
            open_names = {t.config_name for t in self._tabs}
            available = [n for n in all_configs if n not in open_names]
            return json.dumps(available, ensure_ascii=False)
        except Exception:
            return '[]'

    # ── QML Properties ───────────────────────────────────────────────

    def _get_active_tab_index(self) -> int:
        return self._active_index

    def _get_active_config_name(self) -> str:
        e = self._active_entry()
        return e.config_name if e else ''

    def _get_any_running(self) -> bool:
        return any(t.is_running for t in self._tabs)

    def _get_batch_mode(self) -> str:
        return self._batch_mode

    def _get_stop_all_busy(self) -> bool:
        return self._stop_all_busy

    def _get_active_settings_controller(self):
        return self.settingsCtrlAt(self._active_index)

    def _get_active_produce_controller(self):
        return self.produceCtrlAt(self._active_index)

    activeTabIndex = Property(int, _get_active_tab_index, notify=activeTabChanged)
    activeConfigName = Property(str, _get_active_config_name, notify=activeTabChanged)
    anyRunning = Property(bool, _get_any_running, notify=tabsChanged)
    batchMode = Property(str, _get_batch_mode, notify=batchModeChanged)
    stopAllBusy = Property(bool, _get_stop_all_busy, notify=batchModeChanged)
    activeSettingsController = Property(QObject, _get_active_settings_controller, notify=activeTabChanged)
    activeProduceController = Property(QObject, _get_active_produce_controller, notify=activeTabChanged)

    # ── Controller 惰性创建 Slots ────────────────────────────────────

    @Slot(int)
    def requestCapturePage(self, page_index: int) -> None:
        """Emit capturePageRequested to navigate TabContent to a specific page (capture mode)."""
        self.capturePageRequested.emit(page_index)

    @Slot(int, result=QObject)
    def runCtrlAt(self, index: int) -> RunController | None:
        """返回指定 index 的 tab 的 RunController（惰性创建）。"""
        if 0 <= index < len(self._tabs):
            entry = self._tabs[index]
            if entry.run_ctrl is None:
                entry.run_ctrl = RunController(entry.session)
            return entry.run_ctrl
        return None

    @Slot(int, result=QObject)
    def settingsCtrlAt(self, index: int) -> SettingsController | None:
        """返回指定 index 的 tab 的 SettingsController（惰性创建）。"""
        if 0 <= index < len(self._tabs):
            entry = self._tabs[index]
            if entry.settings_ctrl is None:
                entry.settings_ctrl = SettingsController(entry.session)
            return entry.settings_ctrl
        return None

    @Slot(int, result=QObject)
    def progressBridgeAt(self, index: int) -> ProgressBridge | None:
        """返回指定 index 的 tab 的 ProgressBridge（惰性创建）。"""
        if 0 <= index < len(self._tabs):
            entry = self._tabs[index]
            if entry.progress_bridge is None:
                entry.progress_bridge = ProgressBridge(entry.session)
            return entry.progress_bridge
        return None

    @Slot(int, result=QObject)
    def logBridgeAt(self, index: int) -> LogBridge | None:
        """返回指定 index 的 tab 的 LogBridge（惰性创建）。"""
        if 0 <= index < len(self._tabs):
            entry = self._tabs[index]
            if entry.log_bridge is None:
                entry.log_bridge = LogBridge()
                entry.log_bridge.install()
            return entry.log_bridge
        return None

    @Slot(int, result=QObject)
    def produceCtrlAt(self, index: int) -> ProduceController | None:
        """返回指定 index 的 tab 的 ProduceController（惰性创建）。"""
        if 0 <= index < len(self._tabs):
            entry = self._tabs[index]
            if entry.produce_ctrl is None:
                entry.produce_ctrl = ProduceController(entry.session)
            return entry.produce_ctrl
        return None

    @Slot(int, result=QObject)
    def updateCtrlAt(self, index: int) -> UpdateController | None:
        """返回指定 index 的 tab 的 UpdateController（惰性创建）。"""
        if 0 <= index < len(self._tabs):
            entry = self._tabs[index]
            if entry.update_ctrl is None:
                entry.update_ctrl = UpdateController(entry.session)
            return entry.update_ctrl
        return None

    @Slot(int, result=QObject)
    def feedbackCtrlAt(self, index: int) -> FeedbackController | None:
        """返回指定 index 的 tab 的 FeedbackController（惰性创建）。"""
        if 0 <= index < len(self._tabs):
            entry = self._tabs[index]
            if entry.feedback_ctrl is None:
                entry.feedback_ctrl = FeedbackController(entry.session)
            return entry.feedback_ctrl
        return None
