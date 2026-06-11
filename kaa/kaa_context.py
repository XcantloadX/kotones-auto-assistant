from typing import TYPE_CHECKING

from kotonebot.backend.context import vars
from kotonebot.client.host import Instance

if TYPE_CHECKING:
    from kaa.config.schema import KaaConfig
    from kaa.config.produce import ProduceSolution
from kaa.errors import NoProduceSolutionSelectedError

_config_cache: 'KaaConfig | None' = None
_config_name: 'str | None' = None


def _set_instance(new_instance: Instance) -> None:
    vars.set('instance', new_instance)


def instance() -> Instance:
    return vars.get('instance')


def init(config: 'KaaConfig', name: str) -> None:
    """在启动任务前由调度器调用，注入当前 profile。"""
    global _config_cache, _config_name
    _config_cache = config
    _config_name = name


def conf() -> 'KaaConfig':
    """获取当前 profile 配置。"""
    if _config_cache is None:
        raise RuntimeError("Config not initialized. Call init() before running tasks.")
    return _config_cache


def save_config() -> None:
    """将当前 profile 写回磁盘。"""
    from kaa.config import manager  # noqa: PLC0415

    if _config_cache is None or _config_name is None:
        return
    manager.write(_config_name, _config_cache)


def produce_solution() -> 'ProduceSolution':
    """获取当前培育方案"""
    from kaa.config.produce import ProduceSolutionManager

    id = conf().produce.selected_solution_id
    if id is None:
        raise NoProduceSolutionSelectedError()
    # TODO: 这里需要缓存，不能每次都从磁盘读取
    return ProduceSolutionManager().read(id)
