"""ShellApp 冒烟测试：Dummy 插件驱动完整 QML 加载与启动线程。"""
from PySide6.QtCore import QTimer

from euishell.app import ShellApp
from euishell.bridges.error_dialog import get_bridge

from .conftest import DummyPlugin


def test_shell_app_boots_and_reaches_ready(dummy_plugin: DummyPlugin) -> None:
    """main.qml 加载成功、启动线程把 splash 置为 ready、事件循环正常退出。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    shell = ShellApp(dummy_plugin, argv=[])

    # 轮询 splash.ready，就绪后退出事件循环
    poll = QTimer()
    poll.setInterval(20)
    poll.timeout.connect(lambda: (
        poll.stop(),
        QTimer.singleShot(0, app.quit),
    ) if (dummy_plugin.last_splash is not None and dummy_plugin.last_splash.ready) else None)
    poll.start()

    exit_code = shell.exec_with(app)

    assert exit_code == 0
    assert dummy_plugin.startup_called
    assert dummy_plugin.post_ready_called
    assert dummy_plugin.last_splash is not None and dummy_plugin.last_splash.ready
    assert get_bridge() is None
