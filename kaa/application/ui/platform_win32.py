"""Windows 专用窗口合成与无边框窗口辅助函数。"""
import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Property, Signal
from PySide6.QtQuick import QQuickWindow

# ── DWM 背景特效 ──────────────────────────────────────────────────────────────

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38

# 1 = 无, 2 = MainWindow (Mica), 3 = TransientWindow (类 Acrylic), 4 = TabbedWindow
DWM_SYSTEMBACKDROP_MAINWINDOW = 2

WNDCA_ACCENT_POLICY = 19

ACCENT_DISABLED = 0
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attrib", ctypes.c_uint),
        ("pvData", ctypes.c_void_p),
        ("cbData", ctypes.c_size_t),
    ]


def is_windows_11() -> bool:
    return sys.getwindowsversion().build >= 22000


def enable_mica(hwnd: int) -> int:
    dwmapi = ctypes.windll.dwmapi
    value = ctypes.c_int(DWM_SYSTEMBACKDROP_MAINWINDOW)
    return dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd),
        ctypes.c_uint(DWMWA_SYSTEMBACKDROP_TYPE),
        ctypes.byref(value),
        ctypes.sizeof(value)
    )


def _set_dwm_frame(hwnd: int, left: int, right: int, top: int, bottom: int) -> int:
    margins = _MARGINS(left, right, top, bottom)
    return ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))


def enable_blur(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    set_window_composition = user32.SetWindowCompositionAttribute
    set_window_composition.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
    set_window_composition.restype = ctypes.c_bool

    _set_dwm_frame(hwnd, -1, -1, -1, -1)
    accent = ACCENT_POLICY(ACCENT_ENABLE_BLURBEHIND, 0, 0, 0)
    data = WINDOWCOMPOSITIONATTRIBDATA(WNDCA_ACCENT_POLICY, ctypes.addressof(accent), ctypes.sizeof(accent))
    return 0 if set_window_composition(wintypes.HWND(hwnd), ctypes.byref(data)) else -1


def enable_acrylic(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    set_window_composition = user32.SetWindowCompositionAttribute
    set_window_composition.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
    set_window_composition.restype = ctypes.c_bool

    _set_dwm_frame(hwnd, -1, -1, -1, -1)
    accent = ACCENT_POLICY(ACCENT_ENABLE_ACRYLICBLURBEHIND, 0, 0, 0)
    data = WINDOWCOMPOSITIONATTRIBDATA(WNDCA_ACCENT_POLICY, ctypes.addressof(accent), ctypes.sizeof(accent))
    return 0 if set_window_composition(wintypes.HWND(hwnd), ctypes.byref(data)) else -1


def disable_blur(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    set_window_composition = user32.SetWindowCompositionAttribute
    set_window_composition.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
    set_window_composition.restype = ctypes.c_bool

    accent = ACCENT_POLICY(ACCENT_DISABLED, 0, 0, 0)
    data = WINDOWCOMPOSITIONATTRIBDATA(WNDCA_ACCENT_POLICY, ctypes.addressof(accent), ctypes.sizeof(accent))
    ret = 0 if set_window_composition(wintypes.HWND(hwnd), ctypes.byref(data)) else -1

    _set_dwm_frame(hwnd, 0, 0, 0, 1)
    return ret


def resolve_window_style(style: str) -> str:
    if style in ('mica', 'acrylic', 'blur', 'solid'):
        return style
    if is_windows_11():
        return 'mica'
    return 'solid'


def apply_window_style(hwnd: int, style: str) -> None:
    resolved = resolve_window_style(style)
    if resolved == 'mica':
        enable_mica(hwnd)
    elif resolved == 'acrylic':
        enable_acrylic(hwnd)
    elif resolved == 'blur':
        enable_blur(hwnd)
    elif resolved == 'solid':
        disable_blur(hwnd)


# ── 无边框窗口 + 贴靠布局支持 ────────────────────────────────────────────────

WM_NCHITTEST     = 0x0084
WM_NCCALCSIZE    = 0x0083
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONUP   = 0x00A2
WM_NCMOUSEMOVE   = 0x00A0
WM_NCMOUSELEAVE  = 0x02A2
WM_SYSCOMMAND    = 0x0112

SC_RESTORE  = 0xF120
SC_MAXIMIZE = 0xF030

# WM_NCHITTEST 返回值
HTCLIENT      = 1
HTCAPTION     = 2
HTMINBUTTON   = 8
HTMAXBUTTON   = 9
HTLEFT        = 10
HTRIGHT       = 11
HTTOP         = 12
HTTOPLEFT     = 13
HTTOPRIGHT    = 14
HTBOTTOM      = 15
HTBOTTOMLEFT  = 16
HTBOTTOMRIGHT = 17
HTCLOSE       = 20

_GWL_STYLE      = -16
_WS_CAPTION     = 0x00C00000
_WS_THICKFRAME  = 0x00040000
_WS_MAXIMIZEBOX = 0x00010000
_WS_MINIMIZEBOX = 0x00020000
_WS_SYSMENU     = 0x00080000

# 与 TitleBar.qml 匹配的标题栏几何参数
_TITLE_BAR_H = 42   # TitleBar 高度（8px 拖拽条 + 34px tab 行）
_BTN_W       = 46   # 窗口控件按钮宽度（close/max/min）
_RESIZE_EDGE = 4    # 调整大小命中区域宽度


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hWnd",    wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam",  wintypes.WPARAM),
        ("lParam",  wintypes.LPARAM),
        ("time",    wintypes.DWORD),
        ("pt",      wintypes.POINT),
    ]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left",   ctypes.c_long),
        ("top",    ctypes.c_long),
        ("right",  ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [
        ("rgrc", _RECT * 3),
        ("lppos", ctypes.c_void_p),
    ]


class _MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth",    ctypes.c_int),
        ("cxRightWidth",   ctypes.c_int),
        ("cyTopHeight",    ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


class TabBarHitTestBridge(QObject):
    """QML 通过此对象将 tab 区域右边界（逻辑像素）实时同步给 Win32 hit-test。"""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tab_interactive_end: int = 0

    @Property(int)
    def tabInteractiveEnd(self) -> int:
        return self._tab_interactive_end

    @tabInteractiveEnd.setter
    def tabInteractiveEnd(self, value: int) -> None:
        self._tab_interactive_end = value


class MaxHoverBridge(QObject):
    """将最大化按钮的 WM_NCMOUSEMOVE/WM_NCMOUSELEAVE 转发给 QML。"""
    hoveredChanged = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._hovered = False

    def set_hovered(self, value: bool) -> None:
        if self._hovered != value:
            self._hovered = value
            self.hoveredChanged.emit(value)


class WindowEventFilter(QAbstractNativeEventFilter):
    """
    为无边框 Qt 窗口处理 WM_NCHITTEST，使得：
      • 四边调整大小手柄正常工作。
      • 最大化按钮返回 HTMAXBUTTON，Windows 11 可显示贴靠布局弹出窗口，
        并由系统驱动最大化/还原。
      • 标题栏拖拽区返回 HTCAPTION，支持原生拖动及双击切换最大化。
      • 最小化和关闭按钮区返回 HTCLIENT，由 QML 处理悬停高亮和点击。
      • HTMAXBUTTON 上的 WM_NCMOUSEMOVE/WM_NCMOUSELEAVE 转发给
        MaxHoverBridge，供 QML 渲染悬停高亮。
    """

    def __init__(self, window: QQuickWindow, max_hover_bridge: MaxHoverBridge, tab_bar_bridge: TabBarHitTestBridge) -> None:
        super().__init__()
        self._hwnd = int(window.winId())
        self.maxHoverBridge = max_hover_bridge
        self._tab_bar_bridge = tab_bar_bridge
        self._max_down_zoomed: bool | None = None

    def nativeEventFilter(self, eventType: bytes, message: int) -> tuple[bool, int]:
        if eventType != b"windows_generic_MSG":
            return False, 0
        msg = ctypes.cast(int(message), ctypes.POINTER(_MSG)).contents
        if msg.hWnd != self._hwnd:
            return False, 0
        if msg.message == WM_NCCALCSIZE and msg.wParam:
            if ctypes.windll.user32.IsZoomed(msg.hWnd):
                p = ctypes.cast(msg.lParam, ctypes.POINTER(_NCCALCSIZE_PARAMS)).contents
                border = ctypes.windll.user32.GetSystemMetrics(33)
                padded = ctypes.windll.user32.GetSystemMetrics(92)
                p.rgrc[0].top += border + padded
            return True, 0
        if msg.message == WM_NCHITTEST:
            return self._hit_test(msg)
        if msg.message == WM_NCMOUSEMOVE:
            self.maxHoverBridge.set_hovered(msg.wParam == HTMAXBUTTON)
            return False, 0
        if msg.message == WM_NCMOUSELEAVE:
            self.maxHoverBridge.set_hovered(False)
            return False, 0
        if msg.message == WM_NCLBUTTONDOWN and msg.wParam == HTMAXBUTTON:
            self._max_down_zoomed = ctypes.windll.user32.IsZoomed(msg.hWnd)
            return True, 0
        if msg.message == WM_NCLBUTTONUP and msg.wParam == HTMAXBUTTON:
            was_zoomed = self._max_down_zoomed
            self._max_down_zoomed = None
            if was_zoomed is not None and ctypes.windll.user32.IsZoomed(msg.hWnd) == was_zoomed:
                cmd = SC_RESTORE if was_zoomed else SC_MAXIMIZE
                ctypes.windll.user32.SendMessageW(msg.hWnd, WM_SYSCOMMAND, cmd, 0)
                return True, 0
            return False, 0
        return False, 0

    def _hit_test(self, msg: _MSG) -> tuple[bool, int]:
        sx = ctypes.c_short(msg.lParam & 0xFFFF).value
        sy = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value

        wr = _RECT()
        ctypes.windll.user32.GetWindowRect(msg.hWnd, ctypes.byref(wr))

        wx = sx - wr.left
        wy = sy - wr.top
        ww = wr.right  - wr.left
        wh = wr.bottom - wr.top

        dpi    = ctypes.windll.user32.GetDpiForWindow(msg.hWnd)
        scale  = dpi / 96.0
        tb_h   = round(_TITLE_BAR_H * scale)
        border = round(_RESIZE_EDGE * scale)
        is_max = bool(ctypes.windll.user32.IsZoomed(msg.hWnd))

        if not is_max:
            top_e    = wy < border
            bottom_e = wy >= wh - border
            left_e   = wx < border
            right_e  = wx >= ww - border
            if top_e    and left_e:  return True, HTTOPLEFT
            if top_e    and right_e: return True, HTTOPRIGHT
            if bottom_e and left_e:  return True, HTBOTTOMLEFT
            if bottom_e and right_e: return True, HTBOTTOMRIGHT
            if top_e:    return True, HTTOP
            if bottom_e: return True, HTBOTTOM
            if left_e:   return True, HTLEFT
            if right_e:  return True, HTRIGHT

        if wy < tb_h:
            close_w = round(_BTN_W * scale)
            max_w   = round(_BTN_W * scale)
            min_w   = round(_BTN_W * scale)

            if wx >= ww - close_w:
                return False, 0
            if wx >= ww - close_w - max_w:
                return True, HTMAXBUTTON
            if wx >= ww - close_w - max_w - min_w:
                return False, 0

            tab_end = round(self._tab_bar_bridge.tabInteractiveEnd * scale)
            if wx < tab_end:
                return False, 0

            return True, HTCAPTION

        return False, 0


def setup_frameless_window(hwnd: int) -> None:
    user32 = ctypes.windll.user32
    style  = user32.GetWindowLongW(hwnd, _GWL_STYLE)
    style |= _WS_CAPTION | _WS_THICKFRAME | _WS_MAXIMIZEBOX | _WS_MINIMIZEBOX | _WS_SYSMENU
    user32.SetWindowLongW(hwnd, _GWL_STYLE, style)

    margins = _MARGINS(-1, -1, -1, -1)
    ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

    user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)
