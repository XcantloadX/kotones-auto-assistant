"""定时任务调度配置。

独立于 profile schema，存储在 conf/_scheduler.json。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel


class ScheduleTrigger(BaseModel):
    """触发条件。"""
    type: Literal['daily', 'weekly'] = 'daily'
    time: str = '04:00'  # HH:MM
    weekdays: list[int] = []  # 0=周一 … 6=周日，daily 时忽略


class ScheduleEntry(BaseModel):
    """单条定时任务条目。"""
    id: str = ''
    enabled: bool = True
    name: str = ''
    profile_name: str = ''
    trigger: ScheduleTrigger = ScheduleTrigger()
    last_run: str | None = None  # ISO 格式时间戳
    skip_if_running: bool = True  # v1 固定 True，字段预留

    def model_post_init(self, __context: object) -> None:
        if not self.id:
            self.id = str(uuid4())


class SchedulerConfig(BaseModel):
    """定时任务调度配置根模型。"""
    version: int = 1
    entries: list[ScheduleEntry] = []


# ── 纯函数 ──────────────────────────────────────────────────────────

_WEEKDAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']


def _parse_time(time_str: str) -> tuple[int, int]:
    """解析 HH:MM 为 (hour, minute)。"""
    parts = time_str.split(':')
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {time_str!r}, expected 'HH:MM'")
    return int(parts[0]), int(parts[1])


def compute_next_run(entry: ScheduleEntry, now: datetime) -> datetime:
    """计算 entry 的下一个触发时刻（不含 last_run 去重）。"""
    hour, minute = _parse_time(entry.trigger.time)

    if entry.trigger.type == 'daily':
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    # weekly: 找最近的匹配 weekday
    target_weekdays = set(entry.trigger.weekdays)
    if not target_weekdays:
        # 无指定星期等同每天
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    for _ in range(7):
        if candidate.weekday() in target_weekdays and candidate > now:
            return candidate
        candidate += timedelta(days=1)

    # 理论上不会到这里
    return candidate + timedelta(days=1)


def _compute_current_planned(entry: ScheduleEntry, now: datetime) -> datetime:
    """计算当前周期的计划触发时刻（最近一次已过或正在的时刻）。"""
    hour, minute = _parse_time(entry.trigger.time)

    if entry.trigger.type == 'daily':
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > now:
            candidate -= timedelta(days=1)
        return candidate

    # weekly: 从今天往前找最近的匹配 weekday
    target_weekdays = set(entry.trigger.weekdays)
    if not target_weekdays:
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > now:
            candidate -= timedelta(days=1)
        return candidate

    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    for _ in range(7):
        if candidate.weekday() in target_weekdays and candidate <= now:
            return candidate
        candidate -= timedelta(days=1)

    return candidate


def should_fire(entry: ScheduleEntry, now: datetime, window_minutes: float = 2) -> bool:
    """判断 entry 是否应在当前时刻触发。

    条件：
    1. entry.enabled
    2. last_run < 计划时刻 ≤ now
    3. now - 计划时刻 ≤ window_minutes（防止重复触发和补跑）
    """
    if not entry.enabled:
        return False

    planned = _compute_current_planned(entry, now)

    # 条件 2: 计划时刻必须已过或正好
    if planned > now:
        return False

    # 条件 3: 不能超出触发窗口（防止休眠唤醒后的补跑）
    if (now - planned).total_seconds() > window_minutes * 60:
        return False

    # 条件 1: last_run 必须早于本次计划时刻
    if entry.last_run is not None:
        try:
            last = datetime.fromisoformat(entry.last_run)
            if last >= planned:
                return False
        except ValueError:
            pass  # last_run 格式异常，视为未执行过

    return True


def format_trigger_desc(entry: ScheduleEntry) -> str:
    """格式化触发描述，如 '每天 04:00' / '周一、周五 12:30'。"""
    hour, minute = _parse_time(entry.trigger.time)
    time_str = f'{hour:02d}:{minute:02d}'

    if entry.trigger.type == 'daily':
        return f'每天 {time_str}'

    weekdays = sorted(entry.trigger.weekdays)
    if not weekdays:
        return f'每天 {time_str}'

    names = [_WEEKDAY_NAMES[d] for d in weekdays if 0 <= d <= 6]
    return f'{"、".join(names)} {time_str}'
