"""EuiShellApp 声明式扩展点行为测试：总览显隐与 per-tab slot 生命周期。"""
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from euishell.app import ShellApp
from euishell.plugin import StartupContext

from .conftest import DummyPlugin

_OVERVIEW_BODY = (
    'import QtQuick\n'
    'import EuiShell\n'
    'EuiShellApp {\n'
    '    overviewContent: Component {\n'
    '        Item { objectName: "overviewProbe" }\n'
    '    }\n'
    '}\n'
)

_NO_OVERVIEW_BODY = (
    'import QtQuick\n'
    'import EuiShell\n'
    'EuiShellApp {\n'
    '}\n'
)

_PER_TAB_BODY = (
    'import QtQuick\n'
    'import EuiShell\n'
    'EuiShellApp {\n'
    '    controlNotices: Component {\n'
    '        Item {\n'
    '            objectName: "perTabProbe"\n'
    '            Component.onCompleted: slotProbe.hit()\n'
    '            Component.onDestruction: slotProbe.markDestroyed()\n'
    '        }\n'
    '    }\n'
    '}\n'
)


class _SlotProbe(QObject):
    """记录 per-tab slot 组件实例化 / 销毁次数的探针。"""

    def __init__(self) -> None:
        super().__init__()
        self.hit_count = 0
        self.destroyed_count = 0

    @Slot()
    def hit(self) -> None:
        self.hit_count += 1

    @Slot()
    def markDestroyed(self) -> None:
        self.destroyed_count += 1


class ProbePlugin(DummyPlugin):
    """以 slotProbe 全局控制器向 QML 提供探针的测试插件。"""

    def __init__(self, tmp_dir: Path, qml_body: str) -> None:
        super().__init__(tmp_dir)
        self.probe = _SlotProbe()
        self.startup_ctx: StartupContext | None = None
        self.index_qml.write_text(qml_body, encoding='utf-8')

    def global_controllers(self, ctx: StartupContext) -> dict[str, QObject]:
        self.startup_ctx = ctx
        return {'slotProbe': self.probe}


def _active_window() -> QQuickWindow:
    """返回当前可见的 Shell 窗口。"""
    for window in QApplication.topLevelWindows():
        if isinstance(window, QQuickWindow) and window.isVisible():
            return window
    raise AssertionError('未找到可见的 QQuickWindow')


def _poll_shell(
    app: QApplication,
    plugin: ProbePlugin,
    on_ready: 'callable',  # type: ignore[valid-type]
) -> int:
    """驱动事件循环：splash 就绪后每 tick 调用 on_ready，返回 True 时退出。"""
    poll = QTimer()
    poll.setInterval(20)

    def _tick() -> None:
        splash = plugin.last_splash
        if splash is None or not splash.ready:
            return
        if on_ready():
            poll.stop()
            QTimer.singleShot(0, app.quit)

    poll.timeout.connect(_tick)
    poll.start()
    return ShellApp(plugin, argv=[]).exec_with(app)


def test_overview_tab_visible_with_content(dummy_plugin: DummyPlugin, tmp_path: Path) -> None:
    """overviewContent 非 null：总览 Tab 可见且内容被实例化。"""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    plugin = ProbePlugin(tmp_path, _OVERVIEW_BODY)
    plugin.last_splash = None

    def _check() -> bool:
        window = _active_window()
        tab = window.findChild(QObject, 'overviewTab')
        assert tab is not None
        if not tab.property('visible'):
            return False
        assert window.findChild(QObject, 'overviewProbe') is not None
        return True

    exit_code = _poll_shell(app, plugin, _check)
    assert exit_code == 0


def test_overview_tab_hidden_without_content(dummy_plugin: DummyPlugin, tmp_path: Path) -> None:
    """overviewContent 为 null：总览 Tab 整体隐藏，内容不实例化。"""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    plugin = ProbePlugin(tmp_path, _NO_OVERVIEW_BODY)

    def _check() -> bool:
        window = _active_window()
        tab = window.findChild(QObject, 'overviewTab')
        assert tab is not None
        if tab.property('visible'):
            return False
        assert window.findChild(QObject, 'overviewProbe') is None
        return True

    exit_code = _poll_shell(app, plugin, _check)
    assert exit_code == 0


def test_per_tab_slot_instantiated_and_destroyed(dummy_plugin: DummyPlugin, tmp_path: Path) -> None:
    """打开 Tab 后 per-tab slot 实例化（每 Tab 一份），关闭 Tab 后销毁。"""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    plugin = ProbePlugin(tmp_path, _PER_TAB_BODY)
    stage = {'step': 0}

    def _check() -> bool:
        assert plugin.startup_ctx is not None
        probe = plugin.probe
        tab_manager = plugin.startup_ctx.tab_manager
        step = stage['step']
        if step == 0:
            tab_manager.openTab('p1')
            stage['step'] = 1
        elif step == 1:
            if probe.hit_count < 1:
                return False
            assert probe.destroyed_count == 0
            tab_manager.closeTab(0)
            stage['step'] = 2
        elif step == 2:
            return probe.destroyed_count >= 1
        return False

    exit_code = _poll_shell(app, plugin, _check)
    assert exit_code == 0
    assert plugin.probe.hit_count == 1
    assert plugin.probe.destroyed_count == 1
