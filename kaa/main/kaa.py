# ruff: noqa: E402
import sys
import logging
import importlib.metadata
from typing import Any, cast, Callable, Iterable

from kotonebot.core.bot import BotContext, KotoneBot
from kotonebot.backend.context import Task
from kotonebot.client.device import Device, WindowsDevice
from kotonebot.client.host import (
    Mumu12Host, LeidianHost, Mumu12Instance,
    LeidianInstance, CustomInstance
)
from kotonebot.client.host.mumu12_host import Mumu12V5Host, MuMu12HostConfig
from kotonebot.client.host.protocol import Instance, AdbHostConfig
from kaa.config.schema import KaaConfig
from kaa.config import upgrade_config
from kaa.config import manager as config_manager
from kotonebot.primitives.geometry import Size
from kotonebot.ui import user
from kotonebot.util import is_windows
from kaa.errors import WindowsOnlyError
from kaa.constants import PLAYCOVER_BUNDLE_ID
from ..util.paths import get_ahk_path
from ..kaa_context import _set_instance
from kaa.tasks import POST_TASK_REGISTRY, TASK_FUNCTIONS
from kotonebot.errors import UserFriendlyError, StopCurrentTask
from kotonebot.core import NextHandler

if is_windows():
    from .dmm_host import DmmHost, DmmInstance
else:
    DmmHost = DmmInstance = None
from kotonebot.primitives.geometry import Size


logger = logging.getLogger(__name__)


def windows_gui_error_middleware(ctx: BotContext, task: Task, next_handler: NextHandler):
    """负责处理 UserFriendlyError 并弹出对话框"""
    try:
        next_handler()
    except UserFriendlyError as e:
        ctx.has_error = True
        ctx.last_exception = e
        logger.error(f"Task {task.name} failed: {e.message}")
        from kaa.application.ui.error_bridge import get_bridge
        bridge = get_bridge()
        if bridge is not None:
            bridge.show(e.message, e.action_buttons, e.invoke)
        ctx.stop()

    except Exception as e:
        # 处理非用户友好错误
        ctx.has_error = True
        ctx.last_exception = e
        logger.error(f"System Error in {task.name}: {e}", exc_info=True)
        pass


class KaaDeviceFactory:
    def __init__(self):
        self.backend_instance: Instance | None = None
        self.target_screenshot_interval: float | None = None

    def __call__(self) -> Device:
        from kaa.kaa_context import conf as get_conf  # noqa: PLC0415
        config = get_conf()
        self.target_screenshot_interval = config.backend.target_screenshot_interval

        from kotonebot.config.config import conf
        from kotonebot.client.scaler import PortraitGameScaler
        conf().device.default_scaler_factory = lambda: PortraitGameScaler()
        conf().device.default_logic_resolution = Size(720, 1280)
        self._setup_global_device_conf()
        self.backend_instance = self._get_backend_instance(config)
        self._ensure_instance_running(self.backend_instance, config)
        return self._create_device_impl(self.backend_instance, config)

    def _setup_global_device_conf(self):
        from kotonebot.config.config import conf
        from kotonebot.client.scaler import PortraitGameScaler
        conf().device.default_scaler_factory = lambda: PortraitGameScaler()
        conf().device.default_logic_resolution = Size(720, 1280)

    def _get_backend_instance(self, config: KaaConfig) -> Any:
        """
        根据配置获取或创建 Instance 或 NativeApp。

        :param config: 用户配置对象
        :return: 后端实例或原生应用实例
        """
        from kotonebot.client.host import create_custom
        from kaa.config.base_config import (  # noqa: PLC0415
            MuMu12Device, MuMu12V5Device, LeidianDevice, DmmDevice, CustomDevice, TcpConnection,
        )
        lc = config.backend.lifecycle
        b_type = lc.type
        logger.info(f'Querying for backend: {b_type}')

        if b_type == 'custom':
            assert isinstance(lc, CustomDevice)
            conn = config.backend.connection
            assert isinstance(conn, TcpConnection)
            exe = lc.emulator_path
            instance = create_custom(
                adb_ip=conn.ip,
                adb_port=conn.port,
                adb_name=None,
                exe_path=exe,
                emulator_args=lc.emulator_args,
            )
            if lc.check_and_start:
                import os
                if exe is None:
                    user.error('「检查并启动模拟器」已开启但未配置「模拟器 exe 文件路径」。')
                    raise ValueError('Emulator executable path is not set.')
                if not os.path.exists(exe):
                    user.error('「模拟器 exe 文件路径」对应的文件不存在！请检查路径是否正确。')
                    raise FileNotFoundError(f'Emulator executable not found: {exe}')
            return instance

        elif b_type == 'mumu12':
            assert isinstance(lc, MuMu12Device)
            if lc.instance_id is None:
                raise ValueError('MuMu12 instance ID is not set.')
            instance = Mumu12Host.query(id=lc.instance_id)
            if instance is None:
                raise ValueError(f'MuMu12 instance not found: {lc.instance_id}')
            return instance

        elif b_type == 'mumu12v5':
            assert isinstance(lc, MuMu12V5Device)
            if lc.instance_id is None:
                raise ValueError('MuMu12v5 instance ID is not set.')
            instance = Mumu12V5Host.query(id=lc.instance_id)
            if instance is None:
                raise ValueError(f'MuMu12v5 instance not found: {lc.instance_id}')
            return instance

        elif b_type == 'leidian':
            assert isinstance(lc, LeidianDevice)
            if lc.instance_id is None:
                raise ValueError('Leidian instance ID is not set.')
            instance = LeidianHost.query(id=lc.instance_id)
            if instance is None:
                raise ValueError(f'Leidian instance not found: {lc.instance_id}')
            return instance

        elif b_type == 'dmm':
            if not is_windows():
                raise WindowsOnlyError('DMM 版')
            assert DmmHost is not None
            return DmmHost.instance

        elif b_type == 'playcover':
            from kotonebot.util import is_macos
            if not is_macos():
                raise UserFriendlyError('PlayCover 版仅支持 macOS 系统。')
            from kotonebot.client.playcover import Playcover
            app = Playcover.find(PLAYCOVER_BUNDLE_ID)
            if app is None:
                raise ValueError(f'PlayCover app not found: {PLAYCOVER_BUNDLE_ID}')
            return app

        else:
            raise ValueError(f'Unsupported backend type: {b_type}')

    def _ensure_instance_running(self, instance: Any, config: KaaConfig):
        """
        确保 Instance 正在运行。

        :param instance: 后端实例
        :param config: 用户配置对象
        """
        if DmmInstance and isinstance(instance, DmmInstance):
            logger.info('DMM backend does not require startup.')
            return

        from kaa.config.base_config import PlayCoverDevice  # noqa: PLC0415
        lc = config.backend.lifecycle
        if isinstance(lc, PlayCoverDevice):
            return

        if lc.check_and_start and not instance.running():
            logger.info(f'Starting backend "{instance}"...')
            if hasattr(instance, 'launch'):
                instance.launch()
            else:
                instance.start()
            logger.info(f'Waiting for backend "{instance}" to be available...')
            instance.wait_available()
        else:
            logger.info(f'Backend "{instance}" already running or check is disabled.')

    def _create_device_impl(self, instance: Any, config: KaaConfig) -> Device:
        """
        创建设备。
        """
        from kaa.config.base_config import MuMu12Device, MuMu12V5Device, DmmDevice  # noqa: PLC0415
        impl_name = config.backend.screenshot_impl
        lc = config.backend.lifecycle

        if hasattr(instance, "create_device") and impl_name == 'macos':
            return instance.create_device()

        if DmmInstance and isinstance(instance, DmmInstance):
            assert isinstance(lc, DmmDevice)
            d = WindowsDevice()
            if impl_name == 'windows':
                from kotonebot.client.implements.windows import WindowsImpl
                from kotonebot.interop.window import WindowQuery
                ahk_path = get_ahk_path()
                impl = WindowsImpl(device=d, window_query=WindowQuery(title_contains='gakumas'), ahk_exe_path=ahk_path)
                d.setup(screenshot=impl, touch=impl)
            elif impl_name == 'windows_native':
                from kotonebot.client.implements.windows import WindowsNativeImpl
                from kotonebot.interop.window import WindowQuery
                impl = WindowsNativeImpl(device=d, window_query=WindowQuery(title_contains='gakumas'))
                d.setup(screenshot=impl, touch=impl)
            elif impl_name == 'windows_background':
                from kotonebot.client.implements.windows.send_message import SendMessageImpl
                from kotonebot.client.implements.windows.print_window import PrintWindowImpl
                from kotonebot.interop.window import WindowQuery
                query = WindowQuery(title_contains='gakumas')
                d.setup(
                    screenshot=PrintWindowImpl(d, query),
                    touch=SendMessageImpl(d, query, wait_cursor_idle=lc.cursor_wait_speed),
                )
            else:
                raise ValueError(f"Impl of '{impl_name}' is not supported on DMM.")
            return d

        elif isinstance(instance, (CustomInstance, Mumu12Instance, LeidianInstance)):
            if impl_name == 'nemu_ipc' and isinstance(instance, Mumu12Instance):
                assert isinstance(lc, (MuMu12Device, MuMu12V5Device))
                timeout = 180
                args = {}
                if lc.mumu_background_mode:
                    args = {
                        "display_id": None,
                        "target_package_name": config.tasks.start_game.game_package_name,
                        "app_index": 0
                    }
                host_conf = MuMu12HostConfig(timeout=timeout, **args)
                return instance.create_device(cast(Any, impl_name), host_conf)

            elif impl_name in ['adb', 'uiautomator2']:
                host_conf = AdbHostConfig(timeout=180)
                return instance.create_device(cast(Any, impl_name), host_conf)
            else:
                raise ValueError(f"{lc.type} backend does not support implementation '{impl_name}'")
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
                from kaa.kaa_context import conf as get_conf  # noqa: PLC0415
                scope.set_extra('config', get_conf().model_dump_json(indent=2))
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

    :param config_path: 配置文件目录路径
    :param profile_name: 指定 profile 名称。传入时跳过配置发现，直接使用该 profile。
    """
    def __init__(self, config_path: str = './conf', profile_name: str | None = None):
        self._profile_name = profile_name

        if profile_name is None:
            upgrade_config()
            self._init_config()
        else:
            from kaa.config import manager  # noqa: PLC0415
            self._config = manager.read(profile_name, not_exist='create')

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

    def _init_config(self) -> None:
        """从磁盘加载当前 profile 并注入运行时上下文。"""
        from kaa.config import manager  # noqa: PLC0415
        from kaa.kaa_context import init  # noqa: PLC0415

        shared = manager.read_shared()
        name = shared.profiles.last_used
        if not name:
            profiles = manager.list_profiles()
            name = profiles[0] if profiles else 'default'
            manager.create(name, exist='ok')
            shared.profiles.last_used = name
            manager.write_shared(shared)

        self._config = manager.read(name, not_exist='create')
        self._profile_name = name
        init(self._config, name)
        logger.info("Loaded profile '%s'", name)

    def _initialize(self):
        from kotonebot.backend.context import init_context
        from kotonebot.core.bot import BotContext
        
        logger.info("Initializing Device...")
        device = self.device_factory()
        self._ctx = BotContext(bot=self, device=device)
        
        init_context(
            target_device=device,
            force=True
        )

    def set_log_level(self, level: int):
        handlers = logging.getLogger().handlers
        if len(handlers) == 0:
            print('Warning: No default handler found.')
        else:
            # 第一个 handler 是默认的 StreamHandler
            handlers[0].setLevel(level)

    @property
    def is_running(self) -> bool:
        return self._ctx is not None and self._ctx.is_running

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

    def run(self, tasks: Iterable[Task]) -> None:
        """重写：在 run 前注入 kaa_context（线程安全的单点入口，覆盖 run/start 两条路径）。"""
        from kaa.kaa_context import init as kaa_init
        from kaa.config import manager as config_manager
        assert self._profile_name is not None, \
            "Kaa not initialized. Call with a profile_name or ensure _init_config() has been called."
        self._config = config_manager.read(self._profile_name)
        kaa_init(self._config, self._profile_name)
        return super().run(tasks)
    
    def stop(self):
        if self._ctx is not None:
            self._ctx.stop()

