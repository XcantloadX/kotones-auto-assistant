"""Tests for kaa.config.scheduler — 纯函数 compute_next_run / should_fire。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from kaa.config.scheduler import (
    ScheduleEntry,
    ScheduleTrigger,
    SchedulerConfig,
    compute_next_run,
    should_fire,
    format_trigger_desc,
)


# ── compute_next_run ──────────────────────────────────────────────

class TestComputeNextRun:
    def test_daily_future(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='14:30'))
        now = datetime(2026, 1, 15, 10, 0)
        result = compute_next_run(entry, now)
        assert result == datetime(2026, 1, 15, 14, 30)

    def test_daily_past_today(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='04:00'))
        now = datetime(2026, 1, 15, 10, 0)
        result = compute_next_run(entry, now)
        assert result == datetime(2026, 1, 16, 4, 0)

    def test_daily_exactly_now(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='10:00'))
        now = datetime(2026, 1, 15, 10, 0)
        result = compute_next_run(entry, now)
        # planned <= now → next day
        assert result == datetime(2026, 1, 16, 10, 0)

    def test_weekly_next_weekday(self):
        # 2026-01-15 is Thursday (weekday=3)
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='weekly', time='09:00', weekdays=[0, 2, 4]))
        now = datetime(2026, 1, 15, 8, 0)
        result = compute_next_run(entry, now)
        # Next matching: Friday (4) = 2026-01-16
        assert result == datetime(2026, 1, 16, 9, 0)

    def test_weekly_wrap_around(self):
        # 2026-01-15 is Thursday (weekday=3), only weekday=0 (Mon) enabled
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='weekly', time='09:00', weekdays=[0]))
        now = datetime(2026, 1, 15, 10, 0)
        result = compute_next_run(entry, now)
        # Next Monday = 2026-01-19
        assert result == datetime(2026, 1, 19, 9, 0)

    def test_weekly_no_weekdays_fallback_daily(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='weekly', time='12:00', weekdays=[]))
        now = datetime(2026, 1, 15, 10, 0)
        result = compute_next_run(entry, now)
        assert result == datetime(2026, 1, 15, 12, 0)

    def test_midnight_boundary(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='00:00'))
        now = datetime(2026, 1, 15, 23, 59)
        result = compute_next_run(entry, now)
        assert result == datetime(2026, 1, 16, 0, 0)


# ── should_fire ───────────────────────────────────────────────────

class TestShouldFire:
    def test_disabled_never_fires(self):
        entry = ScheduleEntry(enabled=False)
        assert should_fire(entry, datetime.now()) is False

    def test_fires_within_window(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='10:00'))
        now = datetime(2026, 1, 16, 10, 1, 30)  # 1.5 min after planned
        assert should_fire(entry, now) is True

    def test_no_fire_outside_window(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='10:00'))
        now = datetime(2026, 1, 16, 10, 5)  # 5 min after planned
        assert should_fire(entry, now) is False

    def test_no_fire_before_planned(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='10:00'))
        now = datetime(2026, 1, 15, 9, 59)
        assert should_fire(entry, now) is False

    def test_last_run_blocks_duplicate(self):
        entry = ScheduleEntry(
            trigger=ScheduleTrigger(type='daily', time='10:00'),
            last_run=datetime(2026, 1, 16, 10, 0, 10).isoformat(),
        )
        now = datetime(2026, 1, 16, 10, 1)
        assert should_fire(entry, now) is False

    def test_last_run_older_allows_fire(self):
        entry = ScheduleEntry(
            trigger=ScheduleTrigger(type='daily', time='10:00'),
            last_run=datetime(2026, 1, 15, 10, 0, 10).isoformat(),
        )
        now = datetime(2026, 1, 16, 10, 1)
        assert should_fire(entry, now) is True

    def test_custom_window(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='10:00'))
        now = datetime(2026, 1, 16, 10, 4)  # 4 min after planned
        # Default window (2 min) → False
        assert should_fire(entry, now) is False
        # Extended window (5 min) → True
        assert should_fire(entry, now, window_minutes=5) is True

    def test_sleep_wakeup_skip(self):
        """Simulate: planned at 10:00, now is 10:30 (e.g. after sleep)."""
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='10:00'))
        now = datetime(2026, 1, 16, 10, 30)
        assert should_fire(entry, now) is False


# ── format_trigger_desc ───────────────────────────────────────────

class TestFormatTriggerDesc:
    def test_daily(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='daily', time='04:00'))
        assert format_trigger_desc(entry) == '每天 04:00'

    def test_weekly_single(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='weekly', time='12:30', weekdays=[0]))
        assert format_trigger_desc(entry) == '周一 12:30'

    def test_weekly_multiple(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='weekly', time='09:00', weekdays=[0, 4, 6]))
        assert format_trigger_desc(entry) == '周一、周五、周日 09:00'

    def test_weekly_no_weekdays(self):
        entry = ScheduleEntry(trigger=ScheduleTrigger(type='weekly', time='08:00', weekdays=[]))
        assert format_trigger_desc(entry) == '每天 08:00'


# ── SchedulerConfig model ─────────────────────────────────────────

class TestSchedulerConfig:
    def test_default_version(self):
        config = SchedulerConfig()
        assert config.version == 1
        assert config.entries == []

    def test_entry_auto_id(self):
        entry = ScheduleEntry()
        assert entry.id != ''

    def test_roundtrip(self):
        config = SchedulerConfig(entries=[
            ScheduleEntry(name='test', profile_name='default', trigger=ScheduleTrigger(type='daily', time='04:00')),
        ])
        data = config.model_dump()
        restored = SchedulerConfig.model_validate(data)
        assert len(restored.entries) == 1
        assert restored.entries[0].name == 'test'
