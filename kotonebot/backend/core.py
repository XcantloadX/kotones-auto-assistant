import logging
from typing import Callable, ParamSpec, TypeVar, overload, Any, NamedTuple

logger = logging.getLogger(__name__)

class Task(NamedTuple):
    name: str
    description: str
    func: Callable


class Action(NamedTuple):
    name: str
    description: str
    func: Callable


P = ParamSpec('P')
R = TypeVar('R')

task_registry: dict[str, Task] = {}
action_registry: dict[str, Action] = {}

def task(
    name: str,
    description: str|None = None,
):
    """
    `task` 装饰器，用于标记一个函数为任务函数。

    :param name: 任务名称
    :param description: 任务描述。如果为 None，则使用函数的 docstring 作为描述。
    """
    def _task_decorator(func: Callable[P, R]) -> Callable[P, R]:
        nonlocal description
        description = description or func.__doc__ or ''
        task_registry[name] = Task(name, description, func)
        logger.debug(f'Task "{name}" registered.')
        return func
    return _task_decorator

@overload
def action(func: Callable[P, R]) -> Callable[P, R]: ...

@overload
def action(name: str, description: str|None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    `action` 装饰器，用于标记一个函数为动作函数。

    :param name: 动作名称。如果为 None，则使用函数的名称作为名称。
    :param description: 动作描述。如果为 None，则使用函数的 docstring 作为描述。
    """
    ...

def action(*args, **kwargs):
    def _register(name: str, description: str|None = None):
        description = description or func.__doc__ or ''
        action_registry[name] = Action(name, description, func)
        logger.debug(f'Action "{name}" registered.')
        return func

    if len(args) == 1:
        func = args[0]
        _register(func.__name__, func.__doc__)
        return func
    elif len(args) == 2:
        name = args[0]
        description = args[1]
        def _action_decorator(func: Callable):
            return func
        _register(name, description)
        return _action_decorator
    else:
        raise ValueError("action() takes 1 or 2 positional arguments but 3 were given")
