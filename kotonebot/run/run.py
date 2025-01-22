import pkgutil
import logging
import importlib
import threading
from typing import Callable, Optional, Any, Literal
from dataclasses import dataclass, field

from kotonebot.backend.context import init_context
from kotonebot.backend.core import task_registry, action_registry, Task, Action

logger = logging.getLogger(__name__)

@dataclass
class TaskStatus:
    task: Task
    status: Literal['pending', 'running', 'finished', 'error']

@dataclass
class RunStatus:
    running: bool = False
    tasks: list[TaskStatus] = field(default_factory=list)
    current_task: Task | None = None
    callstack: list[Task | Action] = field(default_factory=list)

def initialize(module: str):
    """
    初始化并载入所有任务和动作。

    :param module: 主模块名。此模块及其所有子模块都会被载入。
    """
    logger.info('Initializing tasks and actions...')
    logger.debug(f'Loading module: {module}')
    # 加载主模块
    importlib.import_module(module)

    # 加载所有子模块
    pkg = importlib.import_module(module)
    for loader, name, is_pkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + '.'):
        logger.debug(f'Loading sub-module: {name}')
        try:
            importlib.import_module(name)
        except Exception as e:
            logger.error(f'Failed to load sub-module: {name}')
            logger.exception(f'Error: ')
    
    logger.info('Tasks and actions initialized.')
    logger.info(f'{len(task_registry)} task(s) and {len(action_registry)} action(s) loaded.')

def run(
    *,
    config_type: type = dict[str, Any],
    no_try: bool = False,
    on_finished: Optional[Callable[[], None]] = None,
    on_task_status_changed: Optional[Callable[[Task, Literal['pending', 'running', 'finished', 'error']], None]] = None,
    on_task_error: Optional[Callable[[Task, Exception], None]] = None,
):
    """
    按优先级顺序运行所有任务。

    :param no_try: 是否不捕获异常。
    """
    init_context(config_type=config_type)

    tasks = sorted(task_registry.values(), key=lambda x: x.priority, reverse=True)
    for task in tasks:
        if on_task_status_changed:
            on_task_status_changed(task, 'pending')

    for task in tasks:
        logger.info(f'Task started: {task.name}')
        if on_task_status_changed:
            on_task_status_changed(task, 'running')

        if no_try:
            task.func()
        else:
            try:
                task.func()
                if on_task_status_changed:
                    on_task_status_changed(task, 'finished')
            except Exception:
                logger.error(f'Task failed: {task.name}')
                logger.exception(f'Error: ')
                if on_task_status_changed:
                    on_task_status_changed(task, 'error')
        logger.info(f'Task finished: {task.name}')
    logger.info('All tasks finished.')
    if on_finished:
        on_finished()

def start(
    *,
    no_try: bool = False,
    config_type: type = dict[str, Any],
) -> RunStatus:
    run_status = RunStatus(running=True)
    def _on_finished():
        run_status.running = False
        run_status.current_task = None
        run_status.callstack = []
    def _on_task_status_changed(task: Task, status: Literal['pending', 'running', 'finished', 'error']):
        def _find(task: Task) -> TaskStatus:
            for task_status in run_status.tasks:
                if task_status.task == task:
                    return task_status
            raise ValueError(f'Task {task.name} not found in run_status.tasks')
        if status == 'pending':
            run_status.tasks.append(TaskStatus(task=task, status='pending'))
        elif status == 'running':
            _find(task).status = 'running'
        elif status == 'finished':
            _find(task).status = 'finished'
        elif status == 'error':
            _find(task).status = 'error'
    thread = threading.Thread(target=run, kwargs={
        'config_type': config_type,
        'no_try': no_try,
        'on_finished': _on_finished,
        'on_task_status_changed': _on_task_status_changed,
    })
    thread.start()
    return run_status

if __name__ == '__main__':
    from kotonebot.tasks.common import BaseConfig
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s')
    logger.setLevel(logging.DEBUG)
    logging.getLogger('kotonebot').setLevel(logging.DEBUG)
    init_context(config_type=BaseConfig)
    initialize('kotonebot.tasks')
    run(no_try=True)


