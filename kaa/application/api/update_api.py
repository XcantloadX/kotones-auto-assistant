from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from kaa.application.ui.facade import KaaFacade
from kaa.application.services.update_service import VersionInfo

from .models import ApiResponse, ErrorInfo
from .tasks_api import get_facade

router = APIRouter()


@router.get("", response_model=ApiResponse[Any])
async def update_get(
    action: str = Query(...),
    facade: KaaFacade = Depends(get_facade),
):
    if action == "list_versions":
        try:
            info: VersionInfo = facade.update_service.list_remote_versions()
        except Exception as e:
            return ApiResponse[VersionInfo](
                success=False,
                error=ErrorInfo(code="UPDATE_FETCH_FAILED", message=str(e)),
            )
        return ApiResponse[VersionInfo](success=True, data=info)

    raise HTTPException(status_code=404, detail="Unknown action")


@router.post("", response_model=ApiResponse[Any])
async def update_post(
    payload: dict,
    facade: KaaFacade = Depends(get_facade),
):
    action = payload.get("action")

    if action == "install_version":
        version = payload.get("version")
        if not version:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="VERSION_REQUIRED", message="必须提供 version"),
            )
        try:
            facade.update_service.install_version(version)
        except Exception as e:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="UPDATE_INSTALL_ERROR", message=str(e)),
            )
        # 安装过程会在新进程中进行，当前进程会退出
        return ApiResponse[None](success=True, data=None)

    raise HTTPException(status_code=404, detail="Unknown action")
