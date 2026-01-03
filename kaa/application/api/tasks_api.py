"""
tasks_api：BASE=/api/tasks

* ACTION=list_statuses，IN=(action=list_statuses)，OUT=ApiResponse[List[TaskStatusDto]]，列出任务状态
* ACTION=list_registry，IN=(action=list_registry)，OUT=ApiResponse[List[str]]，列出注册表中所有任务名称
* ACTION=overview，IN=(action=overview)，OUT=ApiResponse[TaskOverviewDto]，任务运行概览
* ACTION=run_all，IN=(body: TasksPostPayload with action=run_all)，OUT=ApiResponse[None]，启动所有任务
* ACTION=stop，IN=(body: TasksPostPayload with action=stop)，OUT=ApiResponse[None]，停止所有任务
* ACTION=run_single，IN=(body: TasksPostPayload with task_name)，OUT=ApiResponse[None]，启动单个任务
* ACTION=pause_toggle，IN=(body: TasksPostPayload with action=pause_toggle)，OUT=ApiResponse[PauseToggleResult]，切换暂停状态
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from kaa.application.ui.facade import KaaFacade
from kaa.main.kaa import Kaa
from .models import (
    ApiResponse,
    ErrorInfo,
)


class TaskStatusDto(BaseModel):
    name: str
    status: str  # pending / running / finished / error / cancelled


class PauseToggleResult(BaseModel):
    paused: Optional[bool]


class RunButtonStatus(BaseModel):
    status: str      # "start" / "stop" / "stopping"
    interactive: bool


class PauseButtonStatus(BaseModel):
    status: str      # "pause" / "resume"
    interactive: bool


class TaskRuntimeDto(BaseModel):
    display: str     # 始终为 "HH:MM:SS" 形式
    seconds: int     # 总秒数
    running: bool    # 是否当前有任务在运行


class TaskOverviewDto(BaseModel):
    paused: Optional[bool]
    run_button: RunButtonStatus
    pause_button: PauseButtonStatus
    runtime: TaskRuntimeDto


router = APIRouter()


# --- Dependency helpers ---

def get_kaa() -> Kaa:
    """Create or reuse a singleton Kaa instance for the API layer.

    NOTE: The CLI / Gradio entry points construct Kaa with a specific
    config path. For the HTTP API we currently default to "config.json".
    This can be refactored later into a shared factory.
    """

    if not hasattr(get_kaa, "_instance"):
        get_kaa._instance = Kaa("config.json")
    return get_kaa._instance  # type: ignore[attr-defined]


def get_facade(kaa: Kaa = Depends(get_kaa)) -> KaaFacade:
    if not hasattr(get_facade, "_instance"):
        get_facade._instance = KaaFacade(kaa)
    return get_facade._instance  # type: ignore[attr-defined]


# --- Unified GET handler: /api/tasks?action=... ---


@router.get("", response_model=ApiResponse[Any])
async def tasks_get(action: str = Query(...), facade: KaaFacade = Depends(get_facade)):
    """Handle all GET /api/tasks?action=... queries.

    - list_statuses -> ApiResponse[List[TaskStatusDto]]
    - list_registry -> ApiResponse[List[str]]
    - overview      -> ApiResponse[TaskOverviewDto]
    """

    if action == "list_statuses":
        statuses = [TaskStatusDto(name=name, status=status) for name, status in facade.get_task_statuses()]
        return ApiResponse[List[TaskStatusDto]](success=True, data=statuses)

    if action == "list_registry":
        names = facade.task_service.get_all_task_names()
        return ApiResponse[List[str]](success=True, data=names)

    if action == "overview":
        tcs = facade.task_service
        paused = tcs.get_pause_status()

        # Run button status derived from task flags
        if not tcs.is_running_all:
            run_button = RunButtonStatus(status="start", interactive=True)
        elif tcs.is_stopping:
            run_button = RunButtonStatus(status="stopping", interactive=False)
        else:
            run_button = RunButtonStatus(status="stop", interactive=True)

        # Pause button status derived from pause state and run flags
        is_paused = paused is True
        is_stoppable = not tcs.is_stopping
        can_pause = tcs.is_running() and is_stoppable
        pause_button = PauseButtonStatus(status="resume" if is_paused else "pause", interactive=can_pause)

        # Runtime information: use seconds + running flag, display is HH:MM:SS
        runtime_td = tcs.get_task_runtime()
        running = runtime_td is not None
        total_seconds = int(runtime_td.total_seconds()) if runtime_td is not None else 0
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        runtime = TaskRuntimeDto(
            display=f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            seconds=total_seconds,
            running=running,
        )

        overview_dto = TaskOverviewDto(
            paused=paused,
            run_button=run_button,
            pause_button=pause_button,
            runtime=runtime,
        )
        return ApiResponse[TaskOverviewDto](success=True, data=overview_dto)

    raise HTTPException(status_code=404, detail="Unknown action")


# --- Unified POST handler: /api/tasks {"action": ...} ---


class TasksPostPayload(BaseModel):
    action: str
    task_name: str | None = None


@router.post("", response_model=ApiResponse[Any])
async def tasks_post(payload: TasksPostPayload, facade: KaaFacade = Depends(get_facade)):
    action = payload.action

    if action == "run_all":
        facade.start_all_tasks()
        return ApiResponse[None](success=True, data=None)

    if action == "stop":
        facade.stop_all_tasks()
        return ApiResponse[None](success=True, data=None)

    if action == "run_single":
        if not payload.task_name:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="TASK_NAME_REQUIRED", message="必须提供 task_name"),
            )
        try:
            facade.task_service.start_single_task(payload.task_name)
        except ValueError:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="TASK_NOT_FOUND", message="任务不存在"),
            )
        return ApiResponse[None](success=True, data=None)

    if action == "pause_toggle":
        paused = facade.toggle_pause()
        result = PauseToggleResult(paused=paused)
        return ApiResponse[PauseToggleResult](success=True, data=result)

    raise HTTPException(status_code=404, detail="Unknown action")
