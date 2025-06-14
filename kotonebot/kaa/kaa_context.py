from dataclasses import dataclass

from kotonebot.backend.context import vars
from kotonebot.client.host import Instance
from kotonebot.kaa.common import ProduceMode

@dataclass
class ProduceSession:
    mode: ProduceMode
    
    @property
    def is_nia(self) -> bool:
        return self.mode.startswith('nia')
    
    @property
    def is_hajime(self) -> bool:
        return not self.is_nia

def _set_instance(new_instance: Instance) -> None:
    vars.set('instance', new_instance)

def instance() -> Instance:
    return vars.get('instance')

def set_produce(new_session: ProduceSession) -> None:
    vars.set('produce_session', new_session)

def produce() -> ProduceSession:
    return vars.get('produce_session')