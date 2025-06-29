import os
import json
import subprocess
from functools import lru_cache
from typing import Any, cast
from typing_extensions import override

from kotonebot import logging
from kotonebot.client import DeviceImpl, Device
from kotonebot.client.registration import AdbBasedImpl, create_device
from kotonebot.client.implements.adb import AdbImplConfig
from kotonebot.util import Countdown, Interval
from .protocol import HostProtocol, Instance, copy_type, AdbHostConfig

logger = logging.getLogger(__name__)

if os.name == 'nt':
    from ...interop.win.reg import read_reg
else:
    def read_reg(key, subkey, name, *, default=None, **kwargs):
        """Stub for read_reg on non-Windows platforms."""
        return default

class Mumu12Instance(Instance[AdbHostConfig]):
    @copy_type(Instance.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._args = args
        self.index: int | None = None
        self.is_android_started: bool = False
    
    @override
    def refresh(self):
        ins = Mumu12Host.query(id=self.id)
        assert isinstance(ins, Mumu12Instance), f'Expected Mumu12Instance, got {type(ins)}'
        if ins is not None:
            self.adb_port = ins.adb_port
            self.adb_ip = ins.adb_ip
            self.adb_name = ins.adb_name
            self.is_android_started = ins.is_android_started
            logger.debug('Refreshed MuMu12 instance: %s', repr(ins))
    
    @override
    def start(self):
        if self.running():
            logger.warning('Instance is already running.')
            return
        logger.info('Starting MuMu12 instance %s', self)
        Mumu12Host._invoke_manager(['control', '-v', self.id, 'launch'])
        self.refresh()
    
    @override
    def stop(self):
        if not self.running():
            logger.warning('Instance is not running.')
            return
        logger.info('Stopping MuMu12 instance id=%s name=%s...', self.id, self.name)
        Mumu12Host._invoke_manager(['control', '-v', self.id, 'shutdown'])
        self.refresh()
    
    @override
    def wait_available(self, timeout: float = 180):
        cd = Countdown(timeout)
        it = Interval(5)
        while not cd.expired() and not self.running():
            it.wait()
            self.refresh()
        if not self.running():
            raise TimeoutError(f'MuMu12 instance "{self.name}" is not available.')
    
    @override
    def running(self) -> bool:
        return self.is_android_started

    @override
    def create_device(self, impl: DeviceImpl, host_config: AdbHostConfig) -> Device:
        """为MuMu12模拟器实例创建 Device。"""
        if self.adb_port is None:
            raise ValueError("ADB port is not set and is required.")

        # 为 ADB 相关的实现创建配置
        if impl in ['adb', 'adb_raw', 'uiautomator2']:
            config = AdbImplConfig(
                addr=f'{self.adb_ip}:{self.adb_port}',
                connect=True,
                disconnect=True,
                device_serial=self.adb_name,
                timeout=host_config.timeout
            )
            impl = cast(AdbBasedImpl, impl) # make pylance happy
            return create_device(impl, config)
        else:
            raise ValueError(f'Unsupported device implementation for MuMu12: {impl}')

class Mumu12Host(HostProtocol):
    @staticmethod
    @lru_cache(maxsize=1)
    def _read_install_path() -> str | None:
        """
        Reads the installation path (DisplayIcon) of MuMu Player 12 from the registry.

        :return: The path to the display icon if found, otherwise None.
        """
        if os.name != 'nt':
            return None

        uninstall_subkeys = [
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MuMuPlayer-12.0',
            # TODO: 支持国际版 MuMu
            # r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MuMuPlayerGlobal-12.0'
        ]

        for subkey in uninstall_subkeys:
            icon_path = read_reg('HKLM', subkey, 'DisplayIcon', default=None)
            if icon_path and isinstance(icon_path, str):
                icon_path = icon_path.replace('"', '')
                path = os.path.dirname(icon_path)
                logger.debug('MuMu Player 12 installation path: %s', path)
                return path
        return None

    @staticmethod
    def _invoke_manager(args: list[str]) -> str:
        """
        调用 MuMuManager.exe。
        
        :param args: 命令行参数列表。
        :return: 命令执行的输出。
        """
        install_path = Mumu12Host._read_install_path()
        if install_path is None:
            raise RuntimeError('MuMu Player 12 is not installed.')
        manager_path = os.path.join(install_path, 'MuMuManager.exe')
        logger.debug('MuMuManager execute: %s', repr(args))
        output = subprocess.run(
            [manager_path] + args,
            capture_output=True,
            text=True,
            encoding='utf-8',
            # https://stackoverflow.com/questions/6011235/run-a-program-from-python-and-have-it-continue-to-run-after-the-script-is-kille
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        if output.returncode != 0:
            # raise RuntimeError(f'Failed to invoke MuMuManager: {output.stderr}')
            logger.warning('Failed to invoke MuMuManager: %s', output.stderr)
        return output.stdout

    @staticmethod
    def installed() -> bool:
        return Mumu12Host._read_install_path() is not None

    @staticmethod
    def list() -> list[Instance]:
        output = Mumu12Host._invoke_manager(['info', '-v', 'all'])
        logger.debug('MuMuManager.exe output: %s', output)
        
        try:
            data: dict[str, dict[str, Any]] = json.loads(output)
            if 'name' in data.keys():
                # 这里有个坑：
                # 如果只有一个实例，返回的 JSON 结构是单个对象而不是数组
                data = { '0': data }
            instances = []
            for index, instance_data in data.items():
                instance = Mumu12Instance(
                    id=index,
                    name=instance_data['name'],
                    adb_port=instance_data.get('adb_port'),  
                    adb_ip=instance_data.get('adb_host_ip', '127.0.0.1'), 
                    adb_name=None
                )
                instance.index = int(index)
                instance.is_android_started = instance_data.get('is_android_started', False)
                logger.debug('Mumu12 instance: %s', repr(instance))
                instances.append(instance)
            return instances
        except json.JSONDecodeError as e:
            raise RuntimeError(f'Failed to parse output: {e}')
    
    @staticmethod
    def query(*, id: str) -> Instance | None:
        instances = Mumu12Host.list()
        for instance in instances:
            if instance.id == id:
                return instance
        return None
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    print(Mumu12Host._read_install_path())
    print(Mumu12Host.installed())
    print(Mumu12Host.list())
    print(ins:=Mumu12Host.query(id='2'))
    assert isinstance(ins, Mumu12Instance)
    ins.start()
    ins.wait_available()
    print('status', ins.running(), ins.adb_port, ins.adb_ip)
    ins.stop()
    print('status', ins.running(), ins.adb_port, ins.adb_ip)
