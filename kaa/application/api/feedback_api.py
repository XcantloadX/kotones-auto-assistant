"""
feedback_api：BASE=/api/feedback

POST actions (body: Pydantic request models):
* ACTION=create_report，IN=(CreateReportRequest)，OUT=ApiResponse[Any]，创建并提交反馈报告（可选上传）
* ACTION=export_logs，IN=(ExportLogsRequest)，OUT=ApiResponse[LogExportResult]，导出日志为 zip 并返回路径/消息
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from kaa.application.ui.facade import KaaFacade


from .models import ApiResponse, ErrorInfo
from .tasks_api import get_facade


class LogExportResult(BaseModel):
    message: str
    zip_path: Optional[str] = None


class CreateReportRequest(BaseModel):
    action: str
    title: str | None = None
    description: str | None = None
    upload: bool | None = True


class ExportLogsRequest(BaseModel):
    action: str


router = APIRouter()


@router.post("", response_model=ApiResponse[Any])
async def feedback_post(
    payload: dict,
    facade: KaaFacade = Depends(get_facade),
):
    action = payload.get("action")

    if action == "create_report":
        try:
            req = CreateReportRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse(
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
        title = req.title or "无标题"
        description = req.description or ""
        upload = bool(req.upload if req.upload is not None else True)

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
        try:
            _ = ExportLogsRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse(
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
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
