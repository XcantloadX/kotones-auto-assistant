from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool


class RunButtonState(BaseModel):
    text: str
    interactive: bool


class TaskRow(BaseModel):
    name: str
    status_text: str


class QuickSettings(BaseModel):
    purchase: bool
    assignment: bool
    contest: bool
    produce: bool
    mission_reward: bool
    club_reward: bool
    activity_funds: bool
    presents: bool
    capsule_toys: bool
    upgrade_support_card: bool


class EndAction(str, Enum):
    DO_NOTHING = "DO_NOTHING"
    SHUTDOWN = "SHUTDOWN"
    HIBERNATE = "HIBERNATE"


class SaveResult(BaseModel):
    ok: bool
    message: str


class VersionInfo(BaseModel):
    installed: str | None
    latest: str | None
    versions: list[str]


class ConfigDocument(BaseModel):
    data: dict[str, Any]


class RunState(BaseModel):
    is_running: bool
    is_stopping: bool
    is_paused: bool 