from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from kaa.application.ui.facade import KaaFacade

from .models import ApiResponse, ErrorInfo, LogExportResult
from .tasks_api import get_facade

router = APIRouter()


@router.post("", response_model=ApiResponse[Any])
async def feedback_post(
    payload: dict,
    facade: KaaFacade = Depends(get_facade),
):
    action = payload.get("action")

    if action == "create_report":
        title = payload.get("title") or "无标题"
        description = payload.get("description") or ""
        upload = bool(payload.get("upload", True))

        try:
            # 这里直接使用 changelog 所在版本段落前缀中的版本号不太可靠，
            # 元数据已经移除动态版本号逻辑，因此此处将版本字段留空，由后端自行在压缩包内记录。
            result = facade.feedback_service.report(
                title=title,
                description=description,
                version="",
                upload=upload,
                on_progress=None,
            )
        except Exception as e:
            return ApiResponse(
                success=False,
                error=ErrorInfo(code="FEEDBACK_ERROR", message=str(e)),
            )
        return ApiResponse(success=True, data=result)

    if action == "export_logs":
        message = facade.export_logs_as_zip()
        zip_path = None
        if "已导出到" in message:
            try:
                zip_path = message.split(" ")[-1]
            except Exception:
                zip_path = None
        result = LogExportResult(message=message, zip_path=zip_path)
        return ApiResponse(success=True, data=result)

    raise HTTPException(status_code=404, detail="Unknown action")
