"""运行时后台录屏：独立采样线程 + JPEG 时间环 + 崩溃时 PyAV 离线转 x265。

设计说明（独立采样，不进 Loop、不开进程、不接管 hook）：
- ``Loop.tick()`` 在 runner 线程同步执行 ``sleep + screenshot + 回调``，
  把采集/编码塞进去会拖慢自动化节拍；且 Loop 断续（任务间隙无 Loop、
  长 OCR 阻塞停顿），帧率抖动，给不出稳定的 10fps。
- 采集源（PrintWindow / nemu_ipc）近实时，10fps 只需一个独立采样线程；
  单独进程要重建第二套 Device 连接，多一份争抢与故障面，只为防硬杀进程，
  而 kaa 的崩溃是 Python 层异常（进程存活），不需要。
- 不接管 ``screenshot_hook_before``：实测 nemu_ipc 截图-vs-截图并发安全
  （4 线程 x25s 零异常、无延迟退化），Loop 与采样线程各采各的，互不阻塞、
  互不拖累；recorder 故障也不可能影响任务逻辑。点屏-vs-截图的交叉并发
  未覆盖，为已知残余风险。
- 暂停时不碰设备：采样节拍内 ``is_paused()`` 为真则合成白底红字
  ``Script Paused`` 帧入环，保持时间轴连续（tmcd/时长与日志对齐），
  且不采集用户可能正在操作的画面。

内存与编码：
- 环内只存 JPEG bytes（720x1280 q80 约 100-200KB/帧，60s/10fps 约
  60-120MB）；raw 600 帧约 1.6GB，不可行。
- x265 medium 只在崩溃后离线编码（后台线程），常驻期零编码开销；
  崩溃时自动化已停，转码再慢也不阻塞主链路。
- ``av`` 为硬依赖（见 pyproject），顶层导入；libx265 缺失时编码期 fast-fail，
  不静默降级。

录屏线程自身的采集异常只记日志、不抛入主链路（诊断功能不得带崩任务，
此处隔离是刻意设计，非 fallback）。
"""

import logging
import os
import re
import threading
import time
from collections import deque
from datetime import datetime, timezone
from fractions import Fraction
from typing import Callable, cast

import av
import cv2
import numpy as np
import numpy.typing as npt
from cv2.typing import MatLike
from kotonebot.client.device import Device

logger = logging.getLogger(__name__)

# JPEG 时间环单帧上限兜底（按 60s/10fps=600 帧再放大 half，避免时钟异常时无界增长）。
_MAX_RING_FRAMES = 900

_PAUSED_TEXT = 'Script Paused'


def _never_paused() -> bool:
    """默认暂停谓词：永不暂停。"""
    return False


class FrameRing:
    """按时间淘汰的 JPEG 帧环。线程安全。

    每帧附单调时钟（淘汰用）与 wall-clock（tmcd 起始时间码用）。
    """

    def __init__(
        self,
        retain_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if retain_seconds <= 0:
            raise ValueError(f'retain_seconds must be positive, got {retain_seconds}')
        self._retain_seconds = retain_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._frames: deque[tuple[float, float, bytes]] = deque()

    def append(self, jpeg_bytes: bytes, *, wall: float | None = None) -> None:
        """追加一帧并淘汰过期帧。

        :param jpeg_bytes: 非空 JPEG bytes。
        :param wall: 拍摄 wall-clock（秒）；None 则取当前时间。
        """
        if not jpeg_bytes:
            raise ValueError('jpeg_bytes must be non-empty.')
        now = self._clock()
        with self._lock:
            self._frames.append((now, wall if wall is not None else time.time(), jpeg_bytes))
            self._evict_locked(now)

    def snapshot(self) -> list[bytes]:
        """返回环内未过期帧的时间序拷贝（只含 bytes，不含时间戳）。"""
        frames, _ = self.snapshot_with_start()
        return frames

    def snapshot_with_start(self) -> tuple[list[bytes], float | None]:
        """返回 ``(时间序 bytes, 最老帧 wall-clock)``；环为空时后者为 None。"""
        now = self._clock()
        with self._lock:
            self._evict_locked(now)
            frames = [data for _, _, data in self._frames]
            start = self._frames[0][1] if self._frames else None
            return frames, start

    def __len__(self) -> int:
        with self._lock:
            return len(self._frames)

    def _evict_locked(self, now: float) -> None:
        cutoff = now - self._retain_seconds
        while self._frames and self._frames[0][0] < cutoff:
            self._frames.popleft()
        while len(self._frames) > _MAX_RING_FRAMES:
            self._frames.popleft()


def format_timecode(wall: float, fps: float) -> str:
    """将 wall-clock 换算为 movenc 接受的非丢帧起始时间码（本地时区）。

    :param wall: 秒级 Unix 时间戳。
    :param fps: 视频帧率；帧号部分按此换算并截断到 ``fps - 1``。
    :return: ``HH:MM:SS:FF`` 字符串。
    """
    if fps <= 0:
        raise ValueError(f'fps must be positive, got {fps}.')
    dt = datetime.fromtimestamp(wall)
    ff = min(int((wall % 1) * fps), int(fps) - 1)
    return f'{dt:%H:%M:%S}:{ff:02d}'


def encode_mp4(
    jpeg_frames: list[bytes],
    output_path: str,
    *,
    fps: float,
    crf: int = 34,
    preset: str = 'medium',
    timecode: str | None = None,
) -> str:
    """将 JPEG 帧序列离线编码为 x265 MP4。

    :param jpeg_frames: 非空 JPEG bytes 列表（时间序）。
    :param output_path: 输出 .mp4 路径（父目录需已存在）。
    :param fps: 输出帧率。
    :param crf: x265 CRF。
    :param preset: x265 preset。
    :param timecode: 起始时间码（``HH:MM:SS:FF``，非丢帧）；提供时写入
        tmcd 轨道（mp4 需强制 ``write_tmcd``，mov 下自动）。None 则不写。
    :return: output_path。
    :raises ValueError: 帧列表为空、单帧解码失败、分辨率非偶数、时间码
        格式非法时抛出。
    :raises RuntimeError: PyAV/libx265 不可用时抛出。
    """
    if not jpeg_frames:
        raise ValueError('jpeg_frames must be non-empty.')
    if fps <= 0:
        raise ValueError(f'fps must be positive, got {fps}.')
    if timecode is not None and not re.fullmatch(r'\d{2}:\d{2}:\d{2}[:;]\d{2}', timecode):
        raise ValueError(f'Invalid timecode: {timecode!r}.')
    try:
        av.Codec('libx265', 'w')
    except Exception as e:
        raise RuntimeError('libx265 encoder is not available in this PyAV build.') from e

    images: list[npt.NDArray[np.uint8]] = []
    for i, data in enumerate(jpeg_frames):
        buf = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if buf is None:
            raise ValueError(f'Failed to decode JPEG frame at index {i}.')
        if buf.dtype != np.uint8:
            raise ValueError(f'Unexpected frame dtype at index {i}: {buf.dtype}.')
        images.append(cast('npt.NDArray[np.uint8]', buf))
    h, w = images[0].shape[:2]
    if h % 2 != 0 or w % 2 != 0:
        raise ValueError(f'x265 yuv420p requires even dimensions, got {w}x{h}.')

    container = av.open(output_path, mode='w')
    if timecode is not None:
        # tmcd 轨道：mp4 下必须强制 write_tmcd（mov 下自动），起始值走 metadata。
        container.container_options.update({'write_tmcd': '1'})
        container.metadata['timecode'] = timecode
    try:
        # PyAV 要求 rate 为 int/Fraction，float 会抛 AttributeError。
        stream = container.add_stream('libx265', rate=Fraction(fps).limit_denominator(1000))
        # add_stream 按 codec 名返回 Stream 联合类型，断言收窄为 VideoStream。
        assert isinstance(stream, av.VideoStream), f'Unexpected stream type: {type(stream)}.'
        stream.width = w
        stream.height = h
        stream.pix_fmt = 'yuv420p'
        stream.options = {'crf': str(crf), 'preset': preset}
        for i, img in enumerate(images):
            frame = av.VideoFrame.from_ndarray(img, format='bgr24')
            frame.pts = i
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()
    return output_path


class ScreenRecorder:
    """后台录屏器：独立采样线程 + JPEG 时间环，崩溃时离线编码。

    与任务逻辑完全解耦：采样线程调裸 ``Device.screenshot_raw()``（不走 hook、
    不写 ``vars.screenshot_data``），Loop 的截图原样直采。两者并发打 impl
    经实测安全（nemu_ipc），互不持有对方的锁。

    :param device: 运行中的 Device（采样线程调用其 ``screenshot_raw``）。
    :param fps: 采样帧率。
    :param retain_seconds: 环保留时长（秒）。
    :param jpeg_quality: 环内 JPEG 质量（0-100）。
    :param output_dir: 崩溃视频落盘目录。
    :param crf: 离线 x265 CRF。
    :param preset: 离线 x265 preset。
    :param is_paused: 暂停状态谓词（跨线程调用）；为真时合成分辨率一致的
        占位帧而非设备截图。None 表示永不暂停。
    """

    def __init__(
        self,
        device: Device,
        *,
        fps: float = 10.0,
        retain_seconds: float = 60.0,
        jpeg_quality: int = 80,
        output_dir: str = os.path.join('logs', 'crash_videos'),
        crf: int = 34,
        preset: str = 'medium',
        is_paused: Callable[[], bool] | None = None,
    ) -> None:
        if device is None:
            raise ValueError('device must not be None.')
        if fps <= 0:
            raise ValueError(f'fps must be positive, got {fps}.')
        if not 1 <= jpeg_quality <= 100:
            raise ValueError(f'jpeg_quality must be in 1..100, got {jpeg_quality}.')
        self._device = device
        self._fps = fps
        self._period = 1.0 / fps
        self._jpeg_quality = jpeg_quality
        self._output_dir = output_dir
        self._crf = crf
        self._preset = preset
        if is_paused is not None:
            self._is_paused = is_paused
        else:
            self._is_paused = _never_paused

        self._ring = FrameRing(retain_seconds)

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = False
        self._last_video_path: str | None = None
        # 最近一次实采帧的 (h, w)，用于合成同分辨率暂停占位帧。
        self._frame_shape: tuple[int, int] | None = None
        # 后台编码任务的完成信号（path → Event）与结果（path → 是否成功），
        # 供导出报告等待用；附时间戳用于淘汰旧条目。
        self._encode_lock = threading.Lock()
        self._encode_events: dict[str, threading.Event] = {}
        self._encode_ok: dict[str, bool] = {}
        self._encode_time: dict[str, float] = {}

    # -- 生命周期 ------------------------------------------------------

    def start(self) -> None:
        """启动采样线程。重复启动抛错。"""
        if self._started:
            raise RuntimeError('ScreenRecorder is already started.')
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._sample_loop, name='kaa-screen-recorder', daemon=True
        )
        self._thread.start()
        self._started = True
        logger.info(
            'Screen recorder started (%.1ffps, retain %.0fs).',
            self._fps, self._ring._retain_seconds,
        )

    def stop(self) -> None:
        """停止采样线程。未启动时为 no-op。"""
        if not self._started:
            return
        self._started = False
        self._stop_event.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
            if thread.is_alive():
                logger.warning('Screen recorder thread did not stop within 2s.')
        logger.info('Screen recorder stopped.')

    @property
    def last_video_path(self) -> str | None:
        """最近一次崩溃 dump 的视频路径（编码可能仍在后台进行）。"""
        return self._last_video_path

    def __len__(self) -> int:
        return len(self._ring)

    # -- 采集 ----------------------------------------------------------

    def _capture_frame(self) -> MatLike:
        """单次全量采集：raw + scaler transform。"""
        raw = self._device.screenshot_raw()
        return self._device.scaler.transform_screenshot(raw)

    @staticmethod
    def _paused_frame(height: int, width: int) -> MatLike:
        """合成暂停占位帧：白底 + 居中红色文字，分辨率与实采帧一致。"""
        img = np.full((height, width, 3), 255, dtype=np.uint8)
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(_PAUSED_TEXT, font, 1.0, 2)
        scale = (width * 0.6) / tw if tw > 0 else 1.0
        thickness = max(1, int(round(scale)))
        (tw, th), _ = cv2.getTextSize(_PAUSED_TEXT, font, scale, thickness)
        org = ((width - tw) // 2, (height + th) // 2)
        cv2.putText(img, _PAUSED_TEXT, org, font, scale, (0, 0, 255), thickness, cv2.LINE_AA)
        return img

    def _publish(self, img: MatLike) -> None:
        """发布一帧：JPEG 入环（附 wall-clock 供 tmcd 用）。"""
        ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality])
        if not ok:
            raise RuntimeError('Failed to JPEG-encode captured frame.')
        self._ring.append(bytes(buf), wall=time.time())

    def _sample_loop(self) -> None:
        """采样线程主循环：固定节拍采集，异常只记日志。

        暂停期间不调用设备截图，改用同分辨率占位帧保持时间轴连续；
        尚未采到任何实帧（无几何信息）时跳过本拍。
        """
        deadline = time.monotonic()
        while not self._stop_event.is_set():
            deadline += self._period
            try:
                if self._is_paused():
                    if self._frame_shape is not None:
                        h, w = self._frame_shape
                        self._publish(self._paused_frame(h, w))
                else:
                    img = self._capture_frame()
                    self._frame_shape = (img.shape[0], img.shape[1])
                    self._publish(img)
            except Exception:
                # 诊断隔离：采集失败（设备停止/窗口消失）不得带崩主链路。
                logger.warning('Screen recorder capture failed.', exc_info=True)
            delay = deadline - time.monotonic()
            if delay <= 0:
                # 采集耗时超过节拍时直接跟上，不补帧、不 sleep 为负。
                deadline = time.monotonic()
                continue
            self._stop_event.wait(delay)

    # -- 崩溃 dump ------------------------------------------------------

    def dump_for_crash(self) -> str | None:
        """快照时间环并在后台线程离线编码为 x265 MP4，立即返回路径。

        起始时间码取自最老帧的 wall-clock，与日志时间轴对齐。

        :return: 输出路径；环为空时返回 None。
        """
        frames, start_wall = self._ring.snapshot_with_start()
        if not frames or start_wall is None:
            logger.warning('Screen recorder ring is empty, no crash video to dump.')
            return None
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        filename = f'crash_{stamp}.mp4'
        os.makedirs(self._output_dir, exist_ok=True)
        path = os.path.join(self._output_dir, filename)
        self._last_video_path = path
        timecode = format_timecode(start_wall, self._fps)
        done = threading.Event()
        with self._encode_lock:
            now = time.monotonic()
            for p in [p for p, t in self._encode_time.items() if now - t > 3600]:
                del self._encode_time[p]
                self._encode_events.pop(p, None)
                self._encode_ok.pop(p, None)
            self._encode_events[path] = done
            self._encode_time[path] = now
        thread = threading.Thread(
            target=self._encode_and_log,
            args=(frames, path, timecode),
            name='kaa-crash-video-encode',
            daemon=True,
        )
        thread.start()
        logger.warning('Crash video dump started: %s (%d frames).', path, len(frames))
        return path

    def wait_for_video(self, path: str, timeout: float | None = None) -> bool:
        """等待指定路径的后台编码完成。

        :param path: ``dump_for_crash`` 返回的路径。
        :param timeout: 最长等待秒数；None 则一直等待。
        :return: 编码成功且文件存在时 True；未知路径/超时/编码失败时 False。
        """
        with self._encode_lock:
            done = self._encode_events.get(path)
        if done is None:
            return False
        done.wait(timeout)
        with self._encode_lock:
            ok = self._encode_ok.get(path, False)
        return ok and os.path.exists(path)

    def _encode_and_log(self, frames: list[bytes], path: str, timecode: str) -> None:
        ok = False
        try:
            encode_mp4(frames, path, fps=self._fps, crf=self._crf, preset=self._preset,
                       timecode=timecode)
            ok = True
        except Exception:
            logger.warning('Crash video encoding failed: %s.', path, exc_info=True)
        with self._encode_lock:
            self._encode_ok[path] = ok
            done = self._encode_events.get(path)
        if done is not None:
            done.set()
        if ok:
            logger.warning('Crash video saved: %s.', path)
