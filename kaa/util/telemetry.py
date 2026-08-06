import locale
import logging
import os
import platform
import sys
import time
from asyncio import CancelledError

logger = logging.getLogger(__name__)


def is_dev() -> bool:
    return not os.path.exists('./kaa.exe')


def is_enabled() -> bool:
    from kaa.config import manager  # noqa: PLC0415
    return bool(manager.read_shared().telemetry.sentry)


def _set_enabled(value: bool) -> None:
    from kaa.config import manager  # noqa: PLC0415
    shared = manager.read_shared()
    shared.telemetry.sentry = value
    manager.write_shared(shared)


def setup():
    if is_dev():
        logger.info('Development mode detected, telemetry disabled.')
        return

    import importlib.metadata
    from packaging import version

    import sentry_sdk

    from kaa.config import manager  # noqa: PLC0415
    shared = manager.read_shared()

    if shared.telemetry.sentry is None:
        print('=' * 40)
        print(
            '是否允许自动发送匿名错误报告以帮助改进琴音小助手？\n'
            '（按任意键同意，按 0 拒绝）'
        )
        print('=' * 40)
        import msvcrt
        ch = msvcrt.getch()
        if ch == b'0':
            logger.info('User declined telemetry.')
            _set_enabled(False)
            print('已禁用匿名错误报告。')
            time.sleep(2)
            return
        else:
            logger.info('User accepted telemetry.')
            _set_enabled(True)
            print('已启用匿名错误报告，感谢您的支持！')
            time.sleep(2)

    if not is_enabled():
        return

    sentry_sdk.init(
        "http://4ca21281d59148989b00454488e759c0@bugsink.1ichika.de/1",

        send_default_pii=False,
        max_request_body_size="always",
        server_name="kaa",

        release=str(version.parse(importlib.metadata.version('ksaa'))),

        traces_sample_rate=0,
        send_client_reports=False,
        auto_session_tracking=False,
        ignore_errors=[KeyboardInterrupt, CancelledError],
    )
    _attach_global_tags()
    logger.info('Telemetry initialized.')


def _attach_global_tags() -> None:
    """为所有后续上报附加静态系统信息全局 tag。

    平台名称/内存/系统版本/locale/显示器分辨率在运行期基本不变，init 时设置一次即可。
    非 Windows 上不易获取的字段（显示器分辨率）跳过，不阻塞遥测初始化。

    tag 附加在进程级 global scope 上，确保任意线程（含后台/AHK 热键线程）产生的
    LoggingIntegration 日志事件也能携带这些字段。
    """
    from sentry_sdk import Scope  # noqa: PLC0415
    global_scope = Scope.get_global_scope()

    # 平台名称（如 Windows / Darwin / Linux）
    try:
        global_scope.set_tag('platform', platform.system())
    except Exception:
        logger.debug('Failed to collect platform.', exc_info=True)

    # 系统内存大小（psutil 跨平台可用）
    try:
        import psutil  # noqa: PLC0415
        total_gb = psutil.virtual_memory().total / (1024 ** 3)
        global_scope.set_tag('system_memory_gb', f'{total_gb:.1f}')
    except Exception:
        logger.debug('Failed to collect system memory.', exc_info=True)

    # 系统版本号
    try:
        global_scope.set_tag('system_version', platform.version())
    except Exception:
        logger.debug('Failed to collect system version.', exc_info=True)

    # 系统 locale
    try:
        loc = locale.getlocale()[0]
        if loc:
            global_scope.set_tag('system_locale', loc)
    except Exception:
        logger.debug('Failed to collect system locale.', exc_info=True)

    # 显示器分辨率（Windows 专用；其他平台跳过）
    # 用 EnumDisplaySettingsW 读取主显示器的真实像素分辨率。若用
    # GetSystemMetrics/GetDeviceCaps，DPI-unaware 进程会拿到 DPI 虚拟化后的
    # 逻辑分辨率（如 2560x1440@125% 会被缩成 2048x1152），故改用设备模式查询。
    if sys.platform == 'win32':
        try:
            import ctypes  # noqa: PLC0415
            from ctypes import wintypes  # noqa: PLC0415

            class _DevModeW(ctypes.Structure):
                _fields_ = [
                    ('dmDeviceName', wintypes.WCHAR * 32),
                    ('dmSpecVersion', wintypes.WORD),
                    ('dmDriverVersion', wintypes.WORD),
                    ('dmSize', wintypes.WORD),
                    ('dmDriverExtra', wintypes.WORD),
                    ('dmFields', wintypes.DWORD),
                    ('dmPosition', wintypes.POINT),
                    ('dmDisplayOrientation', wintypes.DWORD),
                    ('dmDisplayFixedOutput', wintypes.DWORD),
                    ('dmColor', wintypes.SHORT),
                    ('dmDuplex', wintypes.SHORT),
                    ('dmYResolution', wintypes.SHORT),
                    ('dmTTOption', wintypes.SHORT),
                    ('dmCollate', wintypes.SHORT),
                    ('dmFormName', wintypes.WCHAR * 32),
                    ('dmLogPixels', wintypes.WORD),
                    ('dmBitsPerPel', wintypes.DWORD),
                    ('dmPelsWidth', wintypes.DWORD),
                    ('dmPelsHeight', wintypes.DWORD),
                    ('dmDisplayFlags', wintypes.DWORD),
                    ('dmDisplayFrequency', wintypes.DWORD),
                    ('dmICMMethod', wintypes.DWORD),
                    ('dmICMIntent', wintypes.DWORD),
                    ('dmMediaType', wintypes.DWORD),
                    ('dmDitherType', wintypes.DWORD),
                    ('dmReserved1', wintypes.DWORD),
                    ('dmReserved2', wintypes.DWORD),
                    ('dmPanningWidth', wintypes.DWORD),
                    ('dmPanningHeight', wintypes.DWORD),
                ]

            dm = _DevModeW()
            dm.dmSize = ctypes.sizeof(_DevModeW)
            if ctypes.windll.user32.EnumDisplaySettingsW(None, -1, ctypes.byref(dm)):
                global_scope.set_tag(
                    'display_resolution', f'{dm.dmPelsWidth}x{dm.dmPelsHeight}'
                )
        except Exception:
            logger.debug('Failed to collect display resolution.', exc_info=True)


def collect_report_context() -> dict[str, str]:
    """收集错误上报时动态附加的上下文字段（每次上报实时采集）。

    静态系统信息（平台/系统内存/系统版本/locale/显示器分辨率）在 setup() 中已通过
    全局 tag 附加，这里只收集运行期可能变化的数据：进程自身内存占用、游戏数据版本、
    当前 profile 的设备平台与截图方式、模拟器分辨率，以及 MuMu 模拟器版本号（仅 v5，
    v4 无版本查询 API）。所有字段采集失败均静默跳过。
    """
    ctx: dict[str, str] = {}

    # 进程自身内存占用（RSS/工作集，单位 MB；psutil 跨平台可用）
    try:
        import psutil  # noqa: PLC0415
        rss = psutil.Process().memory_info().rss
        ctx['process_memory_mb'] = f'{rss / (1024 ** 2):.0f}'
    except Exception:
        logger.debug('Failed to collect process memory.', exc_info=True)

    # game db 版本（resources/game_data/version.txt）
    try:
        from kaa.game_data.paths import version_path  # noqa: PLC0415
        p = version_path()
        if p.exists():
            ctx['game_db_version'] = p.read_text(encoding='utf-8').strip()
    except Exception:
        logger.debug('Failed to collect game db version.', exc_info=True)

    # 当前运行 profile 的平台与截图方式
    try:
        from kaa.kaa_context import conf as get_conf  # noqa: PLC0415
        backend = get_conf().backend
        ctx['device_platform'] = backend.lifecycle.type
        ctx['screenshot_impl'] = backend.screenshot_impl
    except Exception:
        logger.debug('Failed to collect device config.', exc_info=True)

    # 模拟器分辨率（由设备物理分辨率提供）
    try:
        from kotonebot import device  # noqa: PLC0415
        w, h = device.screen_size
        ctx['emulator_resolution'] = f'{w}x{h}'
    except Exception:
        logger.debug('Failed to collect emulator resolution.', exc_info=True)

    # MuMu 模拟器版本号（仅 v5；v4 无版本查询 API，非 Windows 亦跳过）
    if ctx.get('device_platform') == 'mumu12v5':
        try:
            from kotonebot.client.host.mumu12_host import Mumu12V5Host  # noqa: PLC0415
            ctx['mumu_version'] = Mumu12V5Host.get_mumu_version()
        except Exception:
            logger.debug('Failed to collect MuMu version.', exc_info=True)

    return ctx


class _DummySentry:
    def __call__(self, *args, **kwds):
        return self

    def __getattr__(self, item):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def use_sentry():
    if not is_enabled() or is_dev():
        return _DummySentry()
    import sentry_sdk
    return sentry_sdk
