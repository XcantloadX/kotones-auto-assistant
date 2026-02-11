# ruff: noqa: E402
import sys
import logging
import importlib.metadata
from typing import Any, cast, Callable

from kotonebot.core.bot import BotContext, KotoneBot
from kotonebot.backend.context import Task
from kotonebot.client.device import Device, WindowsDevice
from kotonebot.client.host import (
    Mumu12Host, LeidianHost, Mumu12Instance,
    LeidianInstance, CustomInstance
)
from kotonebot.client.host.mumu12_host import Mumu12V5Host, MuMu12HostConfig
from kotonebot.client.host.protocol import Instance, AdbHostConfig
from kaa.config.base_config import UserConfig
from kaa.config.manager import load_config
from kaa.config import BaseConfig, upgrade_config
from kotonebot.primitives.geometry import Size
from kotonebot.ui import user
from kotonebot.util import is_windows
from kaa.errors import WindowsOnlyError
from ..util.paths import get_ahk_path
from ..kaa_context import _set_instance
from kaa.tasks import POST_TASK_REGISTRY, TASK_FUNCTIONS
from kotonebot.errors import ContextNotInitializedError, UserFriendlyError, StopCurrentTask
from kotonebot.core import NextHandler

if is_windows():
    from .dmm_host import DmmHost, DmmInstance
else:
    DmmHost = DmmInstance = None

logger = logging.getLogger(__name__)


def windows_gui_error_middleware(ctx: BotContext, task: Task, next_handler: NextHandler):
    """负责处理 UserFriendlyError 并弹出 Windows 对话框"""
    try:
        next_handler()
    except UserFriendlyError as e:
        ctx.has_error = True
        ctx.last_exception = e
        logger.error(f"Task {task.name} failed: {e.message}")
        
        if is_windows():
            try:
                from kotonebot.interop.win.task_dialog import TaskDialog
                dialog = TaskDialog(
                    title='琴音小助手',
                    main_instruction='任务执行失败',
                    content=e.message,
                    custom_buttons=e.action_buttons,
                    main_icon='error'
                )
                res, _, _ = dialog.show()
                e.invoke(res)
            except ImportError:
                pass
            ctx.stop()
    
    except Exception as e:
        # 处理非用户友好错误
        ctx.has_error = True
        ctx.last_exception = e
        logger.error(f"System Error in {task.name}: {e}", exc_info=True)
        pass


class KaaDeviceFactory:
    def __init__(self):
        self.config_path = './config.json'
        self.backend_instance: Instance | None = None
        self.target_screenshot_interval: float | None = None

    def __call__(self) -> Device:
        config = load_config(self.config_path, type=BaseConfig)
        user_config = config.user_configs[0]
        self.target_screenshot_interval = user_config.backend.target_screenshot_interval
        self._setup_global_device_conf()
        self.backend_instance = self._get_backend_instance(user_config)
        self._ensure_instance_running(self.backend_instance, user_config)
        return self._create_device_impl(self.backend_instance, user_config)

    def _setup_global_device_conf(self):
        from kotonebot.config.config import conf
        from kotonebot.client.scaler import PortraitGameScaler
        conf().device.default_scaler_factory = lambda: PortraitGameScaler()
        conf().device.default_logic_resolution = Size(720, 1280)

    def _get_backend_instance(self, config: UserConfig) -> Instance:
        """
        根据配置获取或创建 Instance。

        :param config: 用户配置对象
        :return: 后端实例
        """
        from kotonebot.client.host import create_custom
        logger.info(f'Querying for backend: {config.backend.type}')
        
        b_type = config.backend.type
        
        if b_type == 'custom':
            exe = config.backend.emulator_path
            instance = create_custom(
                adb_ip=config.backend.adb_ip,
                adb_port=config.backend.adb_port,
                adb_name=config.backend.adb_emulator_name,
                exe_path=exe,
                emulator_args=config.backend.emulator_args
            )
            if config.backend.check_emulator:
                import os
                if exe is None:
                    user.error('「检查并启动模拟器」已开启但未配置「模拟器 exe 文件路径」。')
                    raise ValueError('Emulator executable path is not set.')
                if not os.path.exists(exe):
                    user.error('「模拟器 exe 文件路径」对应的文件不存在！请检查路径是否正确。')
                    raise FileNotFoundError(f'Emulator executable not found: {exe}')
            return instance

        elif b_type == 'mumu12':
            if config.backend.instance_id is None:
                raise ValueError('MuMu12 instance ID is not set.')
            instance = Mumu12Host.query(id=config.backend.instance_id)
            if instance is None:
                raise ValueError(f'MuMu12 instance not found: {config.backend.instance_id}')
            return instance

        elif b_type == 'mumu12v5':
            if config.backend.instance_id is None:
                raise ValueError('MuMu12v5 instance ID is not set.')
            instance = Mumu12V5Host.query(id=config.backend.instance_id)
            if instance is None:
                raise ValueError(f'MuMu12v5 instance not found: {config.backend.instance_id}')
            return instance

        elif b_type == 'leidian':
            if config.backend.instance_id is None:
                raise ValueError('Leidian instance ID is not set.')
            instance = LeidianHost.query(id=config.backend.instance_id)
            if instance is None:
                raise ValueError(f'Leidian instance not found: {config.backend.instance_id}')
            return instance

        elif b_type == 'dmm':
            if not is_windows():
                raise WindowsOnlyError('DMM 版')
            assert DmmHost is not None
            return DmmHost.instance

        else:
            raise ValueError(f'Unsupported backend type: {b_type}')

    def _ensure_instance_running(self, instance: Instance, config: UserConfig):
        """
        确保 Instance 正在运行。

        :param instance: 后端实例
        :param config: 用户配置对象
        """
        if DmmInstance and isinstance(instance, DmmInstance):
            logger.info('DMM backend does not require startup.')
            return

        if config.backend.check_emulator and not instance.running():
            logger.info(f'Starting backend "{instance}"...')
            instance.start()
            logger.info(f'Waiting for backend "{instance}" to be available...')
            instance.wait_available()
        else:
            logger.info(f'Backend "{instance}" already running or check is disabled.')

    def _create_device_impl(self, instance: Instance, config: UserConfig) -> Device:
        """
        创建设备。
        """
        impl_name = config.backend.screenshot_impl
        
        if DmmInstance and isinstance(instance, DmmInstance):
            d = WindowsDevice()
            if impl_name == 'windows':
                from kotonebot.client.implements.windows import WindowsImpl
                ahk_path = get_ahk_path()
                impl = WindowsImpl(device=d, window_title='gakumas', ahk_exe_path=ahk_path)
                d._screenshot = impl
                d._touch = impl
            elif impl_name == 'remote_windows':
                from kotonebot.client.implements.remote_windows import RemoteWindowsImpl
                impl = RemoteWindowsImpl(device=d, host=config.backend.adb_ip, port=config.backend.adb_port)
                d._screenshot = impl
                d._touch = impl
            elif impl_name == 'windows_background':
                from kotonebot.client.implements.windows.send_message import SendMessageImpl
                from kotonebot.client.implements.windows.print_window import PrintWindowImpl
                d._screenshot = PrintWindowImpl(d, 'gakumas')
                d._touch = SendMessageImpl(d, 'gakumas', wait_cursor_idle=config.backend.cursor_wait_speed)
            else:
                raise ValueError(f"Impl of '{impl_name}' is not supported on DMM.")
            return d

        elif isinstance(instance, (CustomInstance, Mumu12Instance, LeidianInstance)):
            if impl_name == 'nemu_ipc' and isinstance(instance, Mumu12Instance):
                options = cast(BaseConfig, config.options)
                timeout = 180
                args = {}
                if config.backend.mumu_background_mode:
                    args = {
                        "display_id": None,
                        "target_package_name": options.start_game.game_package_name,
                        "app_index": 0
                    }
                host_conf = MuMu12HostConfig(timeout=timeout, **args)
                return instance.create_device(cast(Any, impl_name), host_conf)
            
            elif impl_name in ['adb', 'adb_raw', 'uiautomator2']:
                host_conf = AdbHostConfig(timeout=180)
                return instance.create_device(cast(Any, impl_name), host_conf)
            else:
                raise ValueError(f"{config.backend.type} backend does not support implementation '{impl_name}'")
        else:
            raise TypeError(f"Unknown instance type: {type(instance)}")

def sentry_middleware(ctx: BotContext, task: Task, next_handler: Callable[[], None]):
    try:
        next_handler()
    except Exception as e:
        from kaa.util.telemetry import use_sentry
        sentry_sdk = use_sentry()
        with sentry_sdk.push_scope() as scope:
            scope.set_tag('task_name', task.name)
            try:
                with open('./config.json', 'r', encoding='utf-8') as f:
                    scope.set_extra('config', f.read())
            except Exception:
                logger.warning('Failed to attach config to Sentry report.', exc_info=True)
            try:
                from kotonebot.backend.context import ContextStackVars
                stack = ContextStackVars.current()
                if stack and stack._screenshot is not None:
                    import cv2
                    buff = cv2.imencode('.png', stack._screenshot)[1].tobytes()
                    scope.add_attachment(bytes=buff, filename="last_screenshot.png")
            except Exception:
                logger.warning('Failed to attach screenshot to Sentry report.', exc_info=True)
            try:
                from kotonebot import device
                screenshot = device.screenshot()
                import cv2
                buff = cv2.imencode('.png', screenshot)[1].tobytes()
                scope.add_attachment(bytes=buff, filename="screenshot_at_exception.png")
            except Exception:
                logger.warning('Failed to attach device screenshot to Sentry report.', exc_info=True)
            sentry_sdk.capture_exception(e)
        raise

class Kaa(KotoneBot):
    """
    琴音小助手 kaa 主类。由其他 GUI/TUI 调用。
    """
    def __init__(self, config_path: str):
        self.upgrade_msg = upgrade_config()
        self.version = importlib.metadata.version('ksaa')
        
        logger.info('Version: %s', self.version)
        logger.info('Python Version: %s', sys.version)
        logger.info('Python Executable: %s', sys.executable)
        
        self.factory = KaaDeviceFactory()
        
        super().__init__(
            device_factory=self.factory,
            middlewares=[
                sentry_middleware,
                windows_gui_error_middleware
            ]
        )

    def set_log_level(self, level: int):
        handlers = logging.getLogger().handlers
        if len(handlers) == 0:
            print('Warning: No default handler found.')
        else:
            # 第一个 handler 是默认的 StreamHandler
            handlers[0].setLevel(level)

    def _task_generator(self):
        for task in (func.task for func in TASK_FUNCTIONS):
            try:
                yield task
            except Exception:
                break
        yield from (func.task for func in POST_TASK_REGISTRY.values())

    def run_all(self):
        return self.run(self._task_generator())
    
    def start_all(self):
        return self.start(self._task_generator())
    
    def stop(self):
        try:
            from kotonebot.backend.context import vars as context_vars
            flow = context_vars.flow
            flow.request_interrupt()
        except ContextNotInitializedError:
            pass # Context might not be ready if stopping very early
