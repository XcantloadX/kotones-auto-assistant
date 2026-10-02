"""Tests for TaskService blocking 运行结局 — RunOutcome / raise_if_failed / join。"""
from __future__ import annotations

import dataclasses
import threading
import time
import types
from typing import Any, cast

import pytest

from kaa.application.services import task_service as ts_mod
from kaa.application.services.task_service import RunOutcome, TaskService
from kaa.main.kaa import Kaa
from kotonebot.core.bot import BotStopReason


class _FakeEvent:
    def __init__(self) -> None:
        self.handlers: list = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


def _make_service() -> TaskService:
    kaa = types.SimpleNamespace(
        events=types.SimpleNamespace(stopped=_FakeEvent(), task_status_changed=_FakeEvent())
    )
    # SimpleNamespace 不是 Kaa：cast 标明此处刻意用替身，不做 silent Any 传递。
    return TaskService(cast(Kaa, kaa))


# ── raise_if_failed 政策 ──────────────────────────────────────────

class TestRaiseIfFailed:
    def test_completed_silent(self):
        RunOutcome(reason=BotStopReason.COMPLETED).raise_if_failed()

    def test_user_request_silent(self):
        RunOutcome(reason=BotStopReason.USER_REQUEST).raise_if_failed()

    def test_error_reraises_same_object(self):
        exc = ValueError("boom")
        outcome = RunOutcome(reason=BotStopReason.ERROR, exception=exc)
        with pytest.raises(ValueError) as exc_info:
            outcome.raise_if_failed()
        assert exc_info.value is exc

    def test_error_without_exception_silent(self):
        # ERROR 但无明确异常：不误抛，排查靠日志与返回值。
        RunOutcome(reason=BotStopReason.ERROR, exception=None).raise_if_failed()


# ── 默认值与不可变 ────────────────────────────────────────────────

class TestOutcomeShape:
    def test_timed_out_defaults_false(self):
        assert RunOutcome(reason=BotStopReason.COMPLETED).timed_out is False

    def test_frozen(self):
        outcome = RunOutcome(reason=BotStopReason.COMPLETED)
        with pytest.raises(dataclasses.FrozenInstanceError):
            outcome.reason = BotStopReason.ERROR  # type: ignore[misc]


# ── _wait_blocking 返回 RunOutcome ────────────────────────────────

class TestWaitBlocking:
    def test_returns_outcome_snapshot(self):
        ts = _make_service()
        ts._last_stop_reason = BotStopReason.COMPLETED
        ts._last_exception = None
        thread = threading.Thread(target=lambda: None)
        thread.start()
        thread.join()
        outcome = ts._wait_blocking(thread)
        assert isinstance(outcome, RunOutcome)
        assert outcome.reason == BotStopReason.COMPLETED
        assert outcome.exception is None

    def test_joins_slow_cleanup(self):
        # 后台收尾慢（1s）：必须等满才返回。
        ts = _make_service()
        ts._last_stop_reason = BotStopReason.COMPLETED
        ts._last_exception = None
        thread = threading.Thread(target=lambda: time.sleep(1.0))
        thread.start()
        start = time.monotonic()
        ts._wait_blocking(thread)
        assert not thread.is_alive()
        assert time.monotonic() - start >= 0.9

    def test_hang_join_raises(self, monkeypatch):
        # 后台 hang：join 超时 fast-fail。
        monkeypatch.setattr(ts_mod, "_JOIN_TIMEOUT_SEC", 0.5)
        ts = _make_service()
        ts._last_stop_reason = BotStopReason.COMPLETED
        ts._last_exception = None
        thread = threading.Thread(target=lambda: time.sleep(30), daemon=True)
        thread.start()
        with pytest.raises(RuntimeError, match="did not exit within"):
            ts._wait_blocking(thread)

    def test_missing_stop_record_fast_fail(self):
        ts = _make_service()
        thread = threading.Thread(target=lambda: None)
        thread.start()
        thread.join()
        with pytest.raises(RuntimeError, match="no stop reason"):
            ts._wait_blocking(thread)


# ── 启动句柄缺失 fast-fail ────────────────────────────────────────

class TestBlockingStartGuards:
    def test_run_all_missing_handle(self):
        # start_all() 返回 None（句柄丢失的极端竞态）：
        # is_running 为 True 但 _run_status 缺失，必须 fast-fail。
        ts = _make_service()
        # 刻意破坏 start_all 契约（返回 None）以触发句柄缺失守卫，
        # 经 Any 赋值，类型检查器不为测试替身误报。
        cast(Any, ts._kaa).start_all = lambda: None
        with pytest.raises(RuntimeError, match="run status handle is missing"):
            ts.run_all_blocking()
