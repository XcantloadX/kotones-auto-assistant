"""SchedulerService — 定时任务调度服务。

QTimer 每 30s tick，逐条检查 should_fire，dispatch 执行。
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from kaa.config import manager as config_manager
from kaa.config.scheduler import (
    SchedulerConfig,
    ScheduleEntry,
    should_fire,
    compute_next_run,
    format_trigger_desc,
)

if TYPE_CHECKING:
    from kaa.application.ui.controllers.tab_manager import TabManager

logger = logging.getLogger(__name__)


class SchedulerService(QObject):
    """定时任务调度服务（主线程 QTimer tick）。"""

    entryTriggered = Signal(str, str)   # entry_id, profile_name
    entryFinished = Signal(str, str)    # entry_id, profile_name
    entrySkipped = Signal(str, str, str)  # entry_id, profile_name, reason
    entryFailed = Signal(str, str, str)  # entry_id, profile_name, error
    configChanged = Signal()

    def __init__(
        self,
        tab_manager: TabManager,
        clock: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._tab_manager = tab_manager
        self._clock = clock  # 可注入时钟（测试用），默认 datetime.now
        self._busy: set[str] = set()  # 正在执行的 profile_name 集合
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._invalid_entries: list[str] = []  # profile 不存在的条目 id

    # ── 公开方法 ──────────────────────────────────────────────────────

    @Slot()
    def start(self) -> None:
        """启动定时器（30s 间隔）。

        作为 Slot 以便通过 ``QMetaObject.invokeMethod`` 从后台线程以
        QueuedConnection 投递到主线程执行，避免跨线程启动 QTimer。
        """
        self._validate_entries()
        self._timer.start(30_000)
        logger.info("SchedulerService started")

    def stop(self) -> None:
        """停止定时器。"""
        self._timer.stop()
        logger.info("SchedulerService stopped")

    def isProfileBusyByScheduler(self, profile_name: str) -> bool:
        """检查 profile 是否正在被调度器占用。"""
        return profile_name in self._busy

    # ── 内部 ──────────────────────────────────────────────────────────

    def _now(self) -> datetime:
        if self._clock is not None and hasattr(self._clock, 'now'):
            return self._clock.now()
        return datetime.now()

    def _validate_entries(self) -> None:
        """校验 entries 中的 profile_name 是否存在。"""
        config = config_manager.read_scheduler()
        valid_profiles = set(config_manager.list_profiles())
        self._invalid_entries = [
            e.id for e in config.entries
            if e.profile_name not in valid_profiles
        ]

    def _tick(self) -> None:
        """主循环 tick（主线程 QTimer 回调）。"""
        now = self._now()
        config = config_manager.read_scheduler()

        for entry in config.entries:
            if not entry.enabled:
                continue
            if entry.id in self._invalid_entries:
                continue
            if not should_fire(entry, now):
                continue

            # 同 profile 忙 → 跳过
            if entry.skip_if_running and self._tab_manager.isTabOpen(entry.profile_name):
                ts = None
                for i in range(len(self._tab_manager._tabs)):
                    e = self._tab_manager._tabs[i]
                    if e.config_name == entry.profile_name:
                        ts = e.session.task_service
                        break
                if ts is not None and ts.is_running():
                    self.entrySkipped.emit(entry.id, entry.profile_name, '任务运行中')
                    continue

            # 调度器自身忙 → 跳过
            if entry.profile_name in self._busy:
                self.entrySkipped.emit(entry.id, entry.profile_name, '调度器忙碌')
                continue

            # dispatch
            self._dispatch(entry)

    def _dispatch(self, entry: ScheduleEntry) -> None:
        """在后台线程执行 entry。"""
        self._busy.add(entry.profile_name)
        self.entryTriggered.emit(entry.id, entry.profile_name)

        def _run() -> None:
            try:
                session = None
                tab_manager = self._tab_manager

                # 复用已打开的 tab session
                tab_entry = None
                for t in tab_manager._tabs:
                    if t.config_name == entry.profile_name:
                        tab_entry = t
                        break

                if tab_entry is not None:
                    session = tab_entry.session
                else:
                    # 创建临时 session
                    from kaa.application.ui.kaa_session import KaaSession
                    session = KaaSession(entry.profile_name)
                    session.initialize()

                ts = session.task_service
                if ts is None:
                    raise RuntimeError(f"No task_service for profile '{entry.profile_name}'")

                ts.start_all_tasks()
                # 等待任务完成
                while session.is_running:
                    time.sleep(0.5)

                # 写回 last_run
                self._update_last_run(entry)

                if tab_entry is None and session is not None:
                    session.destroy()

                self.entryFinished.emit(entry.id, entry.profile_name)
            except Exception as exc:
                logger.exception("Scheduler dispatch failed for '%s'", entry.profile_name)
                self.entryFailed.emit(entry.id, entry.profile_name, str(exc))
            finally:
                self._busy.discard(entry.profile_name)

        threading.Thread(target=_run, daemon=True).start()

    def _update_last_run(self, entry: ScheduleEntry) -> None:
        """更新 entry 的 last_run 并写盘。"""
        config = config_manager.read_scheduler()
        for e in config.entries:
            if e.id == entry.id:
                e.last_run = self._now().isoformat()
                break
        config_manager.write_scheduler(config)
        self.configChanged.emit()
