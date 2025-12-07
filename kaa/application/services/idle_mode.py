import sys
import time
import logging
import threading
from contextlib import suppress
from typing import Callable, Optional

with suppress(ImportError):
    keyboard = None
    win32api = None
    win32gui = None
    win32con = None
    import keyboard # type: ignore
    import win32api # type: ignore
    import win32gui # type: ignore
    import win32con # type: ignore

from kotonebot.backend.context.context import vars
from kaa.config.schema import IdleModeConfig

logger = logging.getLogger(__name__)

def _get_system_idle_seconds_windows() -> int:
    if win32api is None:
        return 0
    try:
        last_input_tick = win32api.GetLastInputInfo()
        tick_count = win32api.GetTickCount()
        elapsed_ms = tick_count - last_input_tick
        return max(0, int(elapsed_ms / 1000))
    except Exception:
        logger.exception('win32api.GetLastInputInfo failed')
        return 0


def get_system_idle_seconds() -> int:
    if sys.platform.startswith('win'):
        try:
            return _get_system_idle_seconds_windows()
        except Exception:
            logger.exception('GetLastInputInfo failed')
            return 0
    return 0


class IdleModeManager:
    def __init__(
        self,
        *,
        get_is_running: Callable[[], bool],
        get_is_paused: Callable[[], bool],
        get_config: Callable[[], IdleModeConfig],
    ) -> None:
        self._get_is_running = get_is_running
        self._get_is_paused = get_is_paused
        self._get_config = get_config
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._keyboard_hook = None
        self._last_key_ts: float = 0.0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name='IdleModeThread', daemon=True)
        self._thread.start()
        self._install_keyboard_hook()
        logger.info('IdleModeManager started')

    def stop(self) -> None:
        self._remove_keyboard_hook()
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=2.0)
        logger.info('IdleModeManager stopped')

    def notify_on_start(self) -> None:
        # 运行态切换时可根据需要做重置
        self._last_key_ts = 0.0

    def notify_on_stop(self) -> None:
        self._last_key_ts = 0.0

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            conf = self._get_config()
            if not conf.enabled:
                time.sleep(0.8)
                continue
            try:
                if self._get_is_paused():
                    idle_sec = get_system_idle_seconds()
                    if idle_sec >= max(0, int(conf.idle_seconds)):
                        logger.info('System idle for %ss while paused. Requesting resume...', idle_sec)
                        try:
                            vars.flow.request_resume()
                        except Exception:
                            logger.exception('request_resume failed')
                time.sleep(0.8)
            except Exception:
                logger.exception('IdleMode loop error')
                time.sleep(1.0)

    def _install_keyboard_hook(self) -> None:
        if keyboard is None:
            logger.warning('keyboard module not available; key-to-pause disabled')
            return
        if self._keyboard_hook is not None:
            return

        def _on_key_event(_: object) -> None:
            conf = self._get_config()
            if not conf.enabled:
                return
            now = time.time()
            if (now - self._last_key_ts) < 0.3:
                return
            self._last_key_ts = now
            try:
                if self._get_is_running() and not self._get_is_paused():
                    logger.info('Any key pressed -> pause requested')
                    vars.flow.request_pause()
                    if conf.minimize_on_pause:
                        self._minimize_game_window()
            except Exception:
                logger.exception('key handler failed')

        try:
            self._keyboard_hook = keyboard.on_press(_on_key_event, suppress=False)
        except Exception:
            logger.warning('Failed to install keyboard hook; degraded behavior')
            self._keyboard_hook = None

    def _remove_keyboard_hook(self) -> None:
        if keyboard is None:
            return
        if self._keyboard_hook is None:
            return
        try:
            keyboard.unhook(self._keyboard_hook)
        except Exception:
            logger.exception('Failed to remove keyboard hook')
        finally:
            self._keyboard_hook = None

    def _minimize_game_window(self) -> None:
        # Send the window to background (bottom of Z-order) via pywin32
        if not sys.platform.startswith('win'):
            return
        if win32gui is None or win32con is None:
            logger.warning('pywin32 (win32gui/win32con) not available; skip backgrounding')
            return
        try:
            hwnd = win32gui.FindWindow(None, 'gakumas')  # type: ignore
            if hwnd:
                flags = (
                    win32con.SWP_NOMOVE
                    | win32con.SWP_NOSIZE
                    | win32con.SWP_NOACTIVATE
                    | win32con.SWP_NOOWNERZORDER
                )
                win32gui.SetWindowPos(hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0, flags)
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
                except Exception:
                    pass
                logger.info('Sent game window to background (HWND=%s)', hwnd)
            else:
                logger.warning('Game window not found; cannot send to background')
        except Exception:
            logger.warning('Failed to send game window to background', exc_info=True) 