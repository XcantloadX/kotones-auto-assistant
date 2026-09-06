"""TabManager — 管理多 Tab（ShellSession）生命周期。

每个 Tab 对应一个下游 :class:`ShellSession`。TabManager 负责 Tab 的
创建/关闭/激活/批量运行、Profile CRUD 委托与持久化，并通过 Qt Signals 通知 QML。
"""
import json
import logging
import threading
import time
from dataclasses import dataclass
from collections.abc import Callable

from PySide6.QtCore import QObject, Property, Signal, Slot

from euishell.controllers.tab_controller import TabController
from euishell.exceptions import ProfileError
from euishell.session import OpenTabsState, ProfileProvider, ShellSession, TabPersistence

logger = logging.getLogger(__name__)


@dataclass
class _TabEntry:
    """单个打开 Tab 的运行时状态。"""

    session: ShellSession
    tab_controller: TabController | None = None
    """惰性创建（首次被 QML 访问时）。"""

    @property
    def profile_id(self) -> str:
        return self.session.profile_id

    @property
    def is_running(self) -> bool:
        return self.session.is_running


class TabManager(QObject):
    """管理多 Tab 生命周期，并向 QML 暴露 Tab 列表和状态。"""

    tabsChanged = Signal()
    activeTabChanged = Signal()
    batchModeChanged = Signal()
    closeTabBlocked = Signal(str)
    readyToCloseTab = Signal(int)
    tabOpenFailed = Signal(str)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    capturePageRequested = Signal(int)

    def __init__(
        self,
        session_factory: Callable[[str], ShellSession],
        persistence: TabPersistence,
        profile_provider: ProfileProvider,
        parent: QObject | None = None,
    ) -> None:
        """
        :param session_factory: 下游会话工厂（profile_id → ShellSession）
        :param persistence: Tab 持久化后端
        :param profile_provider: profile 管理后端
        :param parent: Qt 父对象
        """
        super().__init__(parent)
        self._session_factory = session_factory
        self._persistence = persistence
        self._profile_provider = profile_provider
        self._tabs: list[_TabEntry] = []
        self._active_index: int = 0
        self._batch_mode: str = ''
        self._stop_all_busy: bool = False
        self._seq_cancel: threading.Event | None = None
        self._lock = threading.Lock()
        self._tab_open_guard: Callable[[str], bool] | None = None
        self._profile_remove_handler: Callable[[str], None] | None = None
        self._profile_rename_handler: Callable[[str, str], None] | None = None

    def set_tab_open_guard(self, check: Callable[[str], bool]) -> None:
        """注册 Tab 打开守卫（返回 True 表示该 profile 暂不可打开）。

        :param check: 守卫回调
        """
        self._tab_open_guard = check

    def set_profile_handlers(
        self,
        on_remove: Callable[[str], None],
        on_rename: Callable[[str, str], None],
    ) -> None:
        """注册 profile 删除/重命名生命周期回调。

        :param on_remove: profile 被删除后回调
        :param on_rename: profile 被重命名后回调 (old, new)
        """
        self._profile_remove_handler = on_remove
        self._profile_rename_handler = on_rename

    # ── 内部工具 ──────────────────────────────────────────────────────

    def _create_entry(self, profile_id: str) -> _TabEntry:
        session = self._session_factory(profile_id)
        return _TabEntry(session=session)

    def _destroy_entry(self, entry: _TabEntry) -> None:
        try:
            if entry.tab_controller is not None:
                entry.tab_controller.destroy()
        except Exception:
            logger.exception("Failed to destroy tab controller for '%s'", entry.profile_id)
        try:
            entry.session.destroy()
        except Exception:
            logger.exception("Failed to destroy session for '%s'", entry.profile_id)

    def _save_tabs(self) -> None:
        try:
            active = self._active_entry()
            self._persistence.save_open_tabs(OpenTabsState(
                tab_ids=[t.profile_id for t in self._tabs],
                last_used=active.profile_id if active is not None else None,
            ))
        except Exception:
            logger.exception('Failed to save tab list')

    def _run_entry_tasks(self, entry: _TabEntry) -> None:
        """初始化 session 并启动所有任务，阻塞至完成。"""
        try:
            entry.session.initialize()
            control = entry.session.task_control()
            if control is None:
                return
            control.start()
            while entry.is_running:
                time.sleep(0.5)
        except Exception:
            logger.exception("Run tasks failed for '%s'", entry.profile_id)

    def restore_tabs(self) -> None:
        """从持久化后端恢复已保存的 tabs（在后台线程中调用）。"""
        try:
            state = self._persistence.load_open_tabs()
            available = set(self._profile_provider.list_profiles())

            names = [n for n in state.tab_ids if n in available]
            entries: list[_TabEntry] = []
            for name in names:
                try:
                    session = self._session_factory(name)
                    session.initialize()
                    entries.append(_TabEntry(session=session))
                except Exception:
                    logger.exception('Failed to restore tab: %s', name)

            with self._lock:
                self._tabs = entries
                if state.last_used and any(t.profile_id == state.last_used for t in self._tabs):
                    self._active_index = next(
                        i for i, t in enumerate(self._tabs) if t.profile_id == state.last_used
                    )
                else:
                    self._active_index = 0

            self.tabsChanged.emit()
            self.activeTabChanged.emit()
        except Exception:
            logger.exception('Failed to restore tabs')

    def _active_entry(self) -> _TabEntry | None:
        if 0 <= self._active_index < len(self._tabs):
            return self._tabs[self._active_index]
        return None

    def get_active_task_control(self):
        """获取当前活跃 Tab 的 TaskControl，无活跃 Tab 时返回 None。"""
        entry = self._active_entry()
        if entry is None:
            return None
        return entry.session.task_control()

    # ── QML Slots ─────────────────────────────────────────────────────

    @Slot(str)
    def openTab(self, profile_id: str) -> None:
        """在新 Tab 中打开指定 profile。同一 profile 不能重复打开。

        :param profile_id: profile 标识。
        """
        if any(t.profile_id == profile_id for t in self._tabs):
            self.operationFailed.emit(f'配置 "{profile_id}" 已在某个 Tab 中打开')
            return
        if self._tab_open_guard is not None and self._tab_open_guard(profile_id):
            self.operationFailed.emit(f'配置 "{profile_id}" 当前不可打开')
            return
        try:
            entry = self._create_entry(profile_id)
            self._tabs.append(entry)
            self._active_index = len(self._tabs) - 1
            self._save_tabs()
            self.tabsChanged.emit()
            self.activeTabChanged.emit()

            # 后台线程初始化 session，完成后通知 QML 刷新
            def _init_and_notify():
                try:
                    entry.session.initialize()
                except Exception:
                    logger.exception('Failed to initialize tab: %s', profile_id)
                    self.tabOpenFailed.emit(str(profile_id))
                    return
                self.tabsChanged.emit()
            threading.Thread(target=_init_and_notify, daemon=True).start()
        except Exception as e:
            logger.exception('Failed to open tab: %s', profile_id)
            self.tabOpenFailed.emit(str(e))

    @Slot(int)
    def setActiveTab(self, index: int) -> None:
        """激活指定 Tab。

        :param index: Tab 下标。
        """
        if index < 0 or index >= len(self._tabs):
            return
        if index == self._active_index:
            return
        self._active_index = index
        self._save_tabs()
        self.activeTabChanged.emit()

    @Slot(int)
    def requestCloseTab(self, index: int) -> None:
        """请求关闭 Tab。若运行中则阻断；否则 emit readyToCloseTab。

        :param index: Tab 下标。
        """
        if index < 0 or index >= len(self._tabs):
            return
        entry = self._tabs[index]
        if entry.is_running:
            self.closeTabBlocked.emit('请先停止正在运行的任务')
            return
        self.readyToCloseTab.emit(index)

    @Slot(int)
    def closeTab(self, index: int) -> None:
        """无条件关闭 Tab。

        :param index: Tab 下标。
        """
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
    def closeTabForConfig(self, profile_id: str) -> bool:
        """Profile 删除前调用：关闭该 profile 的 Tab。

        :param profile_id: profile 标识。
        :returns: 是否成功关闭（运行中或最后一个 Tab 时返回 False）。
        """
        for i, entry in enumerate(self._tabs):
            if entry.profile_id == profile_id:
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
    def isTabOpen(self, profile_id: str) -> bool:
        """指定 profile 是否已有打开的 Tab。

        :param profile_id: profile 标识。
        """
        return any(t.profile_id == profile_id for t in self._tabs)

    @Slot(str, result=bool)
    def createProfile(self, name: str) -> bool:
        """创建新 profile 并打开对应 Tab。

        :param name: profile 名称。
        """
        try:
            self._profile_provider.create(name)
            self.openTab(name)
            self.operationSucceeded.emit(f'已创建配置: {name}')
            return True
        except ProfileError as exc:
            self.operationFailed.emit(f'创建失败：{exc}')
            return False
        except Exception as exc:
            logger.exception('Failed to create profile: %s', name)
            self.operationFailed.emit(f'创建失败：{exc}')
            return False

    @Slot(str, str, result=bool)
    def renameProfile(self, old_name: str, new_name: str) -> bool:
        """重命名 profile。若该 profile 有打开的 Tab，先关闭再用新名重新打开。

        :param old_name: 旧名称。
        :param new_name: 新名称。
        """
        try:
            self._profile_provider.rename(old_name, new_name)
            was_open = self.isTabOpen(old_name)
            if was_open:
                for i, entry in enumerate(self._tabs):
                    if entry.profile_id == old_name:
                        self.closeTab(i)
                        break
                self.openTab(new_name)
            if self._profile_rename_handler is not None:
                self._profile_rename_handler(old_name, new_name)
            self.operationSucceeded.emit(f'已将配置重命名为: {new_name}')
            return True
        except ProfileError as exc:
            self.operationFailed.emit(f'重命名失败：{exc}')
            return False
        except Exception as exc:
            logger.exception('Failed to rename profile: %s -> %s', old_name, new_name)
            self.operationFailed.emit(f'重命名失败：{exc}')
            return False

    @Slot(str, result=bool)
    def deleteProfile(self, name: str) -> bool:
        """删除 profile。调用前应先通过 closeTabForConfig 关闭 Tab。

        :param name: profile 名称。
        """
        try:
            self._profile_provider.remove(name)
            if self._profile_remove_handler is not None:
                self._profile_remove_handler(name)
            self.operationSucceeded.emit(f'已删除配置: {name}')
            self.tabsChanged.emit()
            return True
        except ProfileError as exc:
            self.operationFailed.emit(f'删除失败：{exc}')
            return False
        except Exception as exc:
            logger.exception('Failed to delete profile: %s', name)
            self.operationFailed.emit(f'删除失败：{exc}')
            return False

    # ── 批量运行 ───────────────────────────────────────────────────────

    @Slot()
    def startAllSequential(self) -> None:
        """在后台线程中依次启动所有 Tab。"""
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
        """同时启动所有 Tab。"""
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
        """停止所有 Tab。"""
        if self._stop_all_busy:
            return
        self._stop_all_busy = True
        self.batchModeChanged.emit()

        # 取消连续执行循环
        if self._seq_cancel is not None:
            self._seq_cancel.set()

        for entry in self._tabs:
            control = entry.session.task_control()
            if control is None:
                logger.warning("Tab '%s' has no task control", entry.profile_id)
                continue
            try:
                control.stop()
            except Exception:
                logger.exception("Failed to stop '%s'", entry.profile_id)

        self._batch_mode = ''
        self._stop_all_busy = False
        self.batchModeChanged.emit()

    # ── JSON 序列化 ───────────────────────────────────────────────────

    @Slot(result=str)
    def allConfigsJson(self) -> str:
        """返回所有 profile（含未打开的），带 tabIndex / isActive / isRunning。"""
        try:
            all_names = self._profile_provider.list_profiles()
            open_map = {t.profile_id: i for i, t in enumerate(self._tabs)}
            running_map = {t.profile_id: t.is_running for t in self._tabs}
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
            logger.exception('Failed to build allConfigsJson')
            return '[]'

    @Slot(result=str)
    def tabsJson(self) -> str:
        """返回已打开 Tab 列表 JSON。"""
        return json.dumps([
            {'configName': t.profile_id, 'index': i, 'isActive': i == self._active_index}
            for i, t in enumerate(self._tabs)
        ], ensure_ascii=False)

    @Slot(result=str)
    def availableConfigsJson(self) -> str:
        """返回未在任何 Tab 中打开的 profile 列表 JSON。"""
        try:
            all_configs = self._profile_provider.list_profiles()
            open_names = {t.profile_id for t in self._tabs}
            available = [n for n in all_configs if n not in open_names]
            return json.dumps(available, ensure_ascii=False)
        except Exception:
            logger.exception('Failed to build availableConfigsJson')
            return '[]'

    # ── QML Properties ───────────────────────────────────────────────

    def _get_active_tab_index(self) -> int:
        return self._active_index

    def _get_active_profile_id(self) -> str:
        e = self._active_entry()
        return e.profile_id if e else ''

    def _get_any_running(self) -> bool:
        return any(t.is_running for t in self._tabs)

    def _get_batch_mode(self) -> str:
        return self._batch_mode

    def _get_stop_all_busy(self) -> bool:
        return self._stop_all_busy

    def _get_active_tab_controller(self) -> TabController | None:
        return self.tabControllerAt(self._active_index)

    activeTabIndex = Property(int, _get_active_tab_index, notify=activeTabChanged)
    activeProfileId = Property(str, _get_active_profile_id, notify=activeTabChanged)
    anyRunning = Property(bool, _get_any_running, notify=tabsChanged)
    batchMode = Property(str, _get_batch_mode, notify=batchModeChanged)
    stopAllBusy = Property(bool, _get_stop_all_busy, notify=batchModeChanged)
    activeTabController = Property(QObject, _get_active_tab_controller, notify=activeTabChanged)

    # ── Controller 惰性创建 Slots ────────────────────────────────────

    @Slot(int)
    def requestCapturePage(self, page_index: int) -> None:
        """请求活跃 Tab 导航到指定页面下标（捕获模式）。

        :param page_index: 页面下标。
        """
        self.capturePageRequested.emit(page_index)

    @Slot(int, result=QObject)
    def tabControllerAt(self, index: int) -> TabController | None:
        """返回指定 Tab 的 TabController（惰性创建）。

        :param index: Tab 下标。
        """
        if 0 <= index < len(self._tabs):
            entry = self._tabs[index]
            if entry.tab_controller is None:
                entry.tab_controller = TabController(entry.session, self)
            return entry.tab_controller
        return None
