"""ScreenRecorder 单测：时间环淘汰、独立采样、x265 离线编码、崩溃路由。"""
import os
import struct
import tempfile
import time
import unittest
from typing import Any

import cv2
import numpy as np
from cv2.typing import MatLike
from kotonebot.client.device import Device
from kotonebot.client.scaler import AbstractScaler

from kaa.util.error_handler import _crash_recorder
from kaa.util.screen_recorder import (
    FrameRing,
    ScreenRecorder,
    encode_mp4,
    format_timecode,
)


def _jpeg(color: int, w: int = 160, h: int = 128) -> bytes:
    img = np.full((h, w, 3), color, dtype=np.uint8)
    ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    assert ok
    return bytes(buf)


class _FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class _FakeScaler(AbstractScaler):
    def transform_screenshot(self, screenshot: MatLike) -> MatLike:
        return screenshot


class _FakeDevice(Device):
    """最小 Device 子类：recorder 只用到 screenshot_raw + scaler。"""

    def __init__(self, w: int = 160, h: int = 128) -> None:
        # 显式传 scaler，避免 Device 默认从 kotonebot 全局 conf 取 factory；
        # 配好分辨率，避免 scaler 懒初始化去读未 setup 的 _screenshot。
        scaler = _FakeScaler()
        scaler.physical_resolution = (w, h)
        scaler.logic_resolution = (w, h)
        super().__init__(scaler=scaler)
        self.raw_calls = 0
        self._counter = 0
        self._w = w
        self._h = h

    def screenshot_raw(self) -> MatLike:
        self.raw_calls += 1
        self._counter += 1
        return np.full((self._h, self._w, 3), self._counter % 256, dtype=np.uint8)


class _FakeBot:
    """最小 bot 替身：仅持有 _recorder。"""

    def __init__(self, recorder: ScreenRecorder | None) -> None:
        self._recorder = recorder


class _FakeCtx:
    """最小 ctx 替身：仅持有 bot。"""

    def __init__(self, bot: _FakeBot | None) -> None:
        self.bot = bot


class TestFrameRing(unittest.TestCase):
    def test_append_and_snapshot_order(self):
        ring = FrameRing(retain_seconds=60.0)
        ring.append(_jpeg(10))
        ring.append(_jpeg(20))
        frames = ring.snapshot()
        self.assertEqual(len(frames), 2)
        self.assertEqual(len(ring), 2)

    def test_time_eviction(self):
        clock = _FakeClock()
        ring = FrameRing(retain_seconds=10.0, clock=clock)
        ring.append(_jpeg(1))
        clock.now += 5.0
        ring.append(_jpeg(2))
        clock.now += 6.0  # 第一帧已过期（11s > 10s），第二帧仍在
        self.assertEqual(len(ring.snapshot()), 1)
        clock.now += 10.0
        self.assertEqual(ring.snapshot(), [])

    def test_invalid_args(self):
        with self.assertRaises(ValueError):
            FrameRing(retain_seconds=0)
        ring = FrameRing(retain_seconds=60.0)
        with self.assertRaises(ValueError):
            ring.append(b'')

    def test_snapshot_with_start(self):
        clock = _FakeClock()
        ring = FrameRing(retain_seconds=60.0, clock=clock)
        ring.append(_jpeg(1), wall=100.5)
        clock.now += 30.0
        ring.append(_jpeg(2), wall=101.5)
        frames, start = ring.snapshot_with_start()
        self.assertEqual(len(frames), 2)
        self.assertEqual(start, 100.5)
        # 第一帧过期后 start 跟随最老存活帧
        clock.now += 31.0
        frames, start = ring.snapshot_with_start()
        self.assertEqual(len(frames), 1)
        self.assertEqual(start, 101.5)

    def test_snapshot_with_start_empty(self):
        frames, start = FrameRing(retain_seconds=60.0).snapshot_with_start()
        self.assertEqual(frames, [])
        self.assertIsNone(start)


class TestFormatTimecode(unittest.TestCase):
    def test_frame_number(self):
        # wall 小数部分 0.75 @10fps → :07；日期部分跟随本地时区换算。
        import datetime
        wall = 1700000000.75
        tc = format_timecode(wall, 10.0)
        dt = datetime.datetime.fromtimestamp(wall)
        self.assertEqual(tc, f'{dt:%H:%M:%S}:07')

    def test_frame_number_truncated(self):
        self.assertTrue(format_timecode(100.99, 10.0).endswith(':09'))
        self.assertTrue(format_timecode(100.0, 10.0).endswith(':00'))

    def test_invalid_fps(self):
        with self.assertRaises(ValueError):
            format_timecode(100.0, 0)


class TestRecorderLifecycle(unittest.TestCase):
    def setUp(self):
        self.device = _FakeDevice()
        self.recorder = ScreenRecorder(
            self.device, fps=20.0, retain_seconds=5.0, output_dir=tempfile.gettempdir()
        )
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        try:
            self.recorder.stop()
        except Exception:
            pass
        self.assertFalse(self.recorder._started)

    def test_start_stop(self):
        self.recorder.start()
        self.assertTrue(self.recorder._started)
        time.sleep(0.3)
        # 独立采样：环自行增长，不依赖任何外部截图调用。
        self.assertGreater(len(self.recorder), 0)
        calls = self.device.raw_calls
        self.assertGreater(calls, 0)
        self.recorder.stop()
        self.assertFalse(self.recorder._started)
        # 停止后不再采样。
        time.sleep(0.15)
        self.assertEqual(self.device.raw_calls, calls)

    def test_double_start_raises(self):
        self.recorder.start()
        with self.assertRaises(RuntimeError):
            self.recorder.start()

    def test_stop_without_start_noop(self):
        self.recorder.stop()


class TestPausedSampling(unittest.TestCase):
    def _decode_last(self, recorder: ScreenRecorder) -> 'np.ndarray[Any, Any]':
        frames = recorder._ring.snapshot()
        self.assertGreater(len(frames), 0)
        buf = cv2.imdecode(np.frombuffer(frames[-1], dtype=np.uint8), cv2.IMREAD_COLOR)
        assert buf is not None
        return np.asarray(buf)

    def test_paused_frame_shape_and_content(self) -> None:
        img = np.asarray(ScreenRecorder._paused_frame(128, 160))
        self.assertEqual(img.shape, (128, 160, 3))
        self.assertGreater(float(img.mean()), 240)
        red = (img[:, :, 2] > 200) & (img[:, :, 0] < 150) & (img[:, :, 1] < 150)
        self.assertGreater(int(red.sum()), 100)

    def test_paused_without_geometry_skips_tick(self) -> None:
        device = _FakeDevice()
        recorder = ScreenRecorder(
            device, fps=20.0, retain_seconds=5.0,
            output_dir=tempfile.gettempdir(), is_paused=lambda: True,
        )
        try:
            recorder.start()
            time.sleep(0.2)
            # 从未采到实帧：无几何信息可合成，占位跳过且零设备调用。
            self.assertEqual(device.raw_calls, 0)
            self.assertEqual(len(recorder), 0)
        finally:
            recorder.stop()

    def test_paused_writes_placeholder_without_capture(self) -> None:
        device = _FakeDevice()
        paused = [False]
        recorder = ScreenRecorder(
            device, fps=20.0, retain_seconds=5.0,
            output_dir=tempfile.gettempdir(), is_paused=lambda: paused[0],
        )
        try:
            recorder.start()
            time.sleep(0.2)
            self.assertGreater(device.raw_calls, 0)
            paused[0] = True
            calls_before = device.raw_calls
            time.sleep(0.3)
            # 暂停期零设备调用，但环继续写入占位帧。
            self.assertEqual(device.raw_calls, calls_before)
            img = self._decode_last(recorder)
            self.assertEqual(img.shape, (128, 160, 3))
            self.assertGreater(float(img.mean()), 240)
        finally:
            recorder.stop()

    def test_resume_recaptures(self) -> None:
        device = _FakeDevice()
        paused = [True]
        recorder = ScreenRecorder(
            device, fps=20.0, retain_seconds=5.0,
            output_dir=tempfile.gettempdir(), is_paused=lambda: paused[0],
        )
        try:
            recorder.start()
            time.sleep(0.15)
            self.assertEqual(device.raw_calls, 0)
            paused[0] = False
            time.sleep(0.2)
            self.assertGreater(device.raw_calls, 0)
        finally:
            recorder.stop()


class TestDumpAndEncode(unittest.TestCase):
    def test_dump_empty_ring_returns_none(self):
        device = _FakeDevice()
        recorder = ScreenRecorder(device, output_dir=tempfile.gettempdir())
        try:
            self.assertIsNone(recorder.dump_for_crash())
        finally:
            recorder.stop()

    def test_dump_encodes_x265(self):
        device = _FakeDevice()
        with tempfile.TemporaryDirectory() as tmp:
            recorder = ScreenRecorder(
                device, fps=5.0, retain_seconds=60.0, output_dir=tmp
            )
            try:
                for i in range(5):
                    recorder._publish(np.full((128, 160, 3), i * 30, dtype=np.uint8))
                path = recorder.dump_for_crash()
                self.assertIsNotNone(path)
                assert path is not None
                self.assertTrue(path.endswith('.mp4'))
                self.assertTrue(os.path.basename(path).startswith('crash_'))
                # 后台编码完成前文件可能不存在，轮询等待。
                deadline = time.monotonic() + 60.0
                while not os.path.exists(path) and time.monotonic() < deadline:
                    time.sleep(0.2)
                self.assertTrue(os.path.exists(path), f'encode timed out: {path}')
                self.assertGreater(os.path.getsize(path), 0)
                import av

                with av.open(path) as container:
                    count = sum(1 for _ in container.decode(video=0))
                self.assertEqual(count, 5)
                # dump 全链路同样写 tmcd（起始值取自最老帧 wall-clock）。
                with av.open(path) as container:
                    self.assertEqual(
                        len([s for s in container.streams if s.type == 'data']), 1
                    )
                self.assertEqual(recorder.last_video_path, path)
            finally:
                recorder.stop()

    def test_encode_mp4_rejects_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'x.mp4')
            with self.assertRaises(ValueError):
                encode_mp4([], out, fps=10.0)
            with self.assertRaises(ValueError):
                encode_mp4([_jpeg(1, w=161)], out, fps=10.0)  # 奇数宽
            with self.assertRaises(ValueError):
                encode_mp4([_jpeg(1)], out, fps=0)
            with self.assertRaises(ValueError):
                encode_mp4([_jpeg(1)], out, fps=10.0, timecode='not-a-timecode')
            with self.assertRaises(ValueError):
                encode_mp4([_jpeg(1)], out, fps=10.0, timecode='12:34:56')  # 缺帧号

    def test_encode_mp4_writes_tmcd(self):
        import av

        frames = [_jpeg((i * 30) % 256) for i in range(5)]
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'tc.mp4')
            encode_mp4(frames, out, fps=10.0, timecode='12:34:56:07')
            with av.open(out) as container:
                data_streams = [s for s in container.streams if s.type == 'data']
                self.assertEqual(len(data_streams), 1)
            raw = b''
            with av.open(out) as container:
                for pkt in container.demux():
                    if pkt.stream.type == 'data':
                        raw = bytes(pkt)
                        break
            self.assertGreaterEqual(len(raw), 4)
            # 12:34:56:07 @10fps = 452967
            self.assertEqual(struct.unpack('>I', raw[:4])[0], 452967)

    def test_encode_mp4_without_timecode_has_no_tmcd(self):
        import av

        frames = [_jpeg(1), _jpeg(2)]
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'notc.mp4')
            encode_mp4(frames, out, fps=10.0)
            with av.open(out) as container:
                self.assertEqual(
                    [s for s in container.streams if s.type == 'data'], []
                )

    def test_wait_for_video_success(self):
        device = _FakeDevice()
        with tempfile.TemporaryDirectory() as tmp:
            recorder = ScreenRecorder(device, fps=5.0, output_dir=tmp)
            try:
                for i in range(3):
                    recorder._publish(np.full((128, 160, 3), i * 30, dtype=np.uint8))
                path = recorder.dump_for_crash()
                assert path is not None
                self.assertTrue(recorder.wait_for_video(path, timeout=60.0))
                self.assertTrue(os.path.exists(path))
            finally:
                recorder.stop()

    def test_wait_for_video_unknown_path(self):
        device = _FakeDevice()
        recorder = ScreenRecorder(device, output_dir=tempfile.gettempdir())
        try:
            self.assertFalse(recorder.wait_for_video(os.path.join('no', 'such.mp4'), timeout=1.0))
        finally:
            recorder.stop()


class TestEncodeWithoutAv(unittest.TestCase):
    def test_encode_mp4_without_av_raises_runtime_error(self):
        # KAA-632：av native DLL 被系统策略拦截时，编码期 fast-fail 为
        # RuntimeError（而非 ImportError 透传），且模块顶层导入不受影响。
        import sys
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'x.mp4')
            with patch.dict(sys.modules, {'av': None}):
                with self.assertRaisesRegex(RuntimeError, 'PyAV is not available'):
                    encode_mp4([_jpeg(1)], out, fps=10.0)

    def test_module_import_does_not_require_av(self):
        # 顶层导入 screen_recorder 不得触发 av 导入（延迟到 encode_mp4 内）。
        import importlib
        import sys
        from unittest.mock import patch
        with patch.dict(sys.modules, {'av': None}):
            mod = importlib.reload(sys.modules['kaa.util.screen_recorder'])
        try:
            self.assertTrue(hasattr(mod, 'ScreenRecorder'))
        finally:
            importlib.reload(mod)


class TestCrashRouting(unittest.TestCase):
    """崩溃路由走 ctx.bot._recorder：归属 Kaa 实例，无全局注册表。"""

    def test_bot_recorder_lookup(self):
        device = _FakeDevice()
        recorder = ScreenRecorder(device, output_dir=tempfile.gettempdir())
        try:
            ctx = _FakeCtx(_FakeBot(recorder))
            self.assertIs(_crash_recorder(ctx), recorder)
        finally:
            recorder.stop()

    def test_missing_recorder_skips(self):
        self.assertIsNone(_crash_recorder(None))
        self.assertIsNone(_crash_recorder(_FakeCtx(None)))
        # Kaa 初始态（_recorder 为 None）与异构 ctx 同样跳过。
        self.assertIsNone(_crash_recorder(_FakeCtx(_FakeBot(None))))
        self.assertIsNone(_crash_recorder(object()))


if __name__ == '__main__':
    unittest.main()
