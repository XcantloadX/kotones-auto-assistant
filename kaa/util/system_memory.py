"""启动期系统可用内存检测。"""

import logging
import sys

logger = logging.getLogger(__name__)

LOW_MEMORY_THRESHOLD_BYTES = 1024 ** 3  # 1GB
LOW_MEMORY_MESSAGE = (
    "当前系统可用内存低于 1GB，小助手可能无法正常运行。\n"
    "建议在游戏运行的情况下，至少预留 1.5GB 可用内存！"
)
LOW_MEMORY_CAPTION = "琴音小助手"


def get_available_bytes() -> int:
    """返回系统当前可用物理内存（字节）。

    :raises OSError: 非 Windows 平台或 Win32 API 调用失败时抛出。
    """
    if sys.platform != "win32":
        raise OSError(f"Unsupported platform for native memory check: {sys.platform}")
    import ctypes

    class _MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(_MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return int(status.ullAvailPhys)


def _show_native_warning(message: str = LOW_MEMORY_MESSAGE) -> None:
    """Windows 原生警告弹窗（MB_OK | MB_ICONWARNING），失败时抛异常由调用方记录。"""
    import ctypes

    mb_ok = 0x0
    mb_iconwarning = 0x30
    ctypes.windll.user32.MessageBoxW(None, message, LOW_MEMORY_CAPTION, mb_ok | mb_iconwarning)


def warn_if_low_memory(threshold_bytes: int = LOW_MEMORY_THRESHOLD_BYTES) -> bool:
    """可用内存低于阈值时原生弹窗提示，返回是否已弹窗。

    非 Windows 平台直接返回 ``False``（只在日志中记录原因供排查）。
    查询失败时记录日志并返回 ``False``，不阻断启动流程。
    """
    if sys.platform != "win32":
        return False
    try:
        available = get_available_bytes()
    except Exception:
        logger.debug("Failed to query available system memory.", exc_info=True)
        return False
    if available >= threshold_bytes:
        return False
    logger.warning(
        "Low system memory detected: available=%.1fGB < threshold=%.1fGB.",
        available / (1024 ** 3),
        threshold_bytes / (1024 ** 3),
    )
    try:
        _show_native_warning()
    except Exception:
        logger.debug("Failed to show low-memory native dialog.", exc_info=True)
    return True
