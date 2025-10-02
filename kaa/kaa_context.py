from kotonebot.backend.context import vars
from kotonebot.client.host import Instance

def _set_instance(new_instance: Instance) -> None:
    vars.set('instance', new_instance)

def instance() -> Instance:
    return vars.get('instance')