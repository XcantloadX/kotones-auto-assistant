import os
import io
import zipfile
import pkgutil
import logging
import importlib
import traceback
import threading
from datetime import datetime
from typing import Callable, Optional, Any, Literal
from dataclasses import dataclass, field

import cv2

from kotonebot.backend.context import init_context
from kotonebot.backend.core import task_registry, action_registry, current_callstack, Task, Action

log_stream = io.StringIO()
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s'))
logging.getLogger('kotonebot').addHandler(stream_handler)
logger = logging.getLogger(__name__)

@dataclass
class TaskStatus:
    task: Task
    status: Literal['pending', 'running', 'finished', 'error', 'cancelled']

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

def _save_error_report(
    exception: Exception,
    *,
    path: str | None = None
) -> str:
    """
    保存错误报告

    :param path: 保存的路径。若为 `None`，则保存到 `./reports/{YY-MM-DD HH-MM-SS}.zip`。
    :return: 保存的路径
    """
    from kotonebot import device
    if path is None:
        path = f'./reports/{datetime.now().strftime("%Y-%m-%d %H-%M-%S")}.zip'
    exception_msg = '\n'.join(traceback.format_exception(exception))
    task_callstack = '\n'.join([f'{i+1}. name={task.name} priority={task.priority}' for i, task in enumerate(current_callstack)])
    screenshot = device.screenshot()
    logs = log_stream.getvalue()
    with open('config.json', 'r') as f:
        config_content = f.read()

    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with zipfile.ZipFile(path, 'w') as zipf:
        zipf.writestr('exception.txt', exception_msg)
        zipf.writestr('task_callstack.txt', task_callstack)
        zipf.writestr('screenshot.png', cv2.imencode('.png', screenshot)[1].tobytes())
        zipf.writestr('config.json', config_content)
        zipf.writestr('logs.txt', logs)
    return path

def run(
    *,
    debug: bool = False,
    resume_on_error: bool = False,
    config_type: type = dict[str, Any],
    on_finished: Optional[Callable[[], None]] = None,
    on_task_status_changed: Optional[Callable[[Task, Literal['pending', 'running', 'finished', 'error', 'cancelled']], None]] = None,
    on_task_error: Optional[Callable[[Task, Exception], None]] = None,
    auto_save_error_report: bool = True,
):
    """
    按优先级顺序运行所有任务。

    :param debug: 是否为调试模式。调试模式下，不捕获异常，不保存错误报告。默认为 `False`。
    :param resume_on_error: 是否在任务出错时继续运行。默认为 `False`。
    :param auto_save_error_report: 是否自动保存错误报告。默认 `True`。
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

        if debug:
            task.func()
        else:
            try:
                task.func()
                if on_task_status_changed:
                    on_task_status_changed(task, 'finished')
            except Exception as e:
                logger.error(f'Task failed: {task.name}')
                logger.exception(f'Error: ')
                report_path = None
                if auto_save_error_report:
                    report_path = _save_error_report(e)
                if on_task_status_changed:
                    on_task_status_changed(task, 'error')
                if not resume_on_error:
                    for task1 in tasks[tasks.index(task)+1:]:
                        if on_task_status_changed:
                            on_task_status_changed(task1, 'cancelled')
                    break
        logger.info(f'Task finished: {task.name}')
    logger.info('All tasks finished.')
    if on_finished:
        on_finished()

def start(
    *,
    debug: bool = False,
    resume_on_error: bool = False,
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
        else:
            _find(task).status = status
    thread = threading.Thread(target=run, kwargs={
        'config_type': config_type,
        'debug': debug,
        'resume_on_error': resume_on_error,
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
    run(debug=True)


