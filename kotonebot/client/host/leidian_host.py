import os
import subprocess
from typing import cast
from functools import lru_cache
from typing_extensions import override

from kotonebot import logging
from kotonebot.client import DeviceImpl
from kotonebot.client.device import Device
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

class LeidianInstance(Instance[AdbHostConfig]):
    @copy_type(Instance.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._args = args
        self.index: int | None = None
        self.is_running: bool = False

    @override
    def refresh(self):
        ins = LeidianHost.query(id=self.id)
        assert isinstance(ins, LeidianInstance), f'Expected LeidianInstance, got {type(ins)}'
        if ins is not None:
            self.adb_port = ins.adb_port
            self.adb_ip = ins.adb_ip
            self.adb_name = ins.adb_name
            self.is_running = ins.is_running
            logger.debug('Refreshed Leidian instance: %s', repr(ins))

    @override
    def start(self):
        if self.running():
            logger.warning('Instance is already running.')
            return
        logger.info('Starting Leidian instance %s', self)
        LeidianHost._invoke_manager(['launch', '--index', str(self.index)])
        self.refresh()

    @override
    def stop(self):
        if not self.running():
            logger.warning('Instance is not running.')
            return
        logger.info('Stopping Leidian instance id=%s name=%s...', self.id, self.name)
        LeidianHost._invoke_manager(['quit', '--index', str(self.index)])
        self.refresh()

    @override
    def wait_available(self, timeout: float = 180):
        cd = Countdown(timeout)
        it = Interval(5)
        while not cd.expired() and not self.running():
            it.wait()
        if not self.running():
            raise TimeoutError(f'Leidian instance "{self.name}" is not available.')

    @override
    def running(self) -> bool:
        result = LeidianHost._invoke_manager(['isrunning', '--index', str(self.index)])
        return result.strip() == 'running'

    @override
    def create_device(self, impl: DeviceImpl, host_config: AdbHostConfig) -> Device:
        """为雷电模拟器实例创建 Device。"""
        if self.adb_port is None:
            raise ValueError("ADB port is not set and is required.")

        # 为 ADB 相关的实现创建配置
        if impl in ['adb', 'adb_raw', 'uiautomator2']:
            config = AdbImplConfig(
                addr=f'{self.adb_ip}:{self.adb_port}',
                connect=False,  # 雷电模拟器不需要 adb connect
                disconnect=False,
                device_serial=self.adb_name,
                timeout=host_config.timeout
            )
            impl = cast(AdbBasedImpl, impl) # make pylance happy
            return create_device(impl, config)
        else:
            raise ValueError(f'Unsupported device implementation for Leidian: {impl}')

class LeidianHost(HostProtocol):
    @staticmethod
    @lru_cache(maxsize=1)
    def _read_install_path() -> str | None:
        """
        从注册表中读取雷电模拟器的安装路径。

        :return: 安装路径，如果未找到则返回 None。
        """
        if os.name != 'nt':
            return None

        try:
            icon_path = read_reg('HKCU', r'Software\leidian\LDPlayer9', 'DisplayIcon', default=None)
            if icon_path and isinstance(icon_path, str):
                icon_path = icon_path.replace('"', '')
                path = os.path.dirname(icon_path)
                logger.debug('Leidian installation path (from DisplayIcon): %s', path)
                return path
            install_dir = read_reg('HKCU', r'Software\leidian\LDPlayer9', 'InstallDir', default=None)
            if install_dir and isinstance(install_dir, str):
                install_dir = install_dir.replace('"', '')
                logger.debug('Leidian installation path (from InstallDir): %s', install_dir)
                return install_dir
        except Exception as e:
            logger.error(f'Failed to read Leidian installation path from registry: {e}')

        return None

    @staticmethod
    def _invoke_manager(args: list[str]) -> str:
        """
        调用 ldconsole.exe。
        
        参考文档：https://www.ldmnq.com/forum/30.html，以及命令行帮助。
        另外还有个 ld.exe，封装了 adb.exe，可以直接执行 adb 命令。（https://www.ldmnq.com/forum/9178.html）

        :param args: 命令行参数列表。
        :return: 命令执行的输出。
        """
        install_path = LeidianHost._read_install_path()
        if install_path is None:
            raise RuntimeError('Leidian is not installed.')
        manager_path = os.path.join(install_path, 'ldconsole.exe')
        logger.debug('ldconsole execute: %s', repr(args))
        output = subprocess.run(
            [manager_path] + args,
            capture_output=True,
            text=True,
            # encoding='utf-8', # 居然不是 utf-8 编码
            # https://stackoverflow.com/questions/6011235/run-a-program-from-python-and-have-it-continue-to-run-after-the-script-is-kille
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        if output.returncode != 0:
            raise RuntimeError(f'Failed to invoke ldconsole: {output.stderr}')
        return output.stdout

    @staticmethod
    def installed() -> bool:
        return LeidianHost._read_install_path() is not None

    @staticmethod
    def list() -> list[Instance]:
        output = LeidianHost._invoke_manager(['list2'])
        instances = []

        # 解析 list2 命令的输出
        # 格式: 索引,标题,顶层窗口句柄,绑定窗口句柄,是否进入android,进程PID,VBox进程PID
        for line in output.strip().split('\n'):
            if not line:
                continue

            parts = line.split(',')
            if len(parts) < 5:
                logger.warning(f'Invalid list2 output line: {line}')
                continue

            index = parts[0]
            name = parts[1]
            is_android_started = parts[4] == '1'
            # 端口号规则 https://help.ldmnq.com/docs/LD9adbserver#a67730c2e7e2e0400d40bcab37d0e0cf
            adb_port = 5554 + (int(index) * 2)

            instance = LeidianInstance(
                id=index,
                name=name,
                adb_port=adb_port,
                adb_ip='127.0.0.1',
                adb_name=f'emulator-{adb_port}'
            )
            instance.index = int(index)
            instance.is_running = is_android_started
            logger.debug('Leidian instance: %s', repr(instance))
            instances.append(instance)

        return instances

    @staticmethod
    def query(*, id: str) -> Instance | None:
        instances = LeidianHost.list()
        for instance in instances:
            if instance.id == id:
                return instance
        return None

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    print(LeidianHost._read_install_path())
    print(LeidianHost.installed())
    print(LeidianHost.list())
    print(ins:=LeidianHost.query(id='0'))
    assert isinstance(ins, LeidianInstance)
    ins.start()
    ins.wait_available()
    print('status', ins.running(), ins.adb_port, ins.adb_ip)
    # ins.stop()
    # print('status', ins.running(), ins.adb_port, ins.adb_ip)