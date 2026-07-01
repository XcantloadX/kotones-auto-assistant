import logging
import os
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
    logger.info('Telemetry initialized.')

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
