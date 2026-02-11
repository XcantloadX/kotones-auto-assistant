from typing import TYPE_CHECKING

from kotonebot.backend.context import vars
from kotonebot.client.host import Instance

if TYPE_CHECKING:
    from kaa.config.schema import BaseConfig
    from kaa.config.produce import ProduceSolution
from kaa.errors import NoProduceSolutionSelectedError

def _set_instance(new_instance: Instance) -> None:
    vars.set('instance', new_instance)

def instance() -> Instance:
    return vars.get('instance')

def conf() -> 'BaseConfig':
    return raw_conf().options

def raw_conf():
    """获取当前配置数据"""
    from kaa.config.context import ContextConfig

    config: ContextConfig | None = vars.get('config', None)
    if config is None:
        config = ContextConfig(config_path='config.json')
        vars.set('config', config)        
    c = config.current
    return c

def produce_solution() -> 'ProduceSolution':
    """获取当前培育方案"""
    from kaa.config.produce import ProduceSolutionManager

    id = conf().produce.selected_solution_id
    if id is None:
        raise NoProduceSolutionSelectedError()
    # TODO: 这里需要缓存，不能每次都从磁盘读取
    return ProduceSolutionManager().read(id)