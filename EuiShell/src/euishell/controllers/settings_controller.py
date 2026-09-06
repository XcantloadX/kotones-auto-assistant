"""SettingsControllerBase — 设置控制器基类（QML 契约）。"""
from abc import abstractmethod

from PySide6.QtCore import QObject, Signal, Slot


class SettingsControllerBase(QObject):
    """Tab 内设置控制器的抽象基类。

    QML 契约：
      - 信号: configChanged / dirtyChanged(bool) / operationSucceeded(str) / operationFailed(str)
      - Slot: isDirty() / save() / discard() / validateJson()

    下游子类实现四个抽象 Slot；控制页等仅依赖该契约。
    """

    configChanged = Signal()
    dirtyChanged = Signal(bool)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    @Slot(result=bool)
    @abstractmethod
    def isDirty(self) -> bool:
        """返回草稿是否有未保存更改。"""

    @Slot(result=bool)
    @abstractmethod
    def save(self) -> bool:
        """提交草稿；返回是否成功。"""

    @Slot(result=bool)
    @abstractmethod
    def discard(self) -> bool:
        """丢弃未保存更改；返回是否有更改被丢弃。"""

    @Slot(result=str)
    @abstractmethod
    def validateJson(self) -> str:
        """校验当前草稿，返回 [{severity, field, message}] JSON。"""
