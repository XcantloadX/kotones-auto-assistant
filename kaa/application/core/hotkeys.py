import sys
import logging
from contextlib import suppress
from typing import Callable

keyboard = None

if sys.platform.startswith('win'):
    with suppress(ImportError):
        import keyboard  # type: ignore

from kotonebot.interop.win.message_box import message_box

logger = logging.getLogger(__name__)


class HotkeyManager:
    """全局热键管理器：Ctrl+F4 暂停/恢复，Ctrl+F3 停止任务。

    `windows`（依赖 AHK 的旧实现）截图方式自带全局热键，
    但新的 `windows_native` 截图方式不依赖 AHK，因此缺失了这一功能。
    本管理器基于 `keyboard` 库实现等价的全局热键，无条件响应。

    通知行为与原 `WindowsImpl`（基于 AHK 的 `msg_box`）保持一致：
    使用阻塞式原生消息框，而不是 toast 通知。
    """

    def __init__(
        self,
        *,
        request_stop: Callable[[], None],
        get_pause_status: Callable[[], bool | None],
        request_pause: Callable[[], None],
        request_resume: Callable[[], None],
    ) -> None:
        self._request_stop = request_stop
        self._get_pause_status = get_pause_status
        self._request_pause = request_pause
        self._request_resume = request_resume
        self._handles: list[Callable[[], None]] = []

    def start(self) -> None:
        if keyboard is None:
            logger.warning('keyboard module not available; global hotkeys (Ctrl+F4/Ctrl+F3) disabled')
            return
        if self._handles:
            return
        self._handles.append(keyboard.add_hotkey('ctrl+f4', self._on_toggle_pause))  # 暂停/恢复
        self._handles.append(keyboard.add_hotkey('ctrl+f3', self._on_stop))  # 停止
        logger.info('HotkeyManager started (Ctrl+F4 暂停/恢复, Ctrl+F3 停止)')

    def stop(self) -> None:
        if keyboard is None:
            return
        for handle in self._handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                logger.exception('Failed to remove hotkey: %s', handle)
        self._handles.clear()

    def _on_toggle_pause(self) -> None:
        try:
            if self._get_pause_status():
                message_box(None, '任务即将恢复。\n关闭此消息框后将会继续执行', '琴音小助手', buttons='ok', icon='warning')
                self._request_resume()
                logger.info('Hotkey Ctrl+F4: resume requested')
            else:
                self._request_pause()
                logger.info('Hotkey Ctrl+F4: pause requested')
                message_box(None, '任务已暂停。\n关闭此消息框后再按一次快捷键恢复执行。', '琴音小助手', buttons='ok', icon='warning')
        except Exception:
            logger.exception('Hotkey toggle pause failed')

    def _on_stop(self) -> None:
        try:
            self._request_stop()
            logger.info('Hotkey Ctrl+F3: stop requested')
            message_box(None, '任务已停止。', '琴音小助手', buttons='ok', icon='warning')
        except Exception:
            logger.exception('Hotkey stop failed')
