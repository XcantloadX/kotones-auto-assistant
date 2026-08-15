from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np

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

    def _run_with_screenshot(self, error, upload_return, screenshot,
                             upload_screenshot: bool | None = True):
        """以 patched device 与 upload_screenshot 运行中间件，返回 (fake_sentry, scope, mock_upload)。

        :param upload_screenshot: telemetry.upload_screenshot 的配置值（True/False/None）。
        """
        from kaa.config.shared import SharedConfig

        def next_handler():
            raise error

        task = Task(name='测试任务', id='test', description='', func=lambda: None, priority=0)
        fake_sentry = MagicMock()
        device_mock = MagicMock()
        device_mock.screenshot.return_value = screenshot
        shared = SharedConfig()
        shared.telemetry.upload_screenshot = upload_screenshot
        with patch('kaa.util.telemetry.use_sentry', return_value=fake_sentry):
            with patch('kaa.main.kaa.config_manager.read_shared',
                       return_value=shared):
                with patch('kotonebot.device', device_mock):
                    with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                               return_value=upload_return) as mock_upload:
                        with self.assertRaises(type(error)):
                            sentry_middleware(_FakeCtx(), task, next_handler)
        scope = fake_sentry.push_scope.return_value.__enter__.return_value
        return fake_sentry, scope, mock_upload

    def test_user_friendly_error_not_reported(self):
        # 友好业务错误已由外层中间件弹窗处理，不应上报 Sentry
        fake_sentry = self._run(UserFriendlyError('用户可预见的错误', []))
        fake_sentry.capture_exception.assert_not_called()

    def test_generic_exception_is_reported(self):
        # 真正的系统缺陷应上报 Sentry
        fake_sentry = self._run(RuntimeError('系统缺陷'))
        fake_sentry.capture_exception.assert_called_once()

    def test_exception_uploads_screenshot_and_sets_tag(self):
        # 通用异常：实时截图应上传到图片服务，并把返回的 UUID 作为 tag 附加
        screenshot = np.zeros((16, 16, 3), dtype=np.uint8)
        _, scope, mock_upload = self._run_with_screenshot(
            RuntimeError('系统缺陷'), 'abc-123', screenshot)
        mock_upload.assert_called_once()
        self.assertIs(mock_upload.call_args.args[0], screenshot)
        scope.set_tag.assert_any_call('screenshot_id', 'abc-123')

    def test_upload_failure_skips_screenshot_tag(self):
        # 上传失败（返回 None）时不应附加 screenshot_id tag，报告仍应正常上报
        screenshot = np.zeros((16, 16, 3), dtype=np.uint8)
        _, scope, mock_upload = self._run_with_screenshot(
            RuntimeError('系统缺陷'), None, screenshot)
        mock_upload.assert_called_once()
        tag_calls = [c for c in scope.set_tag.call_args_list
                     if c.args and c.args[0] == 'screenshot_id']
        self.assertEqual(tag_calls, [])

    def test_upload_screenshot_none_skips_upload(self):
        # 配置缺省（None）时不应上传截图，报告仍应正常上报
        screenshot = np.zeros((16, 16, 3), dtype=np.uint8)
        _, scope, mock_upload = self._run_with_screenshot(
            RuntimeError('系统缺陷'), 'abc-123', screenshot, upload_screenshot=None)
        mock_upload.assert_not_called()
        tag_calls = [c for c in scope.set_tag.call_args_list
                     if c.args and c.args[0] == 'screenshot_id']
        self.assertEqual(tag_calls, [])
        fake_sentry, _, _ = self._run_with_screenshot(
            RuntimeError('系统缺陷'), 'abc-123', np.zeros((16, 16, 3), dtype=np.uint8),
            upload_screenshot=None)
        fake_sentry.capture_exception.assert_called_once()

    def test_upload_screenshot_false_skips_upload(self):
        # 配置为 False 时不应上传截图，报告仍应正常上报
        screenshot = np.zeros((16, 16, 3), dtype=np.uint8)
        _, scope, mock_upload = self._run_with_screenshot(
            RuntimeError('系统缺陷'), 'abc-123', screenshot, upload_screenshot=False)
        mock_upload.assert_not_called()
        tag_calls = [c for c in scope.set_tag.call_args_list
                     if c.args and c.args[0] == 'screenshot_id']
        self.assertEqual(tag_calls, [])

    def test_reports_profile_and_shared_config(self):
        # 异常上报应同时携带当前 profile config 与 shared config 内容
        from kaa.config.schema import KaaConfig
        from kaa.config.shared import SharedConfig

        def next_handler():
            raise RuntimeError('系统缺陷')

        task = Task(name='测试任务', id='test', description='', func=lambda: None, priority=0)
        fake_sentry = MagicMock()
        device_mock = MagicMock()
        device_mock.screenshot.return_value = np.zeros((16, 16, 3), dtype=np.uint8)
        shared = SharedConfig()
        with patch('kaa.util.telemetry.use_sentry', return_value=fake_sentry):
            with patch('kaa.main.kaa.config_manager.read_shared', return_value=shared):
                with patch('kaa.kaa_context.conf', return_value=KaaConfig()):
                    with patch('kotonebot.device', device_mock):
                        with self.assertRaises(RuntimeError):
                            sentry_middleware(_FakeCtx(), task, next_handler)
        scope = fake_sentry.push_scope.return_value.__enter__.return_value
        extra_calls = {c.args[0]: c.args[1] for c in scope.set_extra.call_args_list}
        self.assertIn('config', extra_calls)
        self.assertIn('shared_config', extra_calls)
        self.assertIsInstance(extra_calls['config'], str)
        self.assertIsInstance(extra_calls['shared_config'], str)