import logging
from dataclasses import dataclass
from typing import Callable, ParamSpec, TypeVar, overload

from kotonebot.backend.context import UserConfig

logger = logging.getLogger(__name__)

@dataclass
class Task:
    name: str
    description: str
    func: Callable
    priority: int
    """
    任务优先级，数字越大优先级越高。
    """

@dataclass
class Action:
    name: str
    description: str
    func: Callable
    priority: int
    """
    动作优先级，数字越大优先级越高。
    """

P = ParamSpec('P')
R = TypeVar('R')

task_registry: dict[str, Task] = {}
action_registry: dict[str, Action] = {}
current_callstack: list[Task|Action] = []

def _placeholder():
    raise NotImplementedError('Placeholder function')

def task(
    name: str,
    description: str|None = None,
    *,
    pass_through: bool = False,
    priority: int = 0,
):
    """
    `task` 装饰器，用于标记一个函数为任务函数。

    :param name: 任务名称
    :param description: 任务描述。如果为 None，则使用函数的 docstring 作为描述。
    :param pass_through: 
        默认情况下， @task 装饰器会包裹任务函数，跟踪其执行情况。
        如果不想跟踪，则设置此参数为 False。
    :param priority: 任务优先级，数字越大优先级越高。
    """
    def _task_decorator(func: Callable[P, R]) -> Callable[P, R]:
        nonlocal description
        description = description or func.__doc__ or ''
        task = Task(name, description, _placeholder, priority)
        task_registry[name] = task
        logger.debug(f'Task "{name}" registered.')
        if pass_through:
            return func
        else:
            def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                current_callstack.append(task)
                ret = func(*args, **kwargs)
                current_callstack.pop()
                return ret
            task.func = _wrapper
            return _wrapper
    return _task_decorator

@overload
def action(func: Callable[P, R]) -> Callable[P, R]: ...

@overload
def action(
    name: str,
    description: str|None = None,
    *,
    pass_through: bool = False,
    priority: int = 0,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    `action` 装饰器，用于标记一个函数为动作函数。

    :param name: 动作名称。如果为 None，则使用函数的名称作为名称。
    :param description: 动作描述。如果为 None，则使用函数的 docstring 作为描述。
    :param pass_through: 
        默认情况下， @action 装饰器会包裹动作函数，跟踪其执行情况。
        如果不想跟踪，则设置此参数为 False。
    :param priority: 动作优先级，数字越大优先级越高。
    """
    ...

def action(*args, **kwargs):
    def _register(func: Callable, name: str, description: str|None = None, priority: int = 0) -> Action:
        description = description or func.__doc__ or ''
        action = Action(name, description, func, priority)
        action_registry[name] = action
        logger.debug(f'Action "{name}" registered.')
        return action

    pass_through = kwargs.get('pass_through', True)
    priority = kwargs.get('priority', 0)
    if len(args) == 1 and isinstance(args[0], Callable):
        func = args[0]
        action = _register(_placeholder, func.__name__, func.__doc__, priority)
        if pass_through:
            return func
        else:
            def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                current_callstack.append(action)
                ret = func(*args, **kwargs)
                current_callstack.pop()
                return ret
            action.func = _wrapper
            return _wrapper
    else:
        name = args[0]
        description = args[1] if len(args) >= 2 else None
        def _action_decorator(func: Callable):
            nonlocal pass_through
            action = _register(_placeholder, name, description)
            pass_through = kwargs.get('pass_through', True)
            if pass_through:
                return func
            else:
                def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                    current_callstack.append(action)
                    ret = func(*args, **kwargs)
                    current_callstack.pop()
                    return ret
                action.func = _wrapper
                return _wrapper
        return _action_decorator
