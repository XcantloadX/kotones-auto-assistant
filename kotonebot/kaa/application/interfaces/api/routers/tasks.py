from fastapi import APIRouter
from ..schemas import TaskRow
from ..deps import get_state
from kotonebot.backend.context.task_action import task_registry

router = APIRouter(tags=["tasks"]) 


@router.get("/tasks", response_model=list[TaskRow])
async def get_tasks() -> list[TaskRow]:
    state = get_state()
    rows: list[TaskRow] = []
    run_status = state.run_status
    if run_status is None:
        for name, task in task_registry.items():
            rows.append(TaskRow(name=task.name, status_text="等待中"))
        return rows

    status_text_map = {
        'pending': '等待中',
        'running': '运行中',
        'finished': '已完成',
        'error': '出错',
        'cancelled': '已取消',
    }
    # 仅输出存在于任务状态中的任务；若需要完整列表，可补齐默认项
    for task_status in run_status.tasks:
        rows.append(TaskRow(name=task_status.task.name, status_text=status_text_map.get(task_status.status, '未知')))
    return rows 