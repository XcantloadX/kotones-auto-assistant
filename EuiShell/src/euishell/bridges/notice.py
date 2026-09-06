"""NoticeBackend — Toast 通知桥接。

全局唯一实例，注册为 QML 上下文属性 ``Notice``；
QML 侧由 NoticeHost 渲染，Python / QML 任意侧均可 ``Notice.show(kind, text)``。
"""

from PySide6.QtCore import QObject, Signal, Slot


class NoticeBackend(QObject):
    """Toast 通知桥接。"""

    showNotification = Signal(str, str)

    @Slot(str, str)
    def show(self, kind: str, text: str) -> None:
        """弹出一条 Toast 通知。

        :param kind: 通知类型（``info`` / ``success`` / ``warning`` / ``error``）
        :param text: 通知文本
        """
        self.showNotification.emit(kind, text)
