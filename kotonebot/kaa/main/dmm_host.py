from importlib import resources
from typing_extensions import override

from kotonebot.client import Device, DeviceImpl
from kotonebot.client.registration import create_device
from kotonebot.client.implements.windows import WindowsImplConfig
from kotonebot.client.implements.remote_windows import RemoteWindowsImplConfig
from kotonebot.client.host import HostProtocol, Instance
from kotonebot.client.host.protocol import WindowsHostConfig, RemoteWindowsHostConfig


DmmHostConfigs = WindowsHostConfig | RemoteWindowsHostConfig

# TODO: 可能应该把 start_game 和 end_game 里对启停的操作移动到这里来
class DmmInstance(Instance[DmmHostConfigs]):
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
    def create_device(self, impl: DeviceImpl, host_config: DmmHostConfigs) -> Device:
        if impl == 'windows':
            assert isinstance(host_config, WindowsHostConfig)
            win_config = WindowsImplConfig(
                window_title=host_config.window_title,
                ahk_exe_path=host_config.ahk_exe_path
            )
            return create_device(impl, win_config)

        elif impl == 'remote_windows':
            assert isinstance(host_config, RemoteWindowsHostConfig)
            config = RemoteWindowsImplConfig(
                windows_impl_config=WindowsImplConfig(
                    window_title=host_config.windows_host_config.window_title,
                    ahk_exe_path=host_config.windows_host_config.ahk_exe_path
                ),
                host=host_config.host,
                port=host_config.port
            )
            return create_device(impl, config)

        else:
            raise ValueError(f'Unsupported impl for DMM: {impl}')

class DmmHost(HostProtocol):
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
