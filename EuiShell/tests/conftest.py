"""EuiShell 测试公共设施：Dummy 插件 / 会话与 QML 测试工具。"""
import copy
import os
from pathlib import Path

# 离屏渲染必须在导入 PySide6 前设置
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'FluentWinUI3')

import pytest
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine

from euishell import paths
from euishell.controllers.preferences_controller import PreferencesControllerBase
from euishell.exceptions import ProfileError, TaskControlError
from euishell.plugin import EuiShellPlugin, StartupContext
from euishell.session import (
    AppearanceSettingsStore,
    OpenTabsState,
    ProfileProvider,
    ShellSession,
    TabApi,
    TabPersistence,
    TaskBulkAction,
    TaskControl,
    TaskToggle,
    TaskTogglesSource,
)

# 1x1 红色 PNG
_PNG_1PX = bytes.fromhex(
    '89504e470d0a1a0a0000000d49484452000000010000000108020000009077'
    '53de0000000c4944415408d763f8cfc00000030101'
    '00f62c11fc0000000049454e44ae426082'
)


class DummyTaskControl(TaskControl):
    """内存任务控制实现。"""

    def __init__(self) -> None:
        self._running = False
        self._paused = False
        self.task_list = ['任务A', '任务B']

    @property
    def running(self) -> bool:
        return self._running

    @property
    def stopping(self) -> bool:
        return False

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def current_task_name(self) -> str:
        return self.task_list[0] if self._running else ''

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def toggle_pause(self) -> None:
        self._paused = not self._paused

    def run_single(self, name: str) -> None:
        if name not in self.task_list:
            raise TaskControlError(f'未知任务: {name}')
        self._running = True

    def task_names(self) -> list[str]:
        return list(self.task_list)


class DummyTaskToggles(TaskTogglesSource):
    """内存快速开关实现。"""

    def __init__(self) -> None:
        super().__init__()
        self._state: dict[str, bool] = {'a': True, 'b': False, 'c': True}

    def toggles(self) -> list[TaskToggle]:
        return [
            TaskToggle(key=k, label=f'开关{k}', enabled=v)
            for k, v in self._state.items()
        ]

    def set_enabled(self, key: str, enabled: bool) -> None:
        self._state[key] = enabled
        self.togglesChanged.emit()

    def bulk_actions(self) -> list[TaskBulkAction]:
        return [
            TaskBulkAction(label='全选', callback=lambda: self._set_all(True)),
            TaskBulkAction(label='清空', callback=lambda: self._set_all(False)),
        ]

    def _set_all(self, value: bool) -> None:
        for k in self._state:
            self._state[k] = value
        self.togglesChanged.emit()


class DummySession(ShellSession):
    """内存 Shell 会话实现。"""

    def __init__(self, profile_id: str) -> None:
        self._profile_id = profile_id
        self._initialized = False
        self._destroyed = False
        self.control = DummyTaskControl()
        self.toggles = DummyTaskToggles()
        self.attached: TabApi | None = None

    @property
    def profile_id(self) -> str:
        return self._profile_id

    @property
    def title(self) -> str:
        return self._profile_id

    def initialize(self) -> None:
        self._initialized = True

    def destroy(self) -> None:
        self._destroyed = True

    @property
    def is_running(self) -> bool:
        return self.control.running

    def attach_tab(self, api: TabApi) -> None:
        self.attached = api

    def task_control(self) -> TaskControl:
        return self.control

    def task_toggles(self) -> TaskTogglesSource:
        return self.toggles


class DummyProfileProvider(ProfileProvider):
    """内存 profile 后端。"""

    def __init__(self) -> None:
        self.profiles: list[str] = ['p1', 'p2']

    def list_profiles(self) -> list[str]:
        return list(self.profiles)

    def create(self, name: str) -> None:
        if name in self.profiles:
            raise ProfileError(f'已存在: {name}', name)
        self.profiles.append(name)

    def rename(self, old_name: str, new_name: str) -> None:
        if old_name not in self.profiles:
            raise ProfileError(f'不存在: {old_name}', old_name)
        self.profiles[self.profiles.index(old_name)] = new_name

    def remove(self, name: str) -> None:
        if name in self.profiles:
            self.profiles.remove(name)


class DummyPersistence(TabPersistence):
    """内存 Tab 持久化。"""

    def __init__(self) -> None:
        self.state = OpenTabsState()

    def save_open_tabs(self, state: OpenTabsState) -> None:
        self.state = state

    def load_open_tabs(self) -> OpenTabsState:
        return self.state


class DummyAppearanceStore(AppearanceSettingsStore):
    """内存外观配置。"""

    def __init__(self) -> None:
        self.color_scheme = 'auto'
        self.theme_color: str | None = None
        self.window_style = ''

    def get_color_scheme(self) -> str:
        return self.color_scheme

    def set_color_scheme(self, value: str) -> None:
        self.color_scheme = value

    def get_theme_color(self) -> str | None:
        return self.theme_color

    def set_theme_color(self, value: str | None) -> None:
        self.theme_color = value

    def get_window_style(self) -> str:
        return self.window_style

    def set_window_style(self, value: str) -> None:
        self.window_style = value


class DummyPreferencesController(PreferencesControllerBase):
    """内存偏好草稿控制器。"""

    def __init__(self, parent: QObject | None = None) -> None:
        self._store: dict = {
            'interface': {'color_scheme': 'auto', 'theme_color': None, 'window_style': ''},
        }
        super().__init__(parent)

    def _load_config(self) -> dict:
        return copy.deepcopy(self._store)

    def _commit_config(self, merged: dict) -> None:
        self._store = copy.deepcopy(merged)


class DummyPlugin(EuiShellPlugin):
    """测试用 Dummy 插件。"""

    def __init__(self, tmp_dir: Path) -> None:
        self.icon = tmp_dir / 'icon.png'
        self.icon.write_bytes(_PNG_1PX)
        self.overview_qml = tmp_dir / 'DummyOverview.qml'
        self.overview_qml.write_text(
            'import QtQuick\n'
            'Item { implicitWidth: 10; implicitHeight: 10 }\n',
            encoding='utf-8',
        )
        # 最小组合根：带总览内容以验证总览路径
        self.index_qml = tmp_dir / 'index.qml'
        self.index_qml.write_text(
            'import QtQuick\n'
            'import EuiShell\n'
            'EuiShellApp {\n'
            '    overviewContent: Component { Item { implicitWidth: 10; implicitHeight: 10 } }\n'
            '}\n',
            encoding='utf-8',
        )
        self._session = DummySession('p1')
        self.last_splash = None
        self.startup_called = False
        self.post_ready_called = False

    @property
    def app_name(self) -> str:
        return 'Dummy App'

    @property
    def app_version(self) -> str:
        return '0.0.1'

    @property
    def icon_path(self) -> Path:
        return self.icon

    def entry_qml(self) -> Path:
        return self.index_qml

    def create_session(self, profile_id: str) -> ShellSession:
        return DummySession(profile_id)

    def profile_provider(self) -> ProfileProvider:
        return DummyProfileProvider()

    def tab_persistence(self) -> TabPersistence:
        return DummyPersistence()

    def appearance_store(self) -> AppearanceSettingsStore:
        return DummyAppearanceStore()

    def create_preferences_controller(self) -> PreferencesControllerBase:
        return DummyPreferencesController()

    def create_splash_bridge(self):
        from euishell.bridges.splash import SplashBridge

        self.last_splash = SplashBridge()
        return self.last_splash

    def startup(self, ctx: StartupContext) -> None:
        self.startup_called = True
        ctx.splash.onStatusChanged('dummy startup done')

    def post_ready(self, ctx: StartupContext) -> None:
        self.post_ready_called = True



@pytest.fixture
def dummy_plugin(tmp_path: Path) -> DummyPlugin:
    return DummyPlugin(tmp_path)


@pytest.fixture
def qml_engine() -> object:
    """离屏 QML 引擎（按需使用）。"""
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(paths.QML_DIR))
    yield engine
    engine.clearComponentCache()
    engine.deleteLater()
