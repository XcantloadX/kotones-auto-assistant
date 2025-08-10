from fastapi import APIRouter, HTTPException
from kotonebot.kaa.config.produce import ProduceSolutionManager, ProduceSolution, ProduceData

router = APIRouter(tags=["produce"]) 

_manager = ProduceSolutionManager()


@router.get("/produce/solutions", response_model=list[ProduceSolution])
async def list_solutions() -> list[ProduceSolution]:
    return _manager.list()


@router.post("/produce/solutions", response_model=ProduceSolution)
async def create_solution(name: str) -> ProduceSolution:
    solution = _manager.new(name)
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