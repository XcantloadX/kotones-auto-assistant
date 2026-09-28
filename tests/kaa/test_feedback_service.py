"""FeedbackService 报告导出：崩溃录屏的附带行为。"""
import os
import tempfile
import unittest
import zipfile
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from kaa.application.services.feedback_service import FeedbackService

if TYPE_CHECKING:
    from kaa.main.kaa import Kaa


class _StubRecorder:
    """最小录屏器替身：可配 last_video_path、dump 与等待结果。"""

    def __init__(
        self,
        last_video_path: str | None,
        dump_result: str | None = None,
        wait_result: bool = True,
        on_wait: Callable[[str], None] | None = None,
    ) -> None:
        self.last_video_path = last_video_path
        self._dump_result = dump_result
        self._wait_result = wait_result
        self._on_wait = on_wait
        self.dump_calls = 0
        self.wait_calls = 0

    def dump_for_crash(self) -> str | None:
        self.dump_calls += 1
        return self._dump_result

    def wait_for_video(self, path: str, timeout: float | None = None) -> bool:
        self.wait_calls += 1
        if self._on_wait is not None:
            self._on_wait(path)
        return self._wait_result


class _StubKaa:
    """最小 Kaa 替身：仅持有 _recorder（无活跃设备/配置，截图分支注定失败）。"""

    def __init__(self, recorder: _StubRecorder | None) -> None:
        self._recorder = recorder
        self._ctx = None
        self._config = None


class TestCrashVideoAttachment(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _report(self, recorder: _StubRecorder | None) -> tuple[zipfile.ZipFile, str]:
        stub = _StubKaa(recorder)
        service = FeedbackService(kaa_getter=lambda: cast('Kaa', stub))
        out = os.path.join(self._tmp.name, 'report.zip')
        result = service.report('t', 'd', 'v1', out)
        # 成功提示保持纯路径文案，不因视频附加与否而变化。
        self.assertEqual(result.message, f'报告已保存至 {out}')
        return zipfile.ZipFile(out), result.message

    def test_finished_video_attached(self) -> None:
        video = os.path.join(self._tmp.name, 'crash_x.mp4')
        with open(video, 'wb') as f:
            f.write(b'fake-video-bytes')
        recorder = _StubRecorder(last_video_path=video)
        zf, _ = self._report(recorder)
        with zf:
            self.assertIn('crash_video.mp4', zf.namelist())
            self.assertEqual(zf.read('crash_video.mp4'), b'fake-video-bytes')
            self.assertNotIn('crash_video_status.txt', zf.namelist())
        # 文件已就绪，不应等待。
        self.assertEqual(recorder.wait_calls, 0)

    def test_no_recorder_no_video(self) -> None:
        zf, _ = self._report(None)
        with zf:
            self.assertNotIn('crash_video.mp4', zf.namelist())
            self.assertNotIn('crash_video_status.txt', zf.namelist())

    def test_encoding_in_progress_waits_then_attaches(self) -> None:
        pending = os.path.join(self._tmp.name, 'not-yet.mp4')

        def _finish(_path: str) -> None:
            with open(pending, 'wb') as f:
                f.write(b'late-video-bytes')

        recorder = _StubRecorder(last_video_path=pending, on_wait=_finish)
        zf, _ = self._report(recorder)
        with zf:
            self.assertIn('crash_video.mp4', zf.namelist())
            self.assertEqual(zf.read('crash_video.mp4'), b'late-video-bytes')
            self.assertNotIn('crash_video_status.txt', zf.namelist())
        self.assertEqual(recorder.wait_calls, 1)

    def test_encoding_timeout_writes_status(self) -> None:
        pending = os.path.join(self._tmp.name, 'not-yet.mp4')
        recorder = _StubRecorder(last_video_path=pending, wait_result=False)
        zf, _ = self._report(recorder)
        with zf:
            self.assertNotIn('crash_video.mp4', zf.namelist())
            self.assertIn('crash_video_status.txt', zf.namelist())
            self.assertIn(pending, zf.read('crash_video_status.txt').decode('utf-8'))
        self.assertEqual(recorder.wait_calls, 1)

    def test_never_dumped_triggers_background_dump(self) -> None:
        pending = os.path.join(self._tmp.name, 'fresh.mp4')
        recorder = _StubRecorder(last_video_path=None, dump_result=pending, wait_result=False)
        zf, _ = self._report(recorder)
        with zf:
            self.assertIn('crash_video_status.txt', zf.namelist())
        self.assertEqual(recorder.dump_calls, 1)
        self.assertEqual(recorder.wait_calls, 1)

    def test_progress_steps_reported(self) -> None:
        steps: list[str] = []
        stub = _StubKaa(None)
        service = FeedbackService(kaa_getter=lambda: cast('Kaa', stub))
        out = os.path.join(self._tmp.name, 'report.zip')
        service.report('t', 'd', 'v1', out, on_progress=steps.append)
        self.assertEqual(
            steps,
            ['正在收集截图…', '正在打包配置与日志…', '正在附加崩溃录屏…'],
        )


if __name__ == '__main__':
    unittest.main()
