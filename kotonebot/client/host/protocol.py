import time
import socket
from abc import ABC, abstractmethod
from typing import Callable, TypeVar, Protocol, Any, Generic
from dataclasses import dataclass

from adbutils import adb, AdbTimeout, AdbError
from adbutils._device import AdbDevice

from kotonebot import logging
from kotonebot.client import Device, DeviceImpl

from kotonebot.util import Countdown, Interval

logger = logging.getLogger(__name__)
# https://github.com/python/typing/issues/769#issuecomment-903760354
_T = TypeVar("_T")
def copy_type(_: _T) -> Callable[[Any], _T]:
    return lambda x: x

# --- 定义专用的 HostConfig 数据类 ---
@dataclass
class AdbHostConfig:
    """由外部为基于 ADB 的主机提供的配置。"""
    timeout: float = 180

@dataclass
class WindowsHostConfig:
    """由外部为 Windows 实现提供配置。"""
    window_title: str
    ahk_exe_path: str

@dataclass
class RemoteWindowsHostConfig:
    """由外部为远程 Windows 实现提供配置。"""
    windows_host_config: WindowsHostConfig
    host: str
    port: int

# --- 使用泛型改造 Instance 协议 ---
T_HostConfig = TypeVar("T_HostConfig")

def tcp_ping(host: str, port: int, timeout: float = 1.0) -> bool:
    """
    通过 TCP ping 检查主机和端口是否可达。
    
    :param host: 主机名或 IP 地址
    :param port: 端口号
    :param timeout: 超时时间（秒）
    :return: 如果主机和端口可达，则返回 True，否则返回 False
    """
    logger.debug('TCP ping %s:%d...', host, port)
    try:
        with socket.create_connection((host, port), timeout):
            logger.debug('TCP ping %s:%d success.', host, port)
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        logger.debug('TCP ping %s:%d failed.', host, port)
        return False


class Instance(Generic[T_HostConfig], ABC):
    """
    代表一个可运行环境的实例（如一个模拟器）。
    使用泛型来约束 create_device 方法的配置参数类型。
    """
    def __init__(self,
        id: str,
        name: str,
        adb_port: int | None = None,
        adb_ip: str = '127.0.0.1',
        adb_name: str | None = None
    ):
        self.id: str = id
        self.name: str = name
        self.adb_port: int | None = adb_port
        self.adb_ip: str = adb_ip
        self.adb_name: str | None = adb_name

    def require_adb_port(self) -> int:
        if self.adb_port is None:
            raise ValueError("ADB port is not set and is required.")
        return self.adb_port

    @abstractmethod
    def refresh(self):
        """
        刷新实例信息，如 ADB 端口号等。
        """
        raise NotImplementedError()

    @abstractmethod
    def start(self):
        """
        启动模拟器实例。
        """
        raise NotImplementedError()

    @abstractmethod
    def stop(self):
        """
        停止模拟器实例。
        """
        raise NotImplementedError()

    @abstractmethod
    def running(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def create_device(self, impl: DeviceImpl, host_config: T_HostConfig) -> Device:
        """
        根据实现名称和类型化的主机配置创建设备。

        :param impl: 设备实现的名称。
        :param host_config: 一个类型化的数据对象，包含创建所需的所有外部配置。
        :return: 配置好的 Device 实例。
        """
        raise NotImplementedError()

    def wait_available(self, timeout: float = 180):
        logger.info('Starting to wait for emulator %s(127.0.0.1:%d) to be available...', self.name, self.adb_port)
        state = 0
        port = self.require_adb_port() 
        emulator_name = self.adb_name
        cd = Countdown(timeout)
        it = Interval(1)
        d: AdbDevice | None = None
        while True:
            if cd.expired():
                raise TimeoutError(f'Emulator "{self.name}" is not available.')
            it.wait()
            try:
                match state:
                    case 0:
                        logger.debug('Ping emulator %s(127.0.0.1:%d)...', self.name, port)
                        if tcp_ping('127.0.0.1', port):
                            logger.debug('Ping emulator %s(127.0.0.1:%d) success.', self.name, port)
                            state = 1
                    case 1:
                        logger.debug('Connecting to emulator %s(127.0.0.1:%d)...', self.name, port)
                        if adb.connect(f'127.0.0.1:{port}', timeout=0.5):
                            logger.debug('Connect to emulator %s(127.0.0.1:%d) success.', self.name, port)
                            state = 2
                    case 2:
                        logger.debug('Getting device list...')
                        if devices := adb.device_list():
                            logger.debug('Get device list success. devices=%s', devices)
                            # emulator_name 用于适配雷电模拟器
                            # 雷电模拟器启动后，在上方的列表中并不会出现 127.0.0.1:5555，而是 emulator-5554
                            d = next(
                                (d for d in devices if d.serial == f'127.0.0.1:{port}' or d.serial == emulator_name),
                                None
                            )
                            if d:
                                logger.debug('Get target device success. d=%s', d)
                                state = 3
                    case 3:
                        if not d:
                            logger.warning('Device is None.')
                            state = 0
                            continue
                        logger.debug('Waiting for device state...')
                        if d.get_state() == 'device':
                            logger.debug('Device state ready. state=%s', d.get_state())
                            state = 4
                    case 4:
                        logger.debug('Waiting for device boot completed...')
                        if not d:
                            logger.warning('Device is None.')
                            state = 0
                            continue
                        ret = d.shell('getprop sys.boot_completed')
                        if isinstance(ret, str) and ret.strip() == '1':
                            logger.debug('Device boot completed. ret=%s', ret)
                            state = 5
                    case 5:
                        if not d:
                            logger.warning('Device is None.')
                            state = 0
                            continue
                        app = d.app_current()
                        logger.debug('Waiting for launcher... (current=%s)', app)
                        if app and 'launcher' in app.package:
                            logger.info('Emulator %s(127.0.0.1:%d) now is available.', self.name, self.adb_port)
                            state = 6
                    case 6:
                        break
            except (AdbError, AdbTimeout):
                state = 1
                continue
        time.sleep(1)
        logger.info('Emulator %s(127.0.0.1:%d) now is available.', self.name, self.adb_port)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(name="{self.name}", id="{self.id}", adb="{self.adb_ip}:{self.adb_port}"({self.adb_name}))'

class HostProtocol(Protocol):
    @staticmethod
    def installed() -> bool: ...
    
    @staticmethod
    def list() -> list[Instance]: ...
    
    @staticmethod
    def query(*, id: str) -> Instance | None: ...


if __name__ == '__main__':
    pass
