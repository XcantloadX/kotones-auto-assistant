# ruff: noqa: E402
import sys
import logging
import importlib.metadata
from typing import Any, cast
from collections.abc import Callable, Iterable

from kotonebot.core.bot import BotContext, KotoneBot
from kotonebot.backend.context import Task
from kotonebot.client.device import Device, WindowsDevice
from kotonebot.client.host import (
    LeidianHost, Mumu12Instance,
    LeidianInstance, CustomInstance
)
from kotonebot.client.host.mumu12_host import Mumu12V5Host, MuMu12HostConfig
from kotonebot.client.host.protocol import Instance, AdbHostConfig
from kaa.config.schema import KaaConfig
from kaa.config import upgrade_config
from kaa.config import manager as config_manager
from kotonebot.primitives.geometry import Size
from kotonebot.util import is_windows
from kaa.errors import ElevationRequiredError, WindowsOnlyError
from kaa.constants import GAME_PACKAGE_NAME, PLAYCOVER_BUNDLE_ID

from ..kaa_context import _set_instance
from kaa.tasks import POST_TASK_REGISTRY, TASK_FUNCTIONS
from kotonebot.errors import UserFriendlyError, StopCurrentTask, UnscalableResolutionError
from kotonebot.interop.window.model import WindowQueryError
from kotonebot.core import NextHandler
from kaa.util.error_handler import handle_exception

if is_windows():
    from .dmm_host import DmmHost, DmmInstance
else:
    DmmHost = DmmInstance = None
from kotonebot.primitives.geometry import Size


logger = logging.getLogger(__name__)


def _is_admin() -> bool:
    import ctypes
    import os

    try:
        return os.getuid() == 0  # type: ignore[attr-defined]
    except AttributeError:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

def build_resolution_error_message(screen_size: tuple[int, int]) -> str:
    """构造分辨率不兼容时的用户提示文案。

    :param screen_size: 设备实际分辨率 (width, height)。
    :return: 包含实际分辨率与修复指引的文案。
    """
    w, h = screen_size
    return (
        f'游戏窗口尺寸/模拟器分辨率（{w}x{h}）为不支持的分辨率。\n'
        f'请调整尺寸/分辨率为 16:9 或 9:16 的比例（720x1280 最佳）。'
    )


def windows_gui_error_middleware(ctx: BotContext, task: Task, next_handler: NextHandler):
    """任务期统一异常处理薄包装，委托至 kaa.errors.handler.handle_exception。"""
    try:
        next_handler()
    except BaseException as e:
        handle_exception(e, ctx=ctx, task=task, source="task")


class KaaDeviceFactory:
    def __init__(self):
        self.backend_instance: Instance | None = None
        self.target_screenshot_interval: float | None = None

    def __call__(self) -> Device:
        from kaa.kaa_context import conf as get_conf  # noqa: PLC0415
        config = get_conf()
        return self.create_device_for_config(config)

    def create_device_for_config(self, config: KaaConfig) -> Device:
        """为指定配置创建 Device，绕过 ContextVar，供跨线程截图等场景使用。

        与 ``__call__`` 等价，但不依赖 ``kaa_context.conf()`` 的线程局部状态。
        """
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
            MuMu12V5Device, LeidianDevice, DmmDevice, CustomDevice, TcpConnection,
        )
        lc = config.backend.lifecycle
        b_type = lc.type
        logger.info(f'Querying for backend: {b_type}')

        if b_type == 'custom':
            assert isinstance(lc, CustomDevice)
            conn = config.backend.connection
            assert isinstance(conn, TcpConnection)
            if conn._ip_contains_port():
                # IP 字段误填了端口（如 '127.0.0.1:16384'）会导致 ADB 地址拼接
                # 成非法的双端口形式（127.0.0.1:16384:5555），抛出友好错误以便
                # 用户在设置页修正，而不是以晦涩的 AdbError 崩溃。
                host, _, port = conn.ip.partition(':')
                raise UserFriendlyError(
                    f'ADB 连接配置错误：IP 地址中不能包含端口（当前填了 "{conn.ip}"）。'
                    f'请在设置页将「ADB IP 地址」填为 "{host}"，「ADB 端口」填为 "{port}"。'
                )
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
                    raise ValueError('Emulator executable path is not set.')
                if not os.path.exists(exe):
                    raise FileNotFoundError(f'Emulator executable not found: {exe}')
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
            if not _is_admin():
                raise ElevationRequiredError()
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
        from kaa.config.base_config import MuMu12V5Device, DmmDevice  # noqa: PLC0415
        impl_name = config.backend.screenshot_impl
        lc = config.backend.lifecycle

        if hasattr(instance, "create_device") and impl_name == 'macos':
            return instance.create_device()

        if DmmInstance and isinstance(instance, DmmInstance):
            assert isinstance(lc, DmmDevice)
            d = WindowsDevice()
            if impl_name == 'windows_native':
                from kotonebot.client.implements.windows import WindowsNativeImpl
                from kotonebot.interop.window import WindowQuery
                impl = WindowsNativeImpl(device=d, window_query=WindowQuery(title='gakumas'))
                d.setup(screenshot=impl, touch=impl)
            elif impl_name == 'windows_background':
                from kotonebot.client.implements.windows.send_message import SendMessageImpl
                from kotonebot.client.implements.windows.print_window import PrintWindowImpl
                from kotonebot.interop.window import WindowQuery
                query = WindowQuery(title='gakumas')
                d.setup(
                    screenshot=PrintWindowImpl(d, query),
                    touch=SendMessageImpl(d, query, wait_cursor_idle=lc.cursor_wait_speed),
                )
            else:
                raise ValueError(f"Impl of '{impl_name}' is not supported on DMM.")
            return d

        elif isinstance(instance, (CustomInstance, Mumu12Instance, LeidianInstance)):
            if impl_name == 'nemu_ipc' and isinstance(instance, Mumu12Instance):
                assert isinstance(lc, MuMu12V5Device)
                timeout = 180
                args = {}
                if lc.mumu_background_mode:
                    args = {
                        "display_id": None,
                        "target_package_name": GAME_PACKAGE_NAME,
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
    """保留 Sentry tag 刷新，异常统一由外层 windows_gui_error_middleware 经 handler 处理。"""
    from kaa.util.telemetry import use_sentry
    sentry_sdk = use_sentry()
    try:
        from kaa.util.telemetry import collect_report_context  # noqa: PLC0415
        for key, value in collect_report_context().items():
            sentry_sdk.set_tag(key, value)
    except Exception:
        logger.warning('Failed to refresh report context.', exc_info=True)
    # 异常捕获与上报已统一至 handle_exception（避免双重上报），此处仅透传
    return next_handler()

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
                # 顺序说明：kotonebot 用 reversed() 递归包装，列表第一项为最外层。
                # windows 在最外层作为异常最终吞没点（保证单任务失败不中断整轮 run），
                # sentry 在内层紧贴 core，先捕获异常上报后再向上抛给 windows。
                windows_gui_error_middleware,
                sentry_middleware
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
        from kotonebot.core.bot import BotContext, BotStopReason

        try:
            logger.info("Initializing Device...")
            device = self.device_factory()
            self._ctx = BotContext(bot=self, device=device)

            init_context(
                target_device=device,
                force=True
            )

            if self.factory.backend_instance is None:
                raise RuntimeError('Backend instance was not initialized.')
            _set_instance(self.factory.backend_instance)

            # 注册全局 Loop 回调：每次 Loop 迭代前自动处理网络错误等全局弹窗。
            from kotonebot.config.config import conf
            from kaa.tasks.globals import global_interrupt
            conf().loop.loop_callbacks = [global_interrupt]

            # 启动时预检：截图验证窗口分辨率可缩放，不兼容则友好提示并阻止任务启动。
            self._preflight_resolution(device)
        except BaseException as e:
            # Runner 线程初始化期错误统一经 handler 处理（日志+弹窗+Sentry），避免裸 threading堆栈
            # 去重由 handler 内部 _handled_ids 保证与外层 run 守卫不重复
            # 事件触发由外层 Kaa.run 统一负责，此处仅处理弹窗/日志/Sentry 后透传
            handle_exception(e, ctx=getattr(self, "_ctx", None), task=None, source="runner")
            raise

    def _preflight_resolution(self, device: Device) -> None:
        """启动时用截图验证分辨率可缩放。

        通过实际截图的缩放路径提前暴露 UnscalableResolutionError，以友好
        弹窗提示用户调整窗口/模拟器分辨率，而不是等任务运行到一半才失败。

        若设备或游戏窗口未就绪（无法截图），则跳过预检，交由运行时的
        windows_gui_error_middleware 兜底。
        """
        try:
            device.start()
        except Exception:
            logger.debug('Resolution preflight skipped: device not ready.', exc_info=True)
            return

        screen_size: tuple[int, int] | None = None
        try:
            device.screenshot()
        except UnscalableResolutionError as e:
            screen_size = cast('tuple[int, int] | None', e.screen_size)
        except Exception:
            # 窗口未就绪等其它异常不视为分辨率问题，静默跳过预检。
            logger.debug('Resolution preflight skipped.', exc_info=True)
            return
        finally:
            try:
                device.stop()
            except Exception:
                logger.debug('Failed to stop device in resolution preflight.', exc_info=True)

        if screen_size is None:
            return

        message = build_resolution_error_message(screen_size)
        logger.warning("Incompatible device resolution %dx%d has been detected.",
                       *screen_size)
        from kaa.application.ui.error_bridge import get_bridge
        bridge = get_bridge()
        if bridge is not None:
            bridge.show(message, [(0, '知道了')], lambda _: None)
        else:
            logger.error(message)
        # 阻止 run 循环执行任何任务。
        if self._ctx is not None:
            self._ctx.stop()
        else:
            logger.warning("BotContext is None, cannot stop run loop after resolution preflight failure.")

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
        from kotonebot.core.bot import BotStopReason
        assert self._profile_name is not None, \
            "Kaa not initialized. Call with a profile_name or ensure _init_config() has been called."
        self._config = config_manager.read(self._profile_name)
        kaa_init(self._config, self._profile_name)
        try:
            return super().run(tasks)
        except BaseException as e:
            # Runner 线程兜底：初始化期（含 device_factory）及任务循环外错误统一处理
            # 若 _initialize 已触发过 stopped（去重），此处 handle_exception 会因 _handled_ids 吞掉重复弹窗
            handle_exception(e, ctx=getattr(self, "_ctx", None), task=None, source="runner")
            # 确保 TaskService 能收到 stopped 以重置 UI 的“运行中”状态
            # （当 _initialize 失败时 KotoneBot.run 不会自动触发 stopped）
            try:
                self.events.stopped.trigger(BotStopReason.ERROR, e)
            except Exception:
                logger.debug("Failed to trigger stopped event after run error.", exc_info=True)
            return None

    def stop(self):
        if self._ctx is not None:
            self._ctx.stop()
