"""TabManager — 管理多 profile tab 生命周期r。

每个 tab 对应一个 ProfileRunner（内含 Kaa + KaaFacade + gr.Blocks）。
TabManager 负责 tab 的创建/关闭/激活/批量运行，并通过 Qt Signals 通知 QML。
"""
import json
import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Property, Signal, Slot

from kaa.application.ui.profile_runner import ProfileRunner

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


@dataclass
class _TabEntry:
    runner: ProfileRunner
    mount_path: str = ""

    @property
    def config_name(self) -> str:
        return self.runner.profile_name

    @property
    def is_running(self) -> bool:
        return self.runner.is_running


class TabManager(QObject):
    """管理多 profile tab 生命周期，并向 QML 暴露 tab 列表和状态。"""

    tabsChanged = Signal()
    activeTabChanged = Signal()
    anyBusyChanged = Signal()
    batchModeChanged = Signal()
    closeTabBlocked = Signal(str)          # reason
    readyToCloseTab = Signal(int)          # index
    tabOpenFailed = Signal(str)            # error
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, server_app: 'FastAPI', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server_app = server_app
        self._tabs: list[_TabEntry] = []
        self._active_index: int = 0
        self._batch_mode: str = ''          # '' | 'sequential' | 'parallel'
        self._stop_all_busy: bool = False
        self._seq_cancel: threading.Event | None = None
        self._mount_counter: int = 0
        self._lock = threading.Lock()

    # ── 内部工具 ──────────────────────────────────────────────────────

    def _next_mount_path(self) -> str:
        with self._lock:
            self._mount_counter += 1
            return f"/p{self._mount_counter}"

    def _create_entry(self, config_name: str) -> _TabEntry:
        mount_path = self._next_mount_path()
        runner = ProfileRunner(
            profile_name=config_name,
            mount_path=mount_path,
            server_app=self._server_app,
        )
        # mount 在后台线程执行，避免阻塞 UI
        t = threading.Thread(target=runner.mount, daemon=True)
        t.start()
        t.join(timeout=30)
        return _TabEntry(runner=runner, mount_path=mount_path)

    def _destroy_entry(self, entry: _TabEntry) -> None:
        try:
            entry.runner.unmount()
        except Exception:
            logger.exception("Failed to unmount runner for '%s'", entry.config_name)

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

    def restore_tabs(self) -> None:
        """从 shared config 恢复已保存的 tabs，在后台线程中调用。

        直接调用 ``runner.mount()``（不自启线程，因为调用方已在后台线程）。
        """
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
                    mount_path = self._next_mount_path()
                    runner = ProfileRunner(name, mount_path, self._server_app)
                    runner.mount()
                    entries.append(_TabEntry(runner=runner, mount_path=mount_path))
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

    def _get_server_app(self) -> object:
        return self._server_app

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
                try:
                    entry.runner.run_tasks()
                except Exception:
                    logger.exception("Sequential run failed for '%s'", entry.config_name)

            if not cancel.is_set():
                self._batch_mode = ''
                self.batchModeChanged.emit()
                self.anyBusyChanged.emit()

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
                target=entry.runner.run_tasks,
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
                self.anyBusyChanged.emit()

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
            kaa = entry.runner.kaa
            assert kaa is not None, f"Tab '{entry.config_name}' has no Kaa instance (mount may have failed)"
            try:
                kaa.stop()
            except Exception:
                logger.exception("Failed to stop '%s'", entry.config_name)

        self._batch_mode = ''
        self._stop_all_busy = False
        self.batchModeChanged.emit()
        self.anyBusyChanged.emit()

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

    def _get_any_busy(self) -> bool:
        return any(t.is_running for t in self._tabs)

    def _get_batch_mode(self) -> str:
        return self._batch_mode

    def _get_stop_all_busy(self) -> bool:
        return self._stop_all_busy

    def _get_url_for_index(self, index: int) -> str:
        if 0 <= index < len(self._tabs):
            entry = self._tabs[index]
            return f"http://127.0.0.1:7860{entry.mount_path}"
        return ""

    activeTabIndex = Property(int, _get_active_tab_index, notify=activeTabChanged)
    activeConfigName = Property(str, _get_active_config_name, notify=activeTabChanged)
    anyRunning = Property(bool, _get_any_running, notify=tabsChanged)
    anyBusy = Property(bool, _get_any_busy, notify=anyBusyChanged)
    batchMode = Property(str, _get_batch_mode, notify=batchModeChanged)
    stopAllBusy = Property(bool, _get_stop_all_busy, notify=batchModeChanged)

    @Slot(int, result=str)
    def gradioUrlAt(self, index: int) -> str:
        """返回指定 index 的 tab 的 Gradio URL。"""
        return self._get_url_for_index(index)

    @property
    def serverApp(self) -> object:
        return self._server_app
