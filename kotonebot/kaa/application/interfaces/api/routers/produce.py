from fastapi import APIRouter, HTTPException
from kotonebot.kaa.config.produce import ProduceSolutionManager, ProduceSolution, ProduceData
from kotonebot.kaa.db.idol_card import IdolCard
from kotonebot.kaa.errors import ProduceSolutionNotFoundError
from typing import Optional
from pydantic import BaseModel

router = APIRouter(tags=["produce"]) 

_manager = ProduceSolutionManager()

class IdolOption(BaseModel):
    """偶像选项"""
    label: str
    value: str

@router.get("/produce/idols", response_model=list[IdolOption])
async def list_idols() -> list[IdolOption]:
    """获取所有可选偶像"""
    idols = []
    for idol in IdolCard.all():
        if idol.is_another:
            label = f'{idol.name}　「{idol.another_name}」'
        else:
            label = idol.name
        idols.append(IdolOption(label=label, value=idol.skin_id))
    return idols

@router.get("/produce/solutions", response_model=list[ProduceSolution])
async def list_solutions() -> list[ProduceSolution]:
    return _manager.list()

@router.get("/produce/solutions/{solution_id}", response_model=ProduceSolution)
async def get_solution(solution_id: str) -> ProduceSolution:
    try:
        return _manager.read(solution_id)
    except ProduceSolutionNotFoundError:
        raise HTTPException(status_code=404, detail="培育方案不存在")

@router.post("/produce/solutions", response_model=ProduceSolution)
async def create_solution(name: str, description: Optional[str] = None) -> ProduceSolution:
    solution = _manager.new(name)
    if description:
        solution.description = description
    # 立即保存
    _manager.save(solution.id, solution)
    return solution


@router.put("/produce/solutions/{solution_id}", response_model=ProduceSolution)
async def update_solution(solution_id: str, payload: ProduceSolution) -> ProduceSolution:
    if solution_id != payload.id:
        # 保持路径与载荷一致
        payload.id = solution_id
    _manager.save(solution_id, payload)
    return _manager.read(solution_id)


@router.delete("/produce/solutions/{solution_id}")
async def delete_solution(solution_id: str) -> dict:
    try:
        _manager.delete(solution_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) 