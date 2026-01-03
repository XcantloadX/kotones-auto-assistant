"""
produce_api：BASE=/api/produce

GET actions:
* ACTION=list_solutions，IN=(action=list_solutions)，OUT=ApiResponse[List[ProduceSolution]]，列出所有培育方案
* ACTION=get_solution，IN=(action=get_solution, solution_id)，OUT=ApiResponse[ProduceSolution]，获取指定培育方案

POST actions (body: Pydantic request models):
* ACTION=create_solution，IN=(CreateSolutionRequest)，OUT=ApiResponse[ProduceSolution]，创建新方案
* ACTION=delete_solution，IN=(DeleteSolutionRequest)，OUT=ApiResponse[None]，删除指定方案
* ACTION=save_solution，IN=(SaveSolutionRequest)，OUT=ApiResponse[ProduceSolution]，保存方案数据
"""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from kaa.application.ui.facade import KaaFacade
from kaa.config.produce import ProduceSolution, ProduceData

from .models import ApiResponse, ErrorInfo
from .tasks_api import get_facade

router = APIRouter()


@router.get("", response_model=ApiResponse[Any])
async def produce_get(
    action: str = Query(...),
    solution_id: str | None = Query(None),
    facade: KaaFacade = Depends(get_facade),
):
    if action == "list_solutions":
        solutions: List[ProduceSolution] = facade.list_produce_solutions()
        return ApiResponse[List[ProduceSolution]](success=True, data=solutions)

    if action == "get_solution":
        if not solution_id:
            raise HTTPException(status_code=400, detail="solution_id is required")
        solution = facade.get_produce_solution(solution_id)
        return ApiResponse[ProduceSolution](success=True, data=solution)

    raise HTTPException(status_code=404, detail="Unknown action")


class CreateSolutionRequest(BaseModel):
    action: str
    name: str


class DeleteSolutionRequest(BaseModel):
    action: str
    solution_id: str


class SaveSolutionRequest(BaseModel):
    action: str
    solution_id: str
    name: str
    description: str | None = None
    data: ProduceData


@router.post("", response_model=ApiResponse[Any])
async def produce_post(
    payload: dict,
    facade: KaaFacade = Depends(get_facade),
):
    action = payload.get("action")

    if action == "create_solution":
        try:
            req = CreateSolutionRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse[ProduceSolution](
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
        name = req.name or "新培育方案"
        solution = facade.create_produce_solution(name)
        return ApiResponse[ProduceSolution](success=True, data=solution)

    if action == "delete_solution":
        try:
            req = DeleteSolutionRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
        solution_id = req.solution_id
        if not solution_id:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="SOLUTION_ID_REQUIRED", message="必须提供 solution_id"),
            )
        # Will raise ValueError if deleting selected solution; we map it to a friendly error
        try:
            facade.delete_produce_solution(solution_id)
        except ValueError as e:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="CANNOT_DELETE_SELECTED_SOLUTION", message=str(e)),
            )
        return ApiResponse[None](success=True, data=None)

    if action == "save_solution":
        try:
            req = SaveSolutionRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse[None](
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
        data = req.data
        solution = facade.produce_solution_service.update_solution_data(
            solution_id=req.solution_id,
            name=req.name,
            description=req.description or "",
            data=data,
        )
        return ApiResponse[ProduceSolution](success=True, data=solution)

    raise HTTPException(status_code=404, detail="Unknown action")
