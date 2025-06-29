import io
import os
import zipfile
import logging
import traceback
import importlib.metadata
from datetime import datetime
from typing_extensions import override

import cv2

from ...client import Device
from kotonebot.ui import user
from kotonebot import KotoneBot
from ..util.paths import get_ahk_path
from ..kaa_context import _set_instance
from .dmm_host import DmmHost, DmmInstance
from ..common import BaseConfig, upgrade_config
from kotonebot.config.base_config import UserConfig
from kotonebot.client.host import (
    Mumu12Host, LeidianHost, Mumu12Instance,
    LeidianInstance, CustomInstance
)
from kotonebot.client.host.protocol import (
    Instance, AdbHostConfig, WindowsHostConfig,
    RemoteWindowsHostConfig
)

# 初始化日志
log_formatter = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.CRITICAL)

log_stream = io.StringIO()
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s'))

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

logging.getLogger("kotonebot").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# 升级配置
upgrade_msg = upgrade_config()

class Kaa(KotoneBot):
    """
    琴音小助手 kaa 主类。由其他 GUI/TUI 调用。
    """
    def __init__(self, config_path: str):
        super().__init__(module='kotonebot.kaa.tasks', config_path=config_path, config_type=BaseConfig)
        self.upgrade_msg = upgrade_msg
        self.version = importlib.metadata.version('ksaa')
        logger.info('Version: %s', self.version)

    def add_file_logger(self, log_path: str):
        log_dir = os.path.abspath(os.path.dirname(log_path))
        os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)

    def set_log_level(self, level: int):
        console_handler.setLevel(level)

    def dump_error_report(
        self,
        exception: Exception,
        *,
        path: str | None = None
    ) -> str:
        """
        保存错误报告

        :param path: 保存的路径。若为 `None`，则保存到 `./reports/{YY-MM-DD HH-MM-SS}.zip`。
        :return: 保存的路径
        """
        from kotonebot import device
        from kotonebot.backend.context import current_callstack
        try:
            if path is None:
                path = f'./reports/{datetime.now().strftime("%Y-%m-%d %H-%M-%S")}.zip'
            exception_msg = '\n'.join(traceback.format_exception(exception))
            task_callstack = '\n'.join(
                [f'{i + 1}. name={task.name} priority={task.priority}' for i, task in enumerate(current_callstack)])
            screenshot = device.screenshot()
            logs = log_stream.getvalue()
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with zipfile.ZipFile(path, 'w') as zipf:
                zipf.writestr('exception.txt', exception_msg)
                zipf.writestr('task_callstack.txt', task_callstack)
                zipf.writestr('screenshot.png', cv2.imencode('.png', screenshot)[1].tobytes())
                zipf.writestr('config.json', config_content)
                zipf.writestr('logs.txt', logs)
            return path
        except Exception as e:
            logger.exception('Failed to save error report:')
            return ''

    @override
    def _on_after_init_context(self):
        if self.backend_instance is None:
            raise ValueError('Backend instance is not set.')
        _set_instance(self.backend_instance)

    def __get_backend_instance(self, config: UserConfig) -> Instance:
        """
        根据配置获取或创建 Instance。

        :param config: 用户配置对象
        :return: 后端实例
        """
        from kotonebot.client.host import create_custom

        logger.info(f'Querying for backend: {config.backend.type}')

        if config.backend.type == 'custom':
            exe = config.backend.emulator_path
            instance = create_custom(
                adb_ip=config.backend.adb_ip,
                adb_port=config.backend.adb_port,
                adb_name=config.backend.adb_emulator_name,
                exe_path=exe,
                emulator_args=config.backend.emulator_args
            )
            # 对于 custom 类型，需要额外验证模拟器路径
            if config.backend.check_emulator:
                if exe is None:
                    user.error('「检查并启动模拟器」已开启但未配置「模拟器 exe 文件路径」。')
                    raise ValueError('Emulator executable path is not set.')
                if not os.path.exists(exe):
                    user.error('「模拟器 exe 文件路径」对应的文件不存在！请检查路径是否正确。')
                    raise FileNotFoundError(f'Emulator executable not found: {exe}')
            return instance

        elif config.backend.type == 'mumu12':
            if config.backend.instance_id is None:
                raise ValueError('MuMu12 instance ID is not set.')
            instance = Mumu12Host.query(id=config.backend.instance_id)
            if instance is None:
                raise ValueError(f'MuMu12 instance not found: {config.backend.instance_id}')
            return instance

        elif config.backend.type == 'leidian':
            if config.backend.instance_id is None:
                raise ValueError('Leidian instance ID is not set.')
            instance = LeidianHost.query(id=config.backend.instance_id)
            if instance is None:
                raise ValueError(f'Leidian instance not found: {config.backend.instance_id}')
            return instance

        elif config.backend.type == 'dmm':
            return DmmHost.instance

        else:
            raise ValueError(f'Unsupported backend type: {config.backend.type}')

    def __ensure_instance_running(self, instance: Instance, config: UserConfig):
        """
        确保 Instance 正在运行。

        :param instance: 后端实例
        :param config: 用户配置对象
        """
        # DMM 实例不需要启动，直接返回
        if isinstance(instance, DmmInstance):
            logger.info('DMM backend does not require startup.')
            return

        # 对所有需要启动的后端（custom, mumu, leidian）使用统一逻辑
        if config.backend.check_emulator and not instance.running():
            logger.info(f'Starting backend "{instance}"...')
            instance.start()
            logger.info(f'Waiting for backend "{instance}" to be available...')
            instance.wait_available()
        else:
            logger.info(f'Backend "{instance}" already running or check is disabled.')

    @override
    def _on_create_device(self) -> Device:
        """
        创建设备。
        """
        from kotonebot.config.manager import load_config

        # 步骤1：加载配置
        config = load_config(self.config_path, type=self.config_type)
        user_config = config.user_configs[0]  # HACK: 硬编码

        # 步骤2：获取实例
        self.backend_instance = self.__get_backend_instance(user_config)
        if self.backend_instance is None:
            raise RuntimeError(f"Failed to find instance for backend '{user_config.backend.type}'")

        # 步骤3：确保实例运行
        self.__ensure_instance_running(self.backend_instance, user_config)

        # 步骤4：准备 HostConfig 并创建 Device
        impl_name = user_config.backend.screenshot_impl

        if isinstance(self.backend_instance, DmmInstance):
            if impl_name == 'windows':
                ahk_path = get_ahk_path()
                host_conf = WindowsHostConfig(
                    window_title='gakumas',
                    ahk_exe_path=ahk_path
                )
            elif impl_name == 'remote_windows':
                ahk_path = get_ahk_path()
                host_conf = RemoteWindowsHostConfig(
                    windows_host_config=WindowsHostConfig(
                        window_title='gakumas',
                        ahk_exe_path=ahk_path
                    ),
                    host=user_config.backend.adb_ip,
                    port=user_config.backend.adb_port
                )
            else:
                raise ValueError(f"Impl of '{impl_name}' is not supported on DMM.")
            return self.backend_instance.create_device(impl_name, host_conf)

        # 统一处理所有基于 ADB 的后端
        elif isinstance(self.backend_instance, (CustomInstance, Mumu12Instance, LeidianInstance)):
            if impl_name in ['adb', 'adb_raw', 'uiautomator2']:
                host_conf = AdbHostConfig(timeout=180)
                return self.backend_instance.create_device(impl_name, host_conf)
            else:
                raise ValueError(f"{user_config.backend.type} backend does not support implementation '{impl_name}'")

        else:
            raise TypeError(f"Unknown instance type: {type(self.backend_instance)}")