"""下载进度聚合与任务进度桥接：EMA 速度计算、节流刷新与 QML 进度推送。"""
import logging
import time
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from PySide6.QtCore import Property, QObject, Signal

logger = logging.getLogger(__name__)

_MB = 1024 * 1024
_KB = 1024

# 速度计算的 EMA 平滑系数
_EMA_ALPHA = 0.25
# 两次 flush 之间的最小时间间隔（秒），避免高频 emit 刷爆 UI
_FLUSH_INTERVAL = 0.15
# 计算瞬时速度所需的最小时间差（秒）
_SPEED_MIN_DT = 0.05


def _fmt_size(n: int) -> str:
    if n >= _MB:
        return f'{n / _MB:.1f} MB'
    if n >= _KB:
        return f'{n / _KB:.1f} KB'
    return f'{n} B'


def _fmt_size_pair(downloaded: int, total: int) -> str:
    if total <= 0:
        return f'{_fmt_size(downloaded)} / —'
    if total >= _MB:
        return f'{downloaded / _MB:.1f} / {total / _MB:.1f} MB'
    if total >= _KB:
        return f'{downloaded / _KB:.1f} / {total / _KB:.1f} KB'
    return f'{downloaded} / {total} B'


def _fmt_speed(bps: float) -> str:
    if bps <= 0:
        return '—'
    if bps >= _MB:
        return f'{bps / _MB:.1f} MB/s'
    return f'{bps / _KB:.0f} KB/s'


class FileProgressItem(BaseModel):
    """单个文件的下载进度条目（QML 展示用）。"""

    file_name: str = Field(serialization_alias='fileName')
    """文件名。"""
    percent: float = 0.0
    """下载百分比（0-100，保留 1 位小数）。"""
    speed: float = 0.0
    """EMA 速度（字节/秒）。"""
    speed_text: str = Field(default='—', serialization_alias='speedText')
    """格式化的速度文本。"""
    size_text: str = Field(default='—', serialization_alias='sizeText')
    """格式化的大小文本（已下载 / 总量）。"""

    model_config = {'populate_by_name': True}


@dataclass
class _SpeedState:
    """单文件速度计算状态。"""

    last_t: float = field(default_factory=time.monotonic)
    """上次采样时刻（monotonic 秒）。"""
    last_bytes: int = 0
    """上次采样字节数。"""
    speed_ema: float = 0.0
    """EMA 平滑后的速度（字节/秒）。"""


class ProgressAggregator:
    """按文件名聚合下载进度，计算 EMA 速度并按节流间隔批量导出。"""

    def __init__(
        self,
        flush_interval: float = _FLUSH_INTERVAL,
        ema_alpha: float = _EMA_ALPHA,
    ) -> None:
        """
        :param flush_interval: 两次 flush 之间的最小时间间隔（秒）
        :param ema_alpha: EMA 平滑系数
        """
        self._flush_interval = flush_interval
        self._ema_alpha = ema_alpha
        self._files: dict[str, FileProgressItem] = {}
        self._speed_state: dict[str, _SpeedState] = {}
        self._last_flush: float = 0.0
        self._dirty: bool = False

    def update(self, name: str, downloaded: int, total: int) -> None:
        """记录一次进度更新，计算该文件的 EMA 速度并缓存进度信息。

        :param name: 文件名（如 ``'game.db.zst'``）
        :param downloaded: 已下载字节数
        :param total: 文件总字节数（未知时为 0）
        """
        now = time.monotonic()
        state = self._speed_state.get(name)
        if state is None:
            state = _SpeedState(last_t=now)
            self._speed_state[name] = state

        dt = now - state.last_t
        if dt > _SPEED_MIN_DT:
            instant = (downloaded - state.last_bytes) / dt
            # EMA 平滑：首个采样直接采用瞬时值，后续按系数混合
            ema = state.speed_ema
            ema = (
                instant
                if ema == 0
                else self._ema_alpha * instant + (1 - self._ema_alpha) * ema
            )
            state.speed_ema = ema
            state.last_t = now
            state.last_bytes = downloaded
            speed_bps = ema
        else:
            speed_bps = state.speed_ema

        pct = round(downloaded / total * 100, 1) if total else 0.0
        self._files[name] = FileProgressItem(
            file_name=name,
            percent=pct,
            speed=speed_bps,
            speed_text=_fmt_speed(speed_bps),
            size_text=_fmt_size_pair(downloaded, total),
        )
        self._dirty = True

    def flush(self) -> list[FileProgressItem] | None:
        """若距上次刷新已超过节流间隔且有更新，返回全部文件进度；否则返回 None。"""
        if not self._dirty:
            return None
        if time.monotonic() - self._last_flush < self._flush_interval:
            return None
        return self.force_flush()

    def force_flush(self) -> list[FileProgressItem] | None:
        """无条件返回全部文件进度并重置节流状态（供完成/结束时兜底）。"""
        if not self._dirty:
            return None
        self._dirty = False
        self._last_flush = time.monotonic()
        return list(self._files.values())

    def clear(self) -> None:
        """清空所有进度与速度状态。"""
        self._files.clear()
        self._speed_state.clear()
        self._dirty = False


class ProgressBridge(QObject):
    """向 QML 推送单个 Tab 的任务进度信息。

    下游 session 通过 :meth:`update_status` / :meth:`update_progress` /
    :meth:`set_error` 推送状态；可在任意线程调用，信号跨线程自动排队。
    """

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._status_text = ''
        self._progress_percent = 0
        self._last_error_text = ''

    # ── 下游推送 API ──────────────────────────────────────

    def update_status(self, text: str) -> None:
        """更新状态文本。

        :param text: 状态描述（如 ``'运行中: 日常'``）
        """
        self._status_text = text
        self.changed.emit()

    def update_progress(self, percent: int) -> None:
        """更新整体进度百分比。

        :param percent: 0-100 整数
        """
        self._progress_percent = percent
        self.changed.emit()

    def set_error(self, text: str) -> None:
        """记录最近一次错误文本并更新状态。

        :param text: 错误描述
        """
        self._last_error_text = text
        self._status_text = '出错'
        self.changed.emit()

    def reset(self) -> None:
        """重置进度状态（新一轮运行前调用）。"""
        self._status_text = ''
        self._progress_percent = 0
        self._last_error_text = ''
        self.changed.emit()

    # ── Qt Properties ─────────────────────────────────────

    def _get_status_text(self) -> str:
        return self._status_text

    def _get_progress_percent(self) -> int:
        return self._progress_percent

    def _get_last_error_text(self) -> str:
        return self._last_error_text

    statusText = Property(str, _get_status_text, notify=changed)
    progressPercent = Property(int, _get_progress_percent, notify=changed)
    lastErrorText = Property(str, _get_last_error_text, notify=changed)
