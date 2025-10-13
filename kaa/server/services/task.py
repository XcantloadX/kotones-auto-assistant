"""
Task RPC 服务
处理任务列表和单个任务的启动停止
"""
import logging
from ..rpc import registry
from ..adapters.kaa_runtime import get_runtime

logger = logging.getLogger(__name__)


@registry.decorator('task.list')
async def task_list():
    """获取可用任务列表"""
    from kotonebot.backend.context import task_registry
    
    tasks = []
    for name, task in task_registry.items():
        tasks.append({
            'name': name,
            'display_name': task.name,
            'description': getattr(task, 'description', None),
            'enabled': True,  # TODO: 从配置读取
        })
    
    return tasks


@registry.decorator('task.start')
async def task_start(name: str):
    """启动单个任务"""
    runtime = get_runtime()
    return await runtime.start_task(name)


@registry.decorator('task.stop')
async def task_stop():
    """停止当前任务"""
    runtime = get_runtime()
    return await runtime.stop_task()

