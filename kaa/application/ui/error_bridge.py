from typing import Callable
from PySide6.QtCore import QObject, Signal, Slot

_instance: "ErrorDialogBridge | None" = None


def get_bridge() -> "ErrorDialogBridge | None":
    return _instance


def set_bridge(bridge: "ErrorDialogBridge | None") -> None:
    global _instance
    _instance = bridge


class ErrorDialogBridge(QObject):
    """Python↔QML 错误对话框通信桥。

    task 线程调用 show()（fire-and-forget），QML 显示对话框后
    调用 onButtonClicked()，再由此触发 invoke 回调。
    """

    showDialog = Signal(str, str, list)  # main_instruction, content, buttons

    def __init__(self) -> None:
        super().__init__()
        self._pending_invoke: Callable[[int], None] | None = None

    def show(
        self,
        message: str,
        buttons: list[tuple[int, str]],
        on_click: Callable[[int], None],
    ) -> None:
        """从 task 线程调用，非阻塞地弹出错误对话框。

        :param message: 错误正文。
        :param buttons: 按钮列表，每项为 (id, 显示文本)。
        :param on_click: 用户点击后以 button_id 为参数调用的回调。
        """
        self._pending_invoke = on_click
        btn_list = [{"id": bid, "text": text} for bid, text in buttons]
        self.showDialog.emit("任务执行失败", message, btn_list)

    @Slot(int)
    def onButtonClicked(self, button_id: int) -> None:
        """由 QML 在用户点击按钮时调用。"""
        if self._pending_invoke is not None:
            self._pending_invoke(button_id)
            self._pending_invoke = None
