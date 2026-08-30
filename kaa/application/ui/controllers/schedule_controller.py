"""ScheduleController — 定时任务管理 UI 桥接。

全局单例，注册为 QML 上下文属性。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from PySide6.QtCore import QObject, Property, Signal, Slot

from kaa.config import manager as config_manager
from kaa.config.scheduler import (
    ScheduleEntry,
    SchedulerConfig,
    format_trigger_desc,
    compute_next_run,
)

logger = logging.getLogger(__name__)


class ScheduleController(QObject):
    """定时任务管理控制器。"""

    entriesChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    # ── QML Properties ───────────────────────────────────────────────

    @Slot(result=str)
    def entriesJson(self) -> str:
        """返回所有条目的 JSON 数组。"""
        config = config_manager.read_scheduler()
        items = []
        for e in config.entries:
            items.append({
                'id': e.id,
                'enabled': e.enabled,
                'name': e.name,
                'profileName': e.profile_name,
                'triggerType': e.trigger.type,
                'triggerTime': e.trigger.time,
                'triggerWeekdays': e.trigger.weekdays,
                'triggerDesc': format_trigger_desc(e),
                'lastRun': e.last_run or '',
            })
        return json.dumps(items, ensure_ascii=False)

    @Slot(result=str)
    def nextRunJson(self) -> str:
        """返回最近的启用条目及下次触发时间描述（供 Overview 卡片）。"""
        config = config_manager.read_scheduler()
        now = datetime.now()
        enabled = [e for e in config.entries if e.enabled]
        if not enabled:
            return json.dumps({'hasEntries': False, 'nextRunDesc': '未设置'}, ensure_ascii=False)

        # 找最近的触发时刻
        entries_with_next = []
        for e in enabled:
            try:
                nxt = compute_next_run(e, now)
                entries_with_next.append((nxt, e))
            except Exception:
                continue

        if not entries_with_next:
            return json.dumps({'hasEntries': True, 'nextRunDesc': '无有效条目'}, ensure_ascii=False)

        entries_with_next.sort(key=lambda x: x[0])
        next_time, next_entry = entries_with_next[0]

        # 格式化相对时间
        delta = next_time - now
        total_minutes = int(delta.total_seconds() / 60)
        if total_minutes < 60:
            time_desc = f'{total_minutes} 分钟后'
        elif total_minutes < 1440:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            time_desc = f'{hours} 小时 {minutes} 分钟后' if minutes else f'{hours} 小时后'
        else:
            days = total_minutes // 1440
            time_desc = f'{days} 天后'

        return json.dumps({
            'hasEntries': True,
            'nextRunDesc': f'{time_desc}启动「{next_entry.name or next_entry.profile_name}」',
            'nextRunTime': format_trigger_desc(next_entry),
        }, ensure_ascii=False)

    @Slot(result=str)
    def profilesJson(self) -> str:
        """返回所有 profile 名称列表（供下拉选择）。"""
        return json.dumps(config_manager.list_profiles(), ensure_ascii=False)

    # ── CRUD Slots ───────────────────────────────────────────────────

    @Slot(str)
    def addEntry(self, json_str: str) -> None:
        """新增条目。json_str 包含 name, profileName, triggerType, triggerTime, triggerWeekdays。"""
        try:
            data = json.loads(json_str)
            config = config_manager.read_scheduler()
            trigger_data = data.get('trigger', {})
            entry = ScheduleEntry(
                name=data.get('name', ''),
                profile_name=data.get('profileName', ''),
                trigger={
                    'type': trigger_data.get('type', 'daily'),
                    'time': trigger_data.get('time', '04:00'),
                    'weekdays': trigger_data.get('weekdays', []),
                },
            )
            config.entries.append(entry)
            config_manager.write_scheduler(config)
            self.entriesChanged.emit()
            self.operationSucceeded.emit(f'已添加定时任务: {entry.name}')
        except Exception as exc:
            logger.exception("Failed to add schedule entry")
            self.operationFailed.emit(f'添加失败：{exc}')

    @Slot(str, str)
    def updateEntry(self, entry_id: str, json_str: str) -> None:
        """更新条目。"""
        try:
            data = json.loads(json_str)
            config = config_manager.read_scheduler()
            for e in config.entries:
                if e.id == entry_id:
                    if 'name' in data:
                        e.name = data['name']
                    if 'profileName' in data:
                        e.profile_name = data['profileName']
                    if 'trigger' in data:
                        t = data['trigger']
                        if 'type' in t:
                            e.trigger.type = t['type']
                        if 'time' in t:
                            e.trigger.time = t['time']
                        if 'weekdays' in t:
                            e.trigger.weekdays = t['weekdays']
                    if 'enabled' in data:
                        e.enabled = data['enabled']
                    break
            else:
                self.operationFailed.emit(f'条目 {entry_id} 不存在')
                return
            config_manager.write_scheduler(config)
            self.entriesChanged.emit()
            self.operationSucceeded.emit('定时任务已更新')
        except Exception as exc:
            logger.exception("Failed to update schedule entry")
            self.operationFailed.emit(f'更新失败：{exc}')

    @Slot(str)
    def removeEntry(self, entry_id: str) -> None:
        """删除条目。"""
        try:
            config = config_manager.read_scheduler()
            config.entries = [e for e in config.entries if e.id != entry_id]
            config_manager.write_scheduler(config)
            self.entriesChanged.emit()
            self.operationSucceeded.emit('定时任务已删除')
        except Exception as exc:
            logger.exception("Failed to remove schedule entry")
            self.operationFailed.emit(f'删除失败：{exc}')

    @Slot(str, bool)
    def setEntryEnabled(self, entry_id: str, enabled: bool) -> None:
        """启用/禁用条目。"""
        try:
            config = config_manager.read_scheduler()
            for e in config.entries:
                if e.id == entry_id:
                    e.enabled = enabled
                    break
            config_manager.write_scheduler(config)
            self.entriesChanged.emit()
        except Exception as exc:
            logger.exception("Failed to toggle schedule entry")
            self.operationFailed.emit(f'切换失败：{exc}')

    # ── Profile 生命周期挂钩 ─────────────────────────────────────────

    def handleProfileRemoved(self, name: str) -> None:
        """当配置被删除时调用，移除关联的调度条目。"""
        config = config_manager.read_scheduler()
        before = len(config.entries)
        config.entries = [e for e in config.entries if e.profile_name != name]
        if len(config.entries) != before:
            config_manager.write_scheduler(config)
            self.entriesChanged.emit()

    def handleProfileRenamed(self, old_name: str, new_name: str) -> None:
        """当配置被重命名时调用，更新关联的调度条目。"""
        config = config_manager.read_scheduler()
        changed = False
        for e in config.entries:
            if e.profile_name == old_name:
                e.profile_name = new_name
                changed = True
        if changed:
            config_manager.write_scheduler(config)
            self.entriesChanged.emit()
