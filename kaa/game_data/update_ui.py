"""Game data download progress window (tkinter, thread-safe)."""

import logging
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

logger = logging.getLogger(__name__)

_MB = 1024 * 1024
_KB = 1024

# Column layout: (header_text, tk.Label width in chars or None for the bar)
_COLS = [
    ("文件名",  18),
    ("百分比",   7),
    (None,    None),   # progress bar column
    ("速度",    10),
    ("已下载",  10),
    ("总大小",  10),
]
_BAR_COL = 2
_BAR_LENGTH = 220
_PAD = 6


def _fmt_size(n: int) -> str:
    if n >= _MB:
        return f"{n / _MB:.1f} MB"
    if n >= _KB:
        return f"{n / _KB:.1f} KB"
    return f"{n} B"


def _fmt_speed(bps: float) -> str:
    if bps <= 0:
        return "—"
    if bps >= _MB:
        return f"{bps / _MB:.1f} MB/s"
    return f"{bps / _KB:.0f} KB/s"


class _FileRow:
    """Widgets + speed state for one downloaded file."""

    _EMA = 0.25  # EMA smoothing factor for speed

    def __init__(self, parent: tk.Frame, name: str, row: int):
        self._speed_ema = 0.0
        self._last_t = time.monotonic()
        self._last_bytes = 0

        kw: dict[str, Any] = {"padx": (0, _PAD)}

        tk.Label(parent, text=name, anchor='w', width=_COLS[0][1]).grid(
            row=row, column=0, sticky='w', **kw)

        self._pct = tk.StringVar(value="0.0%")
        tk.Label(parent, textvariable=self._pct, anchor='e', width=_COLS[1][1]).grid(
            row=row, column=1, **kw)

        self._bar_val = tk.DoubleVar(value=0.0)
        ttk.Progressbar(
            parent, variable=self._bar_val,
            maximum=100, mode='determinate', length=_BAR_LENGTH,
        ).grid(row=row, column=_BAR_COL, sticky='ew', **kw)

        self._speed = tk.StringVar(value="—")
        tk.Label(parent, textvariable=self._speed, anchor='e', width=_COLS[3][1]).grid(
            row=row, column=3, **kw)

        self._dl = tk.StringVar(value="0 B")
        tk.Label(parent, textvariable=self._dl, anchor='e', width=_COLS[4][1]).grid(
            row=row, column=4, **kw)

        self._total = tk.StringVar(value="—")
        tk.Label(parent, textvariable=self._total, anchor='e', width=_COLS[5][1]).grid(
            row=row, column=5)

    def update(self, downloaded: int, total: int, t: float) -> None:
        dt = t - self._last_t
        if dt > 0.05:
            instant = (downloaded - self._last_bytes) / dt
            self._speed_ema = (
                instant if self._speed_ema == 0
                else self._EMA * instant + (1 - self._EMA) * self._speed_ema
            )
            self._last_t = t
            self._last_bytes = downloaded

        pct = downloaded / total * 100 if total else 0.0
        self._bar_val.set(pct)
        self._pct.set(f"{pct:.1f}%")
        self._speed.set(_fmt_speed(self._speed_ema))
        self._dl.set(_fmt_size(downloaded))
        self._total.set(_fmt_size(total) if total else "—")

    def mark_done(self) -> None:
        self._bar_val.set(100.0)
        self._pct.set("100%")
        self._speed.set("—")


class GameDataUpdateUI:
    """
    Thread-safe tkinter progress window for game data downloads.

    - Window appears lazily on first on_file_progress() call.
    - Each unique filename gets its own row (added on demand).
    - Call mark_complete() when finished; window closes after 2 s.
    """

    def __init__(self) -> None:
        self._q: queue.Queue = queue.Queue()
        self._root: Optional[tk.Tk] = None
        self._grid: Optional[tk.Frame] = None
        self._rows: dict[str, _FileRow] = {}
        self._row_count = 0
        self._started = False

    # ── public API (thread-safe) ──────────────────────────────────────────

    def on_file_progress(self, name: str, downloaded: int, total: int) -> None:
        self._ensure_window()
        self._q.put(('progress', name, downloaded, total, time.monotonic()))

    def on_file_done(self, name: str) -> None:
        if self._started:
            self._q.put(('done', name))

    def mark_complete(self) -> None:
        if self._started:
            self._q.put(('complete',))

    def close(self) -> None:
        if self._started:
            self._q.put(('close',))

    # ── internals ─────────────────────────────────────────────────────────

    def _ensure_window(self) -> None:
        if self._started:
            return
        self._started = True
        ready = threading.Event()
        threading.Thread(target=self._run_ui, args=(ready,), daemon=True).start()
        ready.wait(timeout=5.0)

    def _run_ui(self, ready: threading.Event) -> None:
        try:
            root = tk.Tk()
            self._root = root
            root.title("游戏数据更新")
            root.resizable(False, False)
            root.protocol("WM_DELETE_WINDOW", root.destroy)

            tk.Label(root, text="正在更新游戏数据，请稍候…",
                     font=('', 10, 'bold'), anchor='w').pack(
                fill='x', padx=12, pady=(12, 6))

            outer = tk.Frame(root, padx=12, pady=8)
            outer.pack(fill='both', expand=True)

            # Header row
            for col, (text, width) in enumerate(_COLS):
                if col == _BAR_COL:
                    tk.Label(outer, text="进度条", anchor='w').grid(
                        row=0, column=col, sticky='w',
                        padx=(0, _PAD), pady=(0, 4))
                else:
                    tk.Label(outer, text=text, width=width,
                             anchor='e' if col > 0 else 'w',
                             fg='#888').grid(
                        row=0, column=col,
                        padx=(0, _PAD) if col < len(_COLS) - 1 else 0,
                        pady=(0, 4))

            ttk.Separator(outer, orient='horizontal').grid(
                row=1, column=0, columnspan=len(_COLS),
                sticky='ew', pady=(0, 4))

            self._grid = outer
            self._row_count = 2  # rows 0=header, 1=separator, 2+ = data

            ready.set()
            root.after(50, self._tick)
            root.mainloop()
        except Exception:
            logger.exception("游戏数据更新界面启动失败")
            ready.set()

    def _tick(self) -> None:
        if not (self._root and self._root.winfo_exists()):
            return
        try:
            while True:
                self._dispatch(self._q.get_nowait())
        except queue.Empty:
            pass
        self._root.after(50, self._tick)

    def _dispatch(self, msg: tuple) -> None:
        kind = msg[0]
        root = self._root
        if root is None:
            return

        if kind == 'progress':
            _, name, downloaded, total, t = msg
            grid = self._grid
            if grid is None:
                return
            if name not in self._rows:
                row = _FileRow(grid, name, self._row_count)
                self._rows[name] = row
                self._row_count += 1
                root.update_idletasks()
                root.geometry('')
            self._rows[name].update(downloaded, total, t)

        elif kind == 'done':
            name = msg[1]
            if name in self._rows:
                self._rows[name].mark_done()

        elif kind == 'complete':
            root.after(2000, root.destroy)

        elif kind == 'close':
            root.destroy()
