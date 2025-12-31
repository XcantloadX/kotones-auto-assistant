from typing import Any

from fastapi import APIRouter, HTTPException

from kaa.application.adapter import misc_adapter
from kaa.errors import WindowsOnlyError, LauncherNotFoundError

from .models import ApiResponse, ErrorInfo, DesktopShortcutRequest

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
