from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np

from typing import TYPE_CHECKING, cast

from kaa.util.telemetry_screenshot import (
    _allow_upload,
    _upload_attempt_times,
    screenshot_before_send,
    upload_report_screenshot,
    upload_screenshot,
    upload_video_file,
)

if TYPE_CHECKING:
    from sentry_sdk.types import Event


def _log_event(message: str = 'boom', level: str = 'error', exception: bool = False,
               mechanism: str | None = None) -> 'Event':
    """构造一个 LoggingIntegration 风格的日志事件。

    :param mechanism: exception.values[0].mechanism.type，模拟 exc_info
        生成（'logging'）与 capture_exception 上报（'generic'）的事件形态。
    """
    event: dict = {
        'level': level,
        'logger': 'test.logger',
        'logentry': {'message': message, 'formatted': message, 'params': []},
    }
    if exception:
        value: dict = {'type': 'RuntimeError'}
        if mechanism is not None:
            value['mechanism'] = {'type': mechanism, 'handled': True}
        event['exception'] = {'values': [value]}
    return cast('Event', event)


class TestScreenshotBeforeSend(TestCase):
    """验证 before_send 钩子对各类日志事件的截图上传行为。"""

    def _run(self, event):
        device_mock = MagicMock()
        device_mock.screenshot.return_value = object()
        with patch('kotonebot.device', device_mock):
            with patch('kaa.util.telemetry_screenshot.upload_screenshot') as mock_upload:
                result = screenshot_before_send(event, {})
        return result, mock_upload

    @staticmethod
    def _tags(result) -> dict:
        """取事件的 tags 字典（实现从不返回 None，cast 仅用于静态类型）。"""
        return cast(dict, result).get('tags', {})

    def test_exception_event_untouched(self):
        # 异常事件由 sentry_middleware 处理，钩子不应上传
        event = _log_event(exception=True)
        result, mock_upload = self._run(event)
        self.assertIs(result, event)
        mock_upload.assert_not_called()

    def test_generic_mechanism_exception_event_untouched(self):
        # capture_exception 上报的异常事件（mechanism 为 generic）已由上报方
        # 同步处理截图，钩子不应重复上传
        event = _log_event(exception=True, mechanism='generic')
        result, mock_upload = self._run(event)
        self.assertIs(result, event)
        mock_upload.assert_not_called()

    def test_logging_mechanism_exception_event_uploads(self):
        # logger.error(exc_info=True) 生成的异常事件（mechanism 为 logging）
        # 未经同步上传，钩子应补传截图并写入 tags.screenshot_id
        event = _log_event('Action recognition hit transient state', exception=True,
                           mechanism='logging')
        with patch('kotonebot.device', MagicMock()):
            with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                       return_value='abc-123') as mock_upload:
                result = screenshot_before_send(event, {})
        mock_upload.assert_called_once()
        self.assertEqual(self._tags(result)['screenshot_id'], '[now]abc-123')

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
        # error 级日志事件上传现场截图并把带 [now] 前缀的 ID 写入 tags.screenshot_id
        event = _log_event('Unexpected failure')
        with patch('kotonebot.device', MagicMock()):
            with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                       return_value='abc-123') as mock_upload:
                result = screenshot_before_send(event, {})
        mock_upload.assert_called_once()
        self.assertEqual(self._tags(result)['screenshot_id'], '[now]abc-123')

    def test_last_screenshot_reused_and_prefixed_with_last(self):
        # 存在上次截图数据时复用该图，并把带 [last] 前缀的 ID 写入 tags.screenshot_id
        last_img = object()
        stack_mock = MagicMock()
        stack_mock._screenshot = last_img
        event = _log_event('Unexpected failure')
        with patch('kotonebot.backend.context.ContextStackVars.current',
                   return_value=stack_mock):
            with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                       return_value='abc-123') as mock_upload:
                result = screenshot_before_send(event, {})
        mock_upload.assert_called_once()
        self.assertIs(mock_upload.call_args.args[0], last_img)
        self.assertEqual(self._tags(result)['screenshot_id'], '[last]abc-123')

    def test_upload_failure_leaves_event_untouched(self):
        # 上传失败（返回 None）时不写 tag，事件本身不受影响
        event = _log_event('Unexpected failure')
        with patch('kotonebot.device', MagicMock()):
            with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                       return_value=None):
                result = screenshot_before_send(event, {})
        self.assertIs(result, event)
        self.assertNotIn('screenshot_id', self._tags(result))


class TestUploadReportScreenshot(TestCase):
    """验证 upload_report_screenshot 的截图来源选择与 ID 前缀。"""

    def test_reuses_last_screenshot(self):
        # 有上次截图数据：复用该图，前缀为 [last]
        last_img = object()
        stack_mock = MagicMock()
        stack_mock._screenshot = last_img
        with patch('kotonebot.backend.context.ContextStackVars.current',
                   return_value=stack_mock):
            with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                       return_value='abc-123') as mock_upload:
                self.assertEqual(upload_report_screenshot(), '[last]abc-123')
        self.assertIs(mock_upload.call_args.args[0], last_img)

    def test_falls_back_to_fresh_screenshot(self):
        # 无上次截图数据：现场截图，前缀为 [now]
        fresh_img = object()
        device_mock = MagicMock()
        device_mock.screenshot.return_value = fresh_img
        with patch('kotonebot.backend.context.ContextStackVars.current',
                   return_value=None):
            with patch('kotonebot.device', device_mock):
                with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                           return_value='abc-123') as mock_upload:
                    self.assertEqual(upload_report_screenshot(), '[now]abc-123')
        self.assertIs(mock_upload.call_args.args[0], fresh_img)

    def test_upload_failure_returns_none(self):
        # 上传失败（返回 None）时整体返回 None
        with patch('kotonebot.backend.context.ContextStackVars.current',
                   return_value=None):
            with patch('kotonebot.device', MagicMock()):
                with patch('kaa.util.telemetry_screenshot.upload_screenshot',
                           return_value=None):
                    self.assertIsNone(upload_report_screenshot())


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


class _FakeResponse:
    """requests.post 的最小替身：status_code + json。"""

    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def _enabled():
    """进入“ telemetry 启用 + 非开发模式”的补丁上下文。"""
    return (
        patch('kaa.util.telemetry_screenshot.is_dev', return_value=False),
        patch('kaa.util.telemetry_screenshot.is_enabled', return_value=True),
    )


class TestUploadScreenshotPostMedia(TestCase):
    """验证截图上传重构（经 _post_media）行为不变。"""

    def tearDown(self):
        _upload_attempt_times.clear()

    def test_success_returns_id_with_png_content_type(self):
        # PNG 编码 + POST 成功：返回 UUID，且 Content-Type 为 image/png
        import tempfile

        raw = np.zeros((10, 10, 3), dtype=np.uint8)
        posted = {}

        def _post(url, headers=None, data=None, timeout=None, proxies=None):
            posted['headers'] = headers
            posted['data'] = data
            return _FakeResponse(201, {'id': 'shot-1'})

        no_dev, enabled = _enabled()
        with no_dev, enabled, patch('requests.post', side_effect=_post):
            with tempfile.TemporaryFile():
                self.assertEqual(upload_screenshot(raw), 'shot-1')
        self.assertEqual(posted['headers'], {'Content-Type': 'image/png'})
        self.assertTrue(posted['data'].startswith(b'\x89PNG'))


class TestUploadVideoFile(TestCase):
    """验证崩溃录屏 MP4 上传。"""

    def tearDown(self):
        _upload_attempt_times.clear()

    def _write_mp4(self, tmp_path, size=64):
        path = tmp_path / 'crash.mp4'
        path.write_bytes(b'\x00' * size)
        return str(path)

    def test_success_returns_id_with_mp4_content_type(self):
        # 上传成功：返回 UUID，Content-Type 为 video/mp4，body 与文件一致
        import tempfile
        from pathlib import Path

        posted = {}

        def _post(url, headers=None, data=None, timeout=None, proxies=None):
            posted['headers'] = headers
            posted['data'] = data
            return _FakeResponse(201, {'id': 'vid-1'})

        no_dev, enabled = _enabled()
        with tempfile.TemporaryDirectory() as d:
            path = self._write_mp4(Path(d))
            with no_dev, enabled, patch('requests.post', side_effect=_post):
                self.assertEqual(upload_video_file(path), 'vid-1')
        self.assertEqual(posted['headers'], {'Content-Type': 'video/mp4'})
        self.assertEqual(posted['data'], b'\x00' * 64)

    def test_telemetry_disabled_returns_none_without_request(self):
        with patch('kaa.util.telemetry_screenshot.is_dev', return_value=False):
            with patch('kaa.util.telemetry_screenshot.is_enabled', return_value=False):
                with patch('requests.post') as mock_post:
                    self.assertIsNone(upload_video_file('/nonexistent.mp4'))
        mock_post.assert_not_called()

    def test_dev_mode_returns_none_without_request(self):
        with patch('kaa.util.telemetry_screenshot.is_dev', return_value=True):
            with patch('requests.post') as mock_post:
                self.assertIsNone(upload_video_file('/nonexistent.mp4'))
        mock_post.assert_not_called()

    def test_missing_file_returns_none(self):
        no_dev, enabled = _enabled()
        with no_dev, enabled, patch('requests.post') as mock_post:
            self.assertIsNone(upload_video_file('/nonexistent-crash.mp4'))
        mock_post.assert_not_called()

    def test_oversize_file_skipped_before_request(self):
        # 超过 Worker 大小上限（3MiB）：不发请求
        no_dev, enabled = _enabled()
        with no_dev, enabled:
            with patch('os.path.getsize', return_value=4 * 1024 * 1024):
                with patch('requests.post') as mock_post:
                    self.assertIsNone(upload_video_file('/fake.mp4'))
        mock_post.assert_not_called()

    def test_rejected_413_returns_none(self):
        import tempfile
        from pathlib import Path

        no_dev, enabled = _enabled()
        with tempfile.TemporaryDirectory() as d:
            path = self._write_mp4(Path(d))
            with no_dev, enabled:
                with patch('requests.post', return_value=_FakeResponse(413)):
                    self.assertIsNone(upload_video_file(path))

    def test_rate_limited_returns_none(self):
        import tempfile
        from pathlib import Path

        no_dev, enabled = _enabled()
        with tempfile.TemporaryDirectory() as d:
            path = self._write_mp4(Path(d))
            with no_dev, enabled:
                with patch('requests.post') as mock_post:
                    for _ in range(5):
                        self.assertTrue(_allow_upload())
                    self.assertIsNone(upload_video_file(path))
        mock_post.assert_not_called()
