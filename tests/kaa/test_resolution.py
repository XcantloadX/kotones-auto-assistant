from unittest import TestCase
from unittest.mock import MagicMock, patch

from kotonebot.backend.context import Task
from kotonebot.errors import UnscalableResolutionError, UserFriendlyError

from kaa.main.kaa import (
    build_resolution_error_message,
    sentry_middleware,
    windows_gui_error_middleware,
)


class _FakeCtx:
    """最小可用的 BotContext 替身，仅记录中间件修改的状态。"""

    def __init__(self):
        self.has_error = False
        self.last_exception = None
        self.stopped = False

    def stop(self):
        self.stopped = True


class _FakeBridge:
    """记录 show() 调用内容的错误对话框替身。"""

    def __init__(self):
        self.shown: list[tuple[str, list, object]] = []

    def show(self, message, buttons, on_click):
        self.shown.append((message, buttons, on_click))


class TestBuildResolutionErrorMessage(TestCase):
    def test_message_contains_resolution(self):
        # 文案应包含实际分辨率，便于用户定位问题
        msg = build_resolution_error_message((1020, 1553))
        self.assertIn('1020x1553', msg)

    def test_message_contains_expected_resolution(self):
        # 文案应给出期望的逻辑分辨率与修复指引
        msg = build_resolution_error_message((1020, 1553))
        self.assertIn('720x1280', msg)


class TestWindowsGuiErrorMiddleware(TestCase):
    def _handle(self, ctx, bridge, error):
        def next_handler():
            raise error

        task = Task(name='测试任务', id='test', description='', func=lambda: None, priority=0)

        with patch('kaa.application.ui.error_bridge.get_bridge', return_value=bridge):
            windows_gui_error_middleware(ctx, task, next_handler)

    def test_unscalable_resolution_is_friendly_and_stops(self):
        ctx = _FakeCtx()
        bridge = _FakeBridge()

        self._handle(ctx, bridge, UnscalableResolutionError((720, 1280), (1900, 1276)))

        # 友好处理：记录状态、弹窗、停止任务
        self.assertTrue(ctx.has_error)
        self.assertIsInstance(ctx.last_exception, UnscalableResolutionError)
        self.assertTrue(ctx.stopped)
        self.assertEqual(len(bridge.shown), 1)
        message, buttons, _ = bridge.shown[0]
        self.assertIn('1900x1276', message)
        self.assertEqual(buttons, [(0, '知道了')])

    def test_without_bridge_logs_instead(self):
        # GUI 桥不存在（如 CLI 场景）时不应抛异常，仅记录日志并停止
        ctx = _FakeCtx()

        self._handle(ctx, None, UnscalableResolutionError((720, 1280), (1020, 1553)))

        self.assertTrue(ctx.has_error)
        self.assertTrue(ctx.stopped)


class TestSentryMiddleware(TestCase):
    """验证 sentry_middleware 对各类异常的上报行为。"""

    def _run(self, error):
        def next_handler():
            raise error

        task = Task(name='测试任务', id='test', description='', func=lambda: None, priority=0)
        fake_sentry = MagicMock()
        with patch('kaa.util.telemetry.use_sentry', return_value=fake_sentry):
            with self.assertRaises(type(error)):
                sentry_middleware(_FakeCtx(), task, next_handler)
        return fake_sentry

    def test_user_friendly_error_not_reported(self):
        # 友好业务错误已由外层中间件弹窗处理，不应上报 Sentry
        fake_sentry = self._run(UserFriendlyError('用户可预见的错误', []))
        fake_sentry.capture_exception.assert_not_called()

    def test_generic_exception_is_reported(self):
        # 真正的系统缺陷应上报 Sentry
        fake_sentry = self._run(RuntimeError('系统缺陷'))
        fake_sentry.capture_exception.assert_called_once()