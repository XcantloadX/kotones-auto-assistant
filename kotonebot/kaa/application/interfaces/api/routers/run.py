from fastapi import APIRouter
from ..schemas import RunState
from ..deps import get_state

router = APIRouter(tags=["run"]) 


def _get_run_state() -> RunState:
    state = get_state()
    is_paused = False
    try:
        from kotonebot.backend.context.context import vars
        is_paused = bool(vars.flow.is_paused)
    except Exception:
        is_paused = False
    return RunState(is_running=state.is_running, is_stopping=state.is_stopping, is_paused=is_paused)


@router.get("/run/state", response_model=RunState)
async def get_run_state() -> RunState:
    return _get_run_state()


@router.post("/run/toggle", response_model=RunState)
async def post_run_toggle() -> RunState:
    state = get_state()
    if not state.is_running:
        # 启动
        state.run_status = state.kaa.start_all()  # type: ignore[union-attr]
        state.is_running = True
        state.is_stopping = False
        return _get_run_state()
    # 正在停止中，维持状态
    if state.is_stopping:
        return _get_run_state()
    # 请求停止
    state.is_stopping = True
    from kotonebot.backend.context.context import vars
    if vars.flow.is_paused:
        vars.flow.request_resume()
    vars.flow.request_interrupt()
    state.is_running = False
    return _get_run_state()


@router.post("/run/start_all", response_model=RunState)
async def post_run_start_all() -> RunState:
    state = get_state()
    if not state.is_running:
        state.run_status = state.kaa.start_all()  # type: ignore[union-attr]
        state.is_running = True
        state.is_stopping = False
    return _get_run_state()


@router.post("/run/stop_all", response_model=RunState)
async def post_run_stop_all() -> RunState:
    state = get_state()
    if state.is_running and not state.is_stopping:
        state.is_stopping = True
        from kotonebot.backend.context.context import vars
        if vars.flow.is_paused:
            vars.flow.request_resume()
        vars.flow.request_interrupt()
        state.is_running = False
    return _get_run_state()


@router.post("/run/pause_toggle", response_model=RunState)
async def post_run_pause_toggle() -> RunState:
    from kotonebot.backend.context.context import vars
    try:
        if vars.flow.is_paused:
            vars.flow.request_resume()
        else:
            vars.flow.request_pause()
    except Exception:
        pass
    return _get_run_state() 