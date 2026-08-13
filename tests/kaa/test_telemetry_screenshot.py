from unittest import TestCase
from unittest.mock import MagicMock, patch

from kaa.util.telemetry_screenshot import (
    _allow_upload,
    _upload_attempt_times,
    screenshot_before_send,
)


def _log_event(message: str = 'boom', level: str = 'error', exception: bool = False) -> dict:
    """构造一个 LoggingIntegration 风格的日志事件。"""
    event: dict = {
        'level': level,
        'logger': 'test.logger',
        'logentry': {'message': message, 'formatted': message, 'params': []},
    }
    if exception:
        event['exception'] = {'values': [{'type': 'RuntimeError'}]}
    return event


class TestScreenshotBeforeSend(TestCase):
    """验证 before_send 钩子对各类日志事件的截图上传行为。"""

    def _run(self, event):
        device_mock = MagicMock()
        device_mock.screenshot.return_value = object()
        with patch('kotonebot.device', device_mock):
            with patch('kaa.util.telemetry_screenshot.upload_screenshot') as mock_upload:
                result = screenshot_before_send(event, {})
        return result, mock_upload

    def test_exception_event_untouched(self):
        # 异常事件由 sentry_middleware 处理，钩子不应上传
        event = _log_event(exception=True)
        result, mock_upload = self._run(event)
        self.assertIs(result, event)
        mock_upload.assert_not_called()

    def test_non_error_level_untouched(self):
        # 非 error 级日志不上传
        event = _log_event(level='info')
        result, mock_upload = self._run(event)
        self.assertIs(result, event)
        mock_upload.assert_not_called()

    def test_known_benign_message_skips_upload(self):
        # 已知良性消息（+30 选项）跳过上传，事件原样返回
        event = _log_event('Failed to find +30 option. Pick the second button instead.')
        result, mock_upload = self._run(event)
        self.assertIs(result, event)
        mock_upload.assert_not_called()

    def test_error_log_event_uploads_and_sets_tag(self):
        # error 级日志事件上传截图并把 UUID 写入 tags.screenshot_id
        event = _log_event('Unexpected failure')
        with patch('kotonebot.device', MagicMock()):
            with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                       return_value='abc-123') as mock_upload:
                result = screenshot_before_send(event, {})
        mock_upload.assert_called_once()
        self.assertEqual(result['tags']['screenshot_id'], 'abc-123')

    def test_upload_failure_leaves_event_untouched(self):
        # 上传失败（返回 None）时不写 tag，事件本身不受影响
        event = _log_event('Unexpected failure')
        with patch('kotonebot.device', MagicMock()):
            with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                       return_value=None):
                result = screenshot_before_send(event, {})
        self.assertIs(result, event)
        self.assertNotIn('screenshot_id', result.get('tags', {}))


class TestUploadRateLimit(TestCase):
    """验证单进程内每分钟上传次数上限。"""

    def tearDown(self):
        _upload_attempt_times.clear()

    def test_five_uploads_then_blocked(self):
        clock = {'t': 0.0}

        def _now():
            clock['t'] += 1.0
            return clock['t']

        with patch('kaa.util.telemetry_screenshot.time.monotonic', side_effect=_now):
            allowed = [_allow_upload() for _ in range(6)]
        self.assertEqual(allowed, [True, True, True, True, True, False])

    def test_window_slides_after_one_minute(self):
        # 一分钟后旧尝试失效，重新放行
        clock = {'t': 0.0}

        def _now():
            return clock['t']

        with patch('kaa.util.telemetry_screenshot.time.monotonic', side_effect=_now):
            for _ in range(5):
                self.assertTrue(_allow_upload())
            self.assertFalse(_allow_upload())  # 第 6 次被限
            clock['t'] += 61.0  # 时间推进 61 秒
            self.assertTrue(_allow_upload())  # 窗口滑动，重新放行
