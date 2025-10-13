"""
Engine RPC 服务
处理引擎启动、停止、暂停等控制操作
"""
import logging
from ..rpc import registry
from ..adapters.kaa_runtime import get_runtime

logger = logging.getLogger(__name__)


@registry.decorator('engine.status')
async def engine_status():
    """获取引擎运行状态"""
    runtime = get_runtime()
    return runtime.get_status()


@registry.decorator('engine.start_all')
async def engine_start_all():
    """启动所有任务"""
    runtime = get_runtime()
    return await runtime.start_all()


@registry.decorator('engine.stop_all')
async def engine_stop_all():
    """停止所有任务"""
    runtime = get_runtime()
    return await runtime.stop_all()


@registry.decorator('engine.pause')
async def engine_pause():
    """暂停"""
    runtime = get_runtime()
    return await runtime.pause()


@registry.decorator('engine.resume')
async def engine_resume():
    """恢复"""
    runtime = get_runtime()
    return await runtime.resume()


@registry.decorator('engine.toggle_pause')
async def engine_toggle_pause():
    """切换暂停/恢复状态"""
    runtime = get_runtime()
    return await runtime.toggle_pause()

