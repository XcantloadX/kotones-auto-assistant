"""LogBridge — 将 Python stdout/stderr/logging/Qt 消息推送到 QML。

每个 LogBridge 实例独立捕获所有输出源（stdout、stderr、logging、Qt 消息），
通过 textWritten 信号将 (text, stream_name) 推送到 QML LogPage。
子线程安全：通过 Qt 信号机制自动切换到主线程。
"""
import sys
import logging
import warnings
import threading
import traceback
from typing import Callable, cast
from collections import deque

from PySide6.QtCore import QObject, Signal, Slot, QtMsgType, qInstallMessageHandler


_QT_MSG_TYPE_NAMES = {
    QtMsgType.QtDebugMsg: "qt.debug",
    QtMsgType.QtInfoMsg: "qt.info",
    QtMsgType.QtWarningMsg: "qt.warning",
    QtMsgType.QtCriticalMsg: "qt.critical",
    QtMsgType.QtFatalMsg: "qt.fatal",
}


class StreamRedirector:
    def __init__(self, bridge: "LogBridge", stream_name: str, original_stream=None) -> None:
        self.bridge = bridge
        self.stream_name = stream_name
        self.original_stream = original_stream

    def write(self, text: str) -> None:
        if not text:
            return

        if self.original_stream is not None:
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except Exception:
                pass

        self.bridge.write_text(text, self.stream_name)

    def flush(self) -> None:
        if self.original_stream is not None:
            try:
                self.original_stream.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        return False

    @property
    def encoding(self) -> str:
        return "utf-8"


class QtLogHandler(logging.Handler):
    def __init__(self, bridge: "LogBridge") -> None:
        super().__init__()
        self.bridge = bridge

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.bridge.write_text(msg + "\n", "logging")
        except Exception:
            self.handleError(record)


class LogBridge(QObject):
    """向 QML 推送日志行。

    每个实例独立捕获 stdout、stderr、Python logging、Qt 消息和异常 traceback。
    使用缓冲区保存早期日志（LogPage 尚未创建时），QML 可通过 bufferedEntries() 获取。
    """

    textWritten = Signal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._installed = False

        self._original_stdout = None
        self._original_stderr = None
        self._original_excepthook = None
        self._original_threading_excepthook = None

        self._handler: QtLogHandler | None = None

        self._qt_message_handler = None
        self._previous_qt_message_handler = None
        self._qt_handler_state = threading.local()

        self._buffer = deque(maxlen=5000)
        self._closing = False

    def write_text(self, text: str, stream_name: str) -> None:
        if not text:
            return

        self._buffer.append((text, stream_name))
        if not self._closing:
            try:
                self.textWritten.emit(text, stream_name)
            except RuntimeError:
                pass

    @Slot(result="QVariantList")
    def bufferedEntries(self):
        return [
            {"text": text, "stream": stream}
            for text, stream in self._buffer
        ]

    def install(self) -> None:
        if self._installed:
            return
        self._installed = True

        # stdout/stderr
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

        original_stdout = sys.__stdout__ or self._original_stdout
        original_stderr = sys.__stderr__ or self._original_stderr

        sys.stdout = StreamRedirector(self, "stdout", original_stdout)
        sys.stderr = StreamRedirector(self, "stderr", original_stderr)

        # logging
        handler = QtLogHandler(self)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "%H:%M:%S",
        ))

        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.DEBUG)
        self._handler = handler

        # warnings
        warnings.simplefilter("default")
        logging.captureWarnings(True)

        # exception tracebacks
        self._original_excepthook = sys.excepthook

        def excepthook(exc_type, exc_value, exc_tb):
            text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            logging.getLogger("uncaught").critical(text)

        sys.excepthook = excepthook

        if hasattr(threading, "excepthook"):
            self._original_threading_excepthook = threading.excepthook

            def threading_excepthook(args):
                text = "".join(traceback.format_exception(
                    args.exc_type,
                    args.exc_value,
                    args.exc_traceback,
                ))
                logging.getLogger("threading").critical(text)

            threading.excepthook = threading_excepthook

        # Qt / QML
        self._qt_message_handler = self._handle_qt_message
        self._previous_qt_message_handler: Callable | None = cast(Callable, qInstallMessageHandler(
            self._qt_message_handler
        ))

    def _handle_qt_message(self, msg_type, context, message: str) -> None:
        if getattr(self._qt_handler_state, "active", False):
            return

        self._qt_handler_state.active = True
        try:
            stream_name = _QT_MSG_TYPE_NAMES.get(msg_type, "qt")

            text = message.rstrip("\n")

            file = getattr(context, "file", None)
            line = getattr(context, "line", 0)

            if file and line and file not in text:
                text = f"{text} ({file}:{line})"

            text += "\n"

            self.write_text(text, stream_name)

            if self._previous_qt_message_handler is not None:
                try:
                    self._previous_qt_message_handler(msg_type, context, message)
                except Exception:
                    pass
            else:
                try:
                    original = self._original_stderr or sys.__stderr__
                    if original is not None:
                        original.write(text)
                        original.flush()
                except Exception:
                    pass

        except Exception:
            pass
        finally:
            self._qt_handler_state.active = False

    def close(self) -> None:
        if not self._installed:
            return
        self._closing = True
        self._installed = False

        # 恢复 Qt message handler
        if self._qt_message_handler is not None:
            try:
                qInstallMessageHandler(self._previous_qt_message_handler)
            except Exception:
                pass

            self._qt_message_handler = None
            self._previous_qt_message_handler = None

        if self._original_stdout is not None:
            sys.stdout = self._original_stdout

        if self._original_stderr is not None:
            sys.stderr = self._original_stderr

        if self._handler is not None:
            root_logger = logging.getLogger()
            try:
                root_logger.removeHandler(self._handler)
            except Exception:
                pass
            self._handler = None

        logging.captureWarnings(False)

        if self._original_excepthook is not None:
            sys.excepthook = self._original_excepthook
            self._original_excepthook = None

        if self._original_threading_excepthook is not None:
            threading.excepthook = self._original_threading_excepthook
            self._original_threading_excepthook = None
