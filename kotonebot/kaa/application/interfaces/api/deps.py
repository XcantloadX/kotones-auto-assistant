from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from kotonebot.kaa.main import Kaa
from kotonebot.backend.bot import RunStatus


@dataclass
class AppState:
    kaa: Optional[Kaa] = None
    run_status: Optional[RunStatus] = None
    is_running: bool = False
    is_stopping: bool = False


_state = AppState()


def get_state() -> AppState:
    global _state
    if _state.kaa is None:
        kaa = Kaa('./config.json')
        kaa.initialize()
        _state.kaa = kaa
    return _state 