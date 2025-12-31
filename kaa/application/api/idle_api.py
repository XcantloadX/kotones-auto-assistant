from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from kaa.application.ui.facade import KaaFacade
from kaa.application.services.task_service import TaskService
from kaa.application.core.idle_mode import get_system_idle_seconds
from kaa.config.schema import IdleModeConfig

from .models import ApiResponse, IdleStatusDto
from .tasks_api import get_facade

router = APIRouter()


@router.get("", response_model=ApiResponse[Any])
async def idle_get(
    action: str = Query(...),
    facade: KaaFacade = Depends(get_facade),
):
    if action != "status":
        raise HTTPException(status_code=404, detail="Unknown action")

    cfg = facade.config_service.get_options()
    idle_conf: IdleModeConfig = cfg.idle

    task_service: TaskService = facade.task_service
    running = task_service.is_running()
    paused = task_service.get_pause_status() is True

    status = IdleStatusDto(
        enabled=idle_conf.enabled,
        idle_seconds_config=idle_conf.idle_seconds,
        system_idle_seconds=get_system_idle_seconds(),
        running=running,
        paused=paused,
    )

    return ApiResponse[IdleStatusDto](success=True, data=status)
