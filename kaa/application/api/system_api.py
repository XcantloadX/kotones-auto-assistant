"""
system_api：BASE=/api/system

GET actions:
* ACTION=get_version，IN=None，OUT=ApiResponse[str]，获取后端应用版本

POST actions (body: DesktopShortcutRequest):
* ACTION=create_desktop_shortcut，IN=(DesktopShortcutRequest)，OUT=ApiResponse[None]，在 Windows 上创建桌面快捷方式并可选择立即启动
"""

from typing import Any
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query, Depends

from kaa.application.adapter import misc_adapter
from kaa.errors import WindowsOnlyError, LauncherNotFoundError

from .models import ApiResponse, ErrorInfo
from .tasks_api import get_facade
from kaa.application.ui.facade import KaaFacade


class DesktopShortcutRequest(BaseModel):
    action: str = "create_desktop_shortcut"
    start_immediately: bool = False

router = APIRouter()


@router.post("", response_model=ApiResponse[Any])
async def system_post(payload: DesktopShortcutRequest):
    action = getattr(payload, "action", "create_desktop_shortcut") if hasattr(payload, "action") else "create_desktop_shortcut"

    if action == "create_desktop_shortcut":
        try:
            misc_adapter.create_desktop_shortcut(start_immediately=payload.start_immediately)
        except WindowsOnlyError:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="NOT_SUPPORTED", message="当前平台不支持创建桌面快捷方式"),
            )
        except LauncherNotFoundError:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="LAUNCHER_NOT_FOUND", message="未找到 kaa.exe，无法创建快捷方式"),
            )
        except Exception as e:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="SYSTEM_ERROR", message=str(e)),
            )
        return ApiResponse[None](success=True, data=None)

    raise HTTPException(status_code=404, detail="Unknown action")


@router.get("", response_model=ApiResponse[Any])
async def system_get(action: str = Query(...), facade: KaaFacade = Depends(get_facade)):
    """Handle GET /api/system?action=... for simple system queries."""

    if action == "get_version":
        try:
            version = getattr(facade._kaa, "version", None)
            return ApiResponse[str](success=True, data=version)
        except Exception as e:
            return ApiResponse[None](success=False, error=ErrorInfo(code="UNKNOWN", message=str(e)))

    raise HTTPException(status_code=404, detail="Unknown action")
