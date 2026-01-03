"""
update_api：BASE=/api/update

GET actions:
* ACTION=list_versions，IN=(action=list_versions)，OUT=ApiResponse[VersionInfo]，获取可用远程版本信息

POST actions (body: Pydantic request models):
* ACTION=install_version，IN=(InstallVersionRequest)，OUT=ApiResponse[None]，在后台安装指定版本（会导致当前进程退出）
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from kaa.application.ui.facade import KaaFacade
from kaa.application.services.update_service import VersionInfo

from .models import ApiResponse, ErrorInfo
from .tasks_api import get_facade


class InstallVersionRequest(BaseModel):
    action: str
    version: str


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
        try:
            req = InstallVersionRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
        version = req.version
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
