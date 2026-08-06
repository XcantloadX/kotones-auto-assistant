"""应用退出请求工具：提供主线程安全的应用退出入口。"""
import sys
import _thread
import logging
import threading

logger = logging.getLogger(__name__)


def request_exit(exit_code: int = 0) -> None:
    """请求退出应用，主线程安全。

    - 主线程（CLI 同步任务）：直接 ``sys.exit``，由调用方正常收尾。
    - 非主线程且存在 QApplication（GUI 模式）：通过 Qt 队列连接在主线程调用
      ``QCoreApplication.quit()``，让 ``app.exec()`` 正常返回并走清理流程，
      避免向主线程注入 ``KeyboardInterrupt`` 被 Qt/shiboken 吞掉。当前工作线程
      随后自然结束，不再抛 ``SystemExit``，防止其泄漏到 ``threading.excepthook``
      造成误报。
    - 非主线程且无 QApplication：回退为 ``_thread.interrupt_main()``。
    """
    if threading.current_thread() is threading.main_thread():
        logger.info("Requesting exit from main thread")
        sys.exit(exit_code)
        return

    from PySide6.QtCore import QMetaObject, Qt
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        logger.info("Requesting Qt application exit from non-main thread")
        QMetaObject.invokeMethod(
            app,
            "quit",
            Qt.ConnectionType.QueuedConnection,
        )
        return

    # 无 QApplication 的非主线程场景（罕见）：回退为在后台线程触发中断。
    logger.info("Requesting exit from non-main thread without QApplication")
    _thread.interrupt_main()
    sys.exit(exit_code)