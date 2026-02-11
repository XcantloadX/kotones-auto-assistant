import os
import time
import logging

logger = logging.getLogger(__name__)
PATH = './conf/telemetry'

def _read() -> str:
    with open(PATH, 'r', encoding='utf-8') as f:
        return f.read()

def _write(content: str):
    with open(PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def is_enabled() -> bool:
    if os.path.exists(PATH):
        content = _read()
        return content.strip() != '0'
    return False

def disable():
    if not os.path.exists('./conf'):
        os.makedirs('./conf')
    _write('0')

def enable():
    if not os.path.exists('./conf'):
        os.makedirs('./conf')
    _write('1')

def is_dev() -> bool:
    return not os.path.exists('./kaa.exe')

def setup():
    if is_dev():
        logger.info('Development mode detected, telemetry disabled.')
        return

    import importlib.metadata
    from packaging import version

    import sentry_sdk

    if os.path.exists(PATH):
        if not is_enabled():
            return
    else:
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
            disable()
            print('已禁用匿名错误报告。')
            time.sleep(2)
            return
        else:
            logger.info('User accepted telemetry.')
            enable()
            print('已启用匿名错误报告，感谢您的支持！')
            time.sleep(2)

    sentry_sdk.init(
        "http://4ca21281d59148989b00454488e759c0@bugsink.1ichika.de/1",

        send_default_pii=False,
        max_request_body_size="always",
        server_name="kaa",

        # Setting up the release is highly recommended. The SDK will try to
        # infer it, but explicitly setting it is more reliable:
        release=str(version.parse(importlib.metadata.version('ksaa'))),

        # Don't event types which are not supported by Bugsink:
        traces_sample_rate=0,
        send_client_reports=False,
        auto_session_tracking=False,
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