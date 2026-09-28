"""验证系统错误上报时的崩溃视频接线：dump→有界等待→上传→video_id tag。"""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from kaa.util.error_handler import (
    _CRASH_VIDEO_WAIT_TIMEOUT,
    _capture_sentry,
    handle_exception,
)


class _FakeScope:
    def __init__(self):
        self.tags = {}
        self.extras = {}

    def set_tag(self, key, value):
        self.tags[key] = value

    def set_extra(self, key, value):
        self.extras[key] = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakeSentry:
    def __init__(self):
        self.scope = _FakeScope()
        self.captured = None

    def isolation_scope(self):
        return self.scope

    def capture_exception(self, exc):
        self.captured = exc


class _FakeRecorder:
    def __init__(self, dump_result='/tmp/crash_test.mp4', wait_result=True):
        self.dump_calls = 0
        self.wait_calls = []
        self.dump_result = dump_result
        self.wait_result = wait_result

    def dump_for_crash(self):
        self.dump_calls += 1
        return self.dump_result

    def wait_for_video(self, path, timeout=None):
        self.wait_calls.append((path, timeout))
        return self.wait_result


def _shared(upload_screenshot=True):
    return SimpleNamespace(
        telemetry=SimpleNamespace(upload_screenshot=upload_screenshot),
        model_dump_json=lambda: '{}',
    )


class TestCaptureSentryVideo(TestCase):
    """验证 _capture_sentry 的视频分支。"""

    def _run(self, ctx, consent=True):
        sentry = _FakeSentry()
        with patch('kaa.util.telemetry.use_sentry', return_value=sentry):
            with patch('kaa.config.manager.read_shared',
                       return_value=_shared(consent)):
                with patch('kaa.util.telemetry_screenshot.upload_report_screenshot',
                           return_value=None):
                    with patch('kaa.util.telemetry_screenshot.upload_video_file',
                               return_value='vid-1') as mock_upload:
                        exc = RuntimeError('boom')
                        _capture_sentry(exc, task_name='t', ctx=ctx)
        return sentry, mock_upload, exc

    def _ctx_with(self, recorder):
        return SimpleNamespace(bot=SimpleNamespace(_recorder=recorder))

    def test_video_uploaded_and_tagged(self):
        # 编码就绪：上传 MP4 并打 video_id tag，等待超时取配置常量
        rec = _FakeRecorder()
        sentry, mock_upload, exc = self._run(self._ctx_with(rec))
        self.assertEqual(rec.dump_calls, 1)
        self.assertEqual(rec.wait_calls, [('/tmp/crash_test.mp4',
                                           _CRASH_VIDEO_WAIT_TIMEOUT)])
        mock_upload.assert_called_once_with('/tmp/crash_test.mp4')
        self.assertEqual(sentry.scope.tags.get('video_id'), 'vid-1')
        self.assertIs(sentry.captured, exc)

    def test_wait_timeout_skips_upload(self):
        # 转码超时：不上传、无 tag，上报本身不受影响
        rec = _FakeRecorder(wait_result=False)
        sentry, mock_upload, exc = self._run(self._ctx_with(rec))
        mock_upload.assert_not_called()
        self.assertNotIn('video_id', sentry.scope.tags)
        self.assertIs(sentry.captured, exc)

    def test_no_recorder_skips_video(self):
        # 无归属录屏（全局兜底等）：不 dump 不等不传
        sentry, mock_upload, exc = self._run(None)
        mock_upload.assert_not_called()
        self.assertNotIn('video_id', sentry.scope.tags)
        self.assertIs(sentry.captured, exc)

    def test_consent_off_skips_video_but_keeps_dump(self):
        # consent 关闭：本地 dump 照常（诊断行为不变），上传跳过
        rec = _FakeRecorder()
        sentry, mock_upload, exc = self._run(self._ctx_with(rec), consent=False)
        self.assertEqual(rec.dump_calls, 1)
        self.assertEqual(rec.wait_calls, [])
        mock_upload.assert_not_called()
        self.assertNotIn('video_id', sentry.scope.tags)
        self.assertIs(sentry.captured, exc)

    def test_upload_failure_keeps_report(self):
        # 上传返回 None：无 tag，上报本身不受影响
        rec = _FakeRecorder()
        sentry = _FakeSentry()
        with patch('kaa.util.telemetry.use_sentry', return_value=sentry):
            with patch('kaa.config.manager.read_shared',
                       return_value=_shared(True)):
                with patch('kaa.util.telemetry_screenshot.upload_report_screenshot',
                           return_value=None):
                    with patch('kaa.util.telemetry_screenshot.upload_video_file',
                               return_value=None):
                        exc = RuntimeError('boom')
                        _capture_sentry(exc, task_name='t',
                                        ctx=self._ctx_with(rec))
        self.assertNotIn('video_id', sentry.scope.tags)
        self.assertIs(sentry.captured, exc)


class TestHandleExceptionRoutesCtx(TestCase):
    """验证 handle_exception 把 ctx 透传给 _capture_sentry（视频归属来源）。"""

    def test_ctx_forwarded_to_capture(self):
        ctx = SimpleNamespace(has_error=False, last_exception=None,
                              stop=lambda: None)
        exc = RuntimeError('boom')
        with patch('kaa.util.error_handler._capture_sentry') as mock_capture:
            handle_exception(exc, ctx=ctx, task=None, source='runner')
        mock_capture.assert_called_once()
        self.assertIs(mock_capture.call_args.kwargs.get('ctx'), ctx)
        self.assertTrue(ctx.has_error)
        self.assertIs(ctx.last_exception, exc)
