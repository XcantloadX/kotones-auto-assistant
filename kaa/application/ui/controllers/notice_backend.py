"""NoticeBackend — Toast 通知桥接。

对应 IAA 的 Notice.qml 单例。全局只有一个实例，注册为 QML 上下文属性 `Notice`。
任何 QML 组件均可直接调用 `Notice.show(kind, text)` 弹出通知。
"""

from PySide6.QtCore import QObject, Signal, Slot


class NoticeBackend(QObject):
    showNotification = Signal(str, str)  # kind, text

    @Slot(str, str)
    def show(self, kind: str, text: str) -> None:
        self.showNotification.emit(kind, text)
