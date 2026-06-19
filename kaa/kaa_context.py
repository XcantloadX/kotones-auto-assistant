import contextvars
from typing import TYPE_CHECKING

from kotonebot.backend.context import vars
from kotonebot.client.host import Instance

if TYPE_CHECKING:
    from kaa.config.schema import KaaConfig
    from kaa.config.produce import ProduceSolution
from kaa.errors import NoProduceSolutionSelectedError

_config_var: contextvars.ContextVar['KaaConfig | None'] = contextvars.ContextVar('kaa_config', default=None)
_config_name_var: contextvars.ContextVar['str | None'] = contextvars.ContextVar('kaa_config_name', default=None)


def _set_instance(new_instance: Instance) -> None:
    vars.set('instance', new_instance)


def instance() -> Instance:
    return vars.get('instance')


def init(config: 'KaaConfig', name: str) -> None:
    """在启动任务前由调度器调用，注入当前 profile（线程隔离）。"""
    _config_var.set(config)
    _config_name_var.set(name)


def conf() -> 'KaaConfig':
    """获取当前线程的 profile 配置。"""
    config = _config_var.get()
    if config is None:
        raise RuntimeError("Config not initialized. Call init() before running tasks.")
    return config


def config_name() -> str | None:
    """获取当前线程的 profile 名称。"""
    return _config_name_var.get()


def save_config() -> None:
    """将当前线程的 profile 写回磁盘。"""
    from kaa.config import manager  # noqa: PLC0415

    config = _config_var.get()
    name = _config_name_var.get()
    if config is None or name is None:
        return
    manager.write(name, config)


def produce_solution() -> 'ProduceSolution':
    """获取当前培育方案"""
    from kaa.config.produce import ProduceSolutionManager

    id = conf().tasks.produce.selected_solution_id
    if id is None:
        raise NoProduceSolutionSelectedError()
    # TODO: 这里需要缓存，不能每次都从磁盘读取
    return ProduceSolutionManager().read(id)
