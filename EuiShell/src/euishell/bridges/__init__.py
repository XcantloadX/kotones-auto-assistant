"""Shell 桥接层：Splash、日志、进度、通知、错误对话框的 Python↔QML 桥。"""

from euishell.bridges.error_dialog import ErrorDialogBridge
from euishell.bridges.log_bridge import LogBridge
from euishell.bridges.notice import NoticeBackend
from euishell.bridges.progress import FileProgressItem, ProgressAggregator, ProgressBridge
from euishell.bridges.splash import SplashBridge

__all__ = [
    'ErrorDialogBridge',
    'FileProgressItem',
    'LogBridge',
    'NoticeBackend',
    'ProgressAggregator',
    'ProgressBridge',
    'SplashBridge',
]
