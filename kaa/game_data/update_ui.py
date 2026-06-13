"""Game data download progress window (PySide6, thread-safe)."""

import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Union

from PySide6.QtCore import QTimer
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

_A = Qt.AlignmentFlag
_WF = Qt.WindowType

logger = logging.getLogger(__name__)

_MB = 1024 * 1024
_KB = 1024

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


# ── messages ──────────────────────────────────────────────────────────────────

@dataclass
class _MsgProgress:
    name: str
    downloaded: int
    total: int
    t: float

@dataclass
class _MsgComplete:
    pass

@dataclass
class _MsgClose:
    pass

_Msg = Union[_MsgProgress, _MsgComplete, _MsgClose]


# ── widgets ───────────────────────────────────────────────────────────────────

class _FileRow:
    """Widgets + speed state for one downloaded file."""

    _EMA = 0.25

    def __init__(self, layout: QGridLayout, name: str, row: int):
        self._speed_ema = 0.0
        self._last_t = time.monotonic()
        self._last_bytes = 0

        self._name_lbl = QLabel(name)
        self._name_lbl.setAlignment(_A.AlignLeft | _A.AlignVCenter)
        self._name_lbl.setFixedWidth(160)
        layout.addWidget(self._name_lbl, row, 0)

        self._pct_lbl = QLabel("0.0%")
        self._pct_lbl.setAlignment(_A.AlignRight | _A.AlignVCenter)
        self._pct_lbl.setFixedWidth(55)
        layout.addWidget(self._pct_lbl, row, 1)

        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setMinimumWidth(160)
        self._bar.setMinimumHeight(24)
        layout.addWidget(self._bar, row, 2)

        self._speed_lbl = QLabel("—")
        self._speed_lbl.setAlignment(_A.AlignRight | _A.AlignVCenter)
        self._speed_lbl.setFixedWidth(85)
        layout.addWidget(self._speed_lbl, row, 3)

        self._dl_lbl = QLabel("0 B")
        self._dl_lbl.setAlignment(_A.AlignRight | _A.AlignVCenter)
        self._dl_lbl.setFixedWidth(75)
        layout.addWidget(self._dl_lbl, row, 4)

        self._total_lbl = QLabel("—")
        self._total_lbl.setAlignment(_A.AlignRight | _A.AlignVCenter)
        self._total_lbl.setFixedWidth(75)
        layout.addWidget(self._total_lbl, row, 5)

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
        self._bar.setValue(int(pct * 10))
        self._pct_lbl.setText(f"{pct:.1f}%")
        self._speed_lbl.setText(_fmt_speed(self._speed_ema))
        self._dl_lbl.setText(_fmt_size(downloaded))
        self._total_lbl.setText(_fmt_size(total) if total else "—")

    def mark_done(self) -> None:
        self._bar.setValue(1000)
        self._pct_lbl.setText("100%")
        self._speed_lbl.setText("—")


# ── main class ────────────────────────────────────────────────────────────────

class GameDataUpdateUI:
    """
    Thread-safe PySide6 progress window for game data downloads.

    - Window opens immediately on construction.
    - Each unique filename gets its own row (added on demand).
    - Call mark_complete() when finished; window closes after 2 s.
    """

    def __init__(self) -> None:
        self._q: queue.Queue[_Msg] = queue.Queue()
        self._dialog: QDialog
        self._grid_layout: QGridLayout
        self._rows: dict[str, _FileRow] = {}
        self._row_count = 0
        ready = threading.Event()
        threading.Thread(target=self._run_ui, args=(ready,), daemon=True).start()
        ready.wait(timeout=5.0)

    # ── public API (thread-safe) ──────────────────────────────────────────

    def on_file_progress(self, name: str, downloaded: int, total: int) -> None:
        self._q.put(_MsgProgress(name, downloaded, total, time.monotonic()))

    def mark_complete(self) -> None:
        self._q.put(_MsgComplete())

    def close(self) -> None:
        self._q.put(_MsgClose())

    # ── internals ─────────────────────────────────────────────────────────

    def _run_ui(self, ready: threading.Event) -> None:
        try:
            existing = QApplication.instance()
            app: QApplication = existing if isinstance(existing, QApplication) else QApplication([])

            dialog = QDialog()
            self._dialog = dialog
            dialog.setWindowTitle("游戏数据更新")
            dialog.setWindowFlags(
                _WF.Window
                | _WF.WindowTitleHint
                | _WF.WindowMinimizeButtonHint
            )

            root_layout = QVBoxLayout(dialog)
            root_layout.setContentsMargins(12, 12, 12, 12)
            root_layout.setSpacing(6)

            title_lbl = QLabel("正在更新游戏数据，请稍候…")
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            title_lbl.setFont(font)
            root_layout.addWidget(title_lbl)

            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(_PAD)
            grid.setVerticalSpacing(8)
            grid.setColumnStretch(2, 1)  # progress bar column expands
            self._grid_layout = grid

            headers = [
                ("文件名",  _A.AlignLeft),
                ("百分比", _A.AlignRight),
                ("进度条",  _A.AlignLeft),
                ("速度",   _A.AlignRight),
                ("已下载", _A.AlignRight),
                ("总大小", _A.AlignRight),
            ]
            for col, (text, align) in enumerate(headers):
                lbl = QLabel(text)
                lbl.setAlignment(align | _A.AlignVCenter)
                lbl.setStyleSheet("color: #888;")
                grid.addWidget(lbl, 0, col)

            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setFrameShadow(QFrame.Shadow.Sunken)
            grid.addWidget(sep, 1, 0, 1, len(headers))

            self._row_count = 2  # 0=header, 1=separator, 2+=data

            root_layout.addWidget(grid_widget)
            dialog.setMinimumSize(720, 120)

            ready.set()

            timer = QTimer()
            timer.setInterval(50)
            timer.timeout.connect(self._tick)
            timer.start()

            app.exec()
        except Exception:
            logger.exception("游戏数据更新界面启动失败")
            ready.set()

    def _tick(self) -> None:
        try:
            while True:
                self._dispatch(self._q.get_nowait())
        except queue.Empty:
            pass

    def _dispatch(self, msg: _Msg) -> None:
        if isinstance(msg, _MsgProgress):
            if not self._dialog.isVisible():
                self._dialog.show()
            if msg.name not in self._rows:
                self._rows[msg.name] = _FileRow(self._grid_layout, msg.name, self._row_count)
                self._row_count += 1
                self._dialog.adjustSize()
            self._rows[msg.name].update(msg.downloaded, msg.total, msg.t)

        elif isinstance(msg, _MsgComplete):
            QTimer.singleShot(2000, self._dialog.close)

        elif isinstance(msg, _MsgClose):
            self._dialog.close()
