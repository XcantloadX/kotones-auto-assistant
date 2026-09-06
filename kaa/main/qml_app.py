"""QML 入口模块：以 EuiShell Shell + KaaPlugin 启动 KAA 桌面 UI。"""
import logging
import sys

logger = logging.getLogger(__name__)


def main() -> None:
    """启动 QML 主窗口（多 Profile Tab 架构）。"""
    from euishell.app import ShellApp

    from kaa.application.ui.plugin import KaaPlugin

    sys.exit(ShellApp(KaaPlugin()).run())
