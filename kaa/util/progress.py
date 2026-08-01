"""下载进度聚合工具：按文件聚合进度，计算 EMA 速度并按节流间隔刷新。

供 Splash 下载进度展示与后台游戏数据更新控制器共用，避免进度计算逻辑重复。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

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
        return f"{n / _MB:.1f} MB"
    if n >= _KB:
        return f"{n / _KB:.1f} KB"
    return f"{n} B"


def _fmt_size_pair(downloaded: int, total: int) -> str:
    if total <= 0:
        return f"{_fmt_size(downloaded)} / —"
    if total >= _MB:
        return f"{downloaded / _MB:.1f} / {total / _MB:.1f} MB"
    if total >= _KB:
        return f"{downloaded / _KB:.1f} / {total / _KB:.1f} KB"
    return f"{downloaded} / {total} B"


def _fmt_speed(bps: float) -> str:
    if bps <= 0:
        return "—"
    if bps >= _MB:
        return f"{bps / _MB:.1f} MB/s"
    return f"{bps / _KB:.0f} KB/s"


@dataclass
class _SpeedState:
    last_t: float = field(default_factory=time.monotonic)
    last_bytes: int = 0
    speed_ema: float = 0.0


class ProgressAggregator:
    """按文件名聚合下载进度，计算 EMA 速度并按节流间隔批量导出。

    用法：::

        agg = ProgressAggregator()
        agg.update('game.db.zst', 1024, 102400)
        files = agg.flush()          # 节流；未到间隔时返回 None
        files = agg.force_flush()    # 完成时兜底，总是返回最新进度

    返回的每个进度 dict 字段：``fileName`` / ``percent`` / ``speed`` /
    ``speedText`` / ``sizeText``。
    """

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
        self._files: dict[str, dict] = {}
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
        self._files[name] = {
            'fileName': name,
            'percent': pct,
            'speed': speed_bps,
            'speedText': _fmt_speed(speed_bps),
            'sizeText': _fmt_size_pair(downloaded, total),
        }
        self._dirty = True

    def flush(self) -> list[dict] | None:
        """若距上次刷新已超过节流间隔且有更新，返回全部文件进度并重置；
        否则返回 None。"""
        if not self._dirty:
            return None
        if time.monotonic() - self._last_flush < self._flush_interval:
            return None
        return self.force_flush()

    def force_flush(self) -> list[dict] | None:
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
