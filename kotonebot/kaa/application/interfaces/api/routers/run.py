from fastapi import APIRouter
from ..schemas import RunButtonState
from ..deps import get_state

router = APIRouter(tags=["run"]) 


def _get_run_button_state() -> RunButtonState:
    state = get_state()
    if not state.is_running:
        return RunButtonState(text="启动", interactive=True)
    if state.is_stopping:
        return RunButtonState(text="停止中...", interactive=False)
    return RunButtonState(text="停止", interactive=True)


def _get_pause_button_state() -> RunButtonState:
    state = get_state()
    try:
        from kotonebot.backend.context.context import vars
        text = "恢复" if vars.flow.is_paused else "暂停"
    except Exception:
        text = "暂停"
    interactive = not state.is_stopping
    return RunButtonState(text=text, interactive=interactive)


@router.get("/run/button_state", response_model=RunButtonState)
async def get_run_button_state() -> RunButtonState:
    return _get_run_button_state()


@router.get("/run/pause_button_state", response_model=RunButtonState)
async def get_pause_button_state() -> RunButtonState:
    return _get_pause_button_state()


@router.post("/run/toggle", response_model=RunButtonState)
async def post_run_toggle() -> RunButtonState:
    state = get_state()
    if not state.is_running:
        # 启动
        state.run_status = state.kaa.start_all()  # type: ignore[union-attr]
        state.is_running = True
        state.is_stopping = False
        return _get_run_button_state()
    # 正在停止中，维持状态
    if state.is_stopping:
        return _get_run_button_state()
    # 请求停止
    state.is_stopping = True
    from kotonebot.backend.context.context import vars
    if vars.flow.is_paused:
        vars.flow.request_resume()
    vars.flow.request_interrupt()
    state.is_running = False
    return _get_run_button_state()


@router.post("/run/start_all", response_model=RunButtonState)
async def post_run_start_all() -> RunButtonState:
    state = get_state()
    if not state.is_running:
        state.run_status = state.kaa.start_all()  # type: ignore[union-attr]
        state.is_running = True
        state.is_stopping = False
    return _get_run_button_state()


@router.post("/run/stop_all", response_model=RunButtonState)
async def post_run_stop_all() -> RunButtonState:
    state = get_state()
    if state.is_running and not state.is_stopping:
        state.is_stopping = True
        from kotonebot.backend.context.context import vars
        if vars.flow.is_paused:
            vars.flow.request_resume()
        vars.flow.request_interrupt()
        state.is_running = False
    return _get_run_button_state()


@router.post("/run/pause_toggle", response_model=RunButtonState)
async def post_run_pause_toggle() -> RunButtonState:
    from kotonebot.backend.context.context import vars
    try:
        if vars.flow.is_paused:
            vars.flow.request_resume()
        else:
            vars.flow.request_pause()
    except Exception:
        pass
    return _get_pause_button_state() 