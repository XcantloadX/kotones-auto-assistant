"""下游会话与协议抽象：ShellSession、TaskControl、TaskTogglesSource 及各类后端接口。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING
from collections.abc import Callable

from pydantic import BaseModel
from PySide6.QtCore import QObject, Signal

from euishell.exceptions import ProfileError

__all__ = [
    'AppearanceSettingsStore',
    'OpenTabsState',
    'ProfileError',
    'ProfileProvider',
    'ShellSession',
    'TabApi',
    'TabPersistence',
    'TaskBulkAction',
    'TaskControl',
    'TaskToggle',
    'TaskTogglesSource',
]

if TYPE_CHECKING:
    from euishell.bridges.log_bridge import LogBridge
    from euishell.bridges.progress import ProgressBridge
    from euishell.controllers.settings_controller import SettingsControllerBase


class TaskToggle(BaseModel):
    """单个快速开关条目。"""

    key: str
    """开关唯一标识（下游写回时使用）。"""
    label: str
    """开关显示文本。"""
    enabled: bool
    """当前是否启用。"""


@dataclass(frozen=True)
class TaskBulkAction:
    """快速开关批量操作按钮。"""

    label: str
    """按钮显示文本。"""
    callback: Callable[[], None]
    """按钮点击回调。"""


class TaskControl(ABC):
    """任务运行控制协议（控制页 / 任务页数据源）。

    实现需线程安全：RunController 通过 1s 定时器轮询状态属性。
    """

    @property
    @abstractmethod
    def running(self) -> bool:
        """当前是否有任务在运行。"""

    @property
    @abstractmethod
    def stopping(self) -> bool:
        """当前是否处于停止中状态。"""

    @property
    @abstractmethod
    def paused(self) -> bool:
        """当前是否处于暂停状态。"""

    @property
    @abstractmethod
    def current_task_name(self) -> str:
        """当前正在执行的任务名；无任务时返回空字符串。"""

    @abstractmethod
    def start(self) -> None:
        """启动全部已启用任务。

        :raises TaskControlError: 启动失败时抛出
        """

    @abstractmethod
    def stop(self) -> None:
        """停止任务。

        :raises TaskControlError: 停止失败时抛出
        """

    @abstractmethod
    def toggle_pause(self) -> None:
        """切换暂停/恢复。

        :raises TaskControlError: 操作失败时抛出
        """

    @abstractmethod
    def run_single(self, name: str) -> None:
        """单独运行指定任务。

        :param name: 任务名
        :raises TaskControlError: 启动失败时抛出
        """

    @abstractmethod
    def task_names(self) -> list[str]:
        """返回所有可单独执行的任务名。"""


class TaskTogglesSource(QObject):
    """快速开关数据源协议。

    数据变化时发射 togglesChanged；RunController 据此刷新模型。
    """

    togglesChanged = Signal()

    @abstractmethod
    def toggles(self) -> list[TaskToggle]:
        """返回当前全部快速开关条目。"""

    @abstractmethod
    def set_enabled(self, key: str, enabled: bool) -> None:
        """写入单个开关状态。

        :param key: 开关唯一标识
        :param enabled: 目标状态
        """

    @abstractmethod
    def bulk_actions(self) -> list[TaskBulkAction]:
        """返回批量操作按钮列表。"""


@dataclass
class TabApi:
    """Shell 注入给 ShellSession 的 shell 侧对象集合。"""

    progress: 'ProgressBridge'
    """该 Tab 的进度桥接，session 可随时推送进度。"""
    log_bridge: 'LogBridge'
    """该 Tab 的日志桥接。"""


class ShellSession(ABC):
    """一个 Tab 会话的抽象基类。

    下游实现本类以承载业务生命周期；Shell 通过 :class:`TabApi` 注入
    shell 侧对象，通过各访问器方法获取下游控制器。
    """

    @property
    @abstractmethod
    def profile_id(self) -> str:
        """会话关联的 profile 标识。"""

    @property
    @abstractmethod
    def title(self) -> str:
        """Tab 显示标题。"""

    @abstractmethod
    def initialize(self) -> None:
        """初始化会话（幂等）。"""

    @abstractmethod
    def destroy(self) -> None:
        """销毁会话（幂等）。"""

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """当前是否有任务在运行。"""

    def attach_tab(self, api: TabApi) -> None:
        """Shell 在创建 Tab 控制器时注入 shell 侧对象（可覆写）。

        :param api: shell 侧对象集合
        """

    def task_control(self) -> TaskControl | None:
        """返回任务运行控制数据源；不需要控制页时返回 None。"""
        return None

    def task_toggles(self) -> TaskTogglesSource | None:
        """返回快速开关数据源；不需要时返回 None。"""
        return None

    def settings_controller(self) -> 'SettingsControllerBase | None':
        """返回该 Tab 的设置控制器；不需要时返回 None。"""
        return None

    def controllers(self) -> dict[str, QObject]:
        """返回自定义页面控制器 role → QObject 映射。"""
        return {}

    def dirty_guards(self) -> list[QObject]:
        """返回该 Tab 的脏检查守卫（需实现 isDirty()/save()/discard()）。"""
        return []


class ProfileProvider(ABC):
    """Profile 管理后端协议（配置管理对话框数据源）。

    :raises ProfileError: 各操作失败时抛出
    """

    @abstractmethod
    def list_profiles(self) -> list[str]:
        """返回全部 profile 名称。"""

    @abstractmethod
    def create(self, name: str) -> None:
        """创建 profile。

        :param name: profile 名称
        :raises ProfileError: 名称冲突等失败时抛出
        """

    @abstractmethod
    def rename(self, old_name: str, new_name: str) -> None:
        """重命名 profile。

        :param old_name: 旧名称
        :param new_name: 新名称
        :raises ProfileError: 名称冲突或不存在时抛出
        """

    @abstractmethod
    def remove(self, name: str) -> None:
        """删除 profile。

        :param name: profile 名称
        :raises ProfileError: 失败时抛出
        """


class OpenTabsState(BaseModel):
    """打开的 Tab 列表持久化状态。"""

    tab_ids: list[str] = []
    """打开中的 Tab 对应 profile 标识，按 Tab 顺序。"""
    last_used: str | None = None
    """最后活跃的 profile 标识。"""


class TabPersistence(ABC):
    """Tab 持久化后端协议。"""

    @abstractmethod
    def save_open_tabs(self, state: OpenTabsState) -> None:
        """保存当前打开 Tab 状态。

        :param state: 待保存状态
        """

    @abstractmethod
    def load_open_tabs(self) -> OpenTabsState:
        """读取已保存的 Tab 状态。

        :returns: 持久化状态；无记录时返回空状态
        """


class AppearanceSettingsStore(ABC):
    """外观配置存取后端协议。

    以下键为 Shell 保留键，下游 store 必须持久化：
    ``interface.color_scheme``、``interface.theme_color``、``interface.window_style``。
    """

    @abstractmethod
    def get_color_scheme(self) -> str:
        """返回色彩方案：'auto' | 'light' | 'dark'。"""

    @abstractmethod
    def set_color_scheme(self, value: str) -> None:
        """保存色彩方案。

        :param value: 'auto' | 'light' | 'dark'
        """

    @abstractmethod
    def get_theme_color(self) -> str | None:
        """返回主题色（#RRGGBB）；跟随系统时为 None。"""

    @abstractmethod
    def set_theme_color(self, value: str | None) -> None:
        """保存主题色。

        :param value: #RRGGBB 或 None（跟随系统）
        """

    @abstractmethod
    def get_window_style(self) -> str:
        """返回窗口背景样式原始值（'' 表示自动）。"""

    @abstractmethod
    def set_window_style(self, value: str) -> None:
        """保存窗口背景样式。

        :param value: '' | 'mica' | 'acrylic' | 'blur' | 'solid'
        """
