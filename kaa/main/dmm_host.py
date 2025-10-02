from typing_extensions import override

from kotonebot.client import Device
from kotonebot.client.host import HostProtocol, Instance
from kotonebot.client.host.windows_common import WindowsRecipes, WindowsHostConfigs, CommonWindowsCreateDeviceMixin


DmmHostConfigs = WindowsHostConfigs
DmmRecipes = WindowsRecipes

# TODO: 可能应该把 start_game 和 end_game 里对启停的操作移动到这里来
class DmmInstance(CommonWindowsCreateDeviceMixin, Instance[DmmHostConfigs]):
    def __init__(self):
        super().__init__('dmm', 'gakumas')

    @override
    def refresh(self):
        raise NotImplementedError()

    @override
    def start(self):
        raise NotImplementedError()

    @override
    def stop(self):
        raise NotImplementedError()

    @override
    def running(self) -> bool:
        raise NotImplementedError()

    @override
    def wait_available(self, timeout: float = 180):
        raise NotImplementedError()

    @override
    def create_device(self, impl: DmmRecipes, host_config: DmmHostConfigs) -> Device:
        """为 DMM 实例创建 Device。"""
        return super().create_device(impl, host_config)

class DmmHost(HostProtocol[DmmRecipes]):
    instance = DmmInstance()
    """DmmInstance 单例。"""

    @staticmethod
    def installed() -> bool:
        # TODO: 应该检查 DMM 和 gamkumas 的安装情况
        raise NotImplementedError()

    @staticmethod
    def list() -> list[Instance]:
        raise NotImplementedError()

    @staticmethod
    def query(*, id: str) -> Instance | None:
        raise NotImplementedError()

    @staticmethod
    def recipes() -> 'list[DmmRecipes]':
        return ['windows', 'remote_windows']
