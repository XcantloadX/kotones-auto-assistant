import sys
from PySide6.QtCore import QObject, Property, Signal, Slot
from kaa.config import manager as config_manager
from kaa.application.ui.platform_win32 import resolve_window_style


class AppThemeController(QObject):
    windowStyleChanged = Signal()

    def _get_window_style(self) -> str:
        style = config_manager.read_shared().interface.window_style
        if sys.platform != 'win32':
            return 'solid'
        if style in ('mica', 'acrylic', 'blur', 'solid'):
            return style
        if sys.getwindowsversion().build >= 22000:
            return 'mica'
        return 'solid'

    windowStyle = Property(str, _get_window_style, notify=windowStyleChanged)

    @Slot()
    def refreshWindowStyle(self) -> None:
        self.windowStyleChanged.emit()
