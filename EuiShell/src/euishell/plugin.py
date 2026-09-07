"""下游插件 API：生命周期钩子上下文与 EuiShellPlugin 抽象基类。"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from euishell.bridges.splash import SplashBridge
from PySide6.QtCore import QObject

if TYPE_CHECKING:
    from euishell.controllers.preferences_controller import PreferencesControllerBase
    from euishell.controllers.tab_manager import TabManager
    from euishell.session import (
        AppearanceSettingsStore,
        ProfileProvider,
        ShellSession,
        TabPersistence,
    )

logger = logging.getLogger(__name__)


@dataclass
class StartupContext:
    """传给插件生命周期钩子的上下文对象。"""

    splash: 'SplashBridge'
    """Shell Splash 桥接，可用于更新启动状态文本与下载进度。"""
    tab_manager: 'TabManager'
    """Shell Tab 管理器。"""


class EuiShellPlugin(ABC):
    """下游应用接入 EuiShell 的插件抽象基类。

    下游实现全部抽象方法后，构造 ``ShellApp(plugin).run()`` 启动 Shell。
    """

    @property
    @abstractmethod
    def app_name(self) -> str:
        """应用显示名（窗口标题、Splash、侧边导航品牌区）。"""

    @property
    @abstractmethod
    def app_version(self) -> str:
        """应用版本号字符串（Splash / 关于页展示）。"""

    @property
    @abstractmethod
    def icon_path(self) -> Path:
        """应用图标 PNG 路径。"""

    @abstractmethod
    def entry_qml(self) -> Path:
        """返回下游组合根 index.qml 路径；根元素须为 EuiShellApp。

        :returns: index.qml 文件路径
        """

    @abstractmethod
    def create_session(self, profile_id: str) -> 'ShellSession':
        """创建一个 Tab 会话。

        :param profile_id: 会话关联的 profile 标识
        :returns: Shell 会话实例
        """

    @abstractmethod
    def profile_provider(self) -> 'ProfileProvider':
        """返回 profile 管理后端（配置管理对话框使用）。"""

    @abstractmethod
    def tab_persistence(self) -> 'TabPersistence':
        """返回 Tab 持久化后端（恢复/保存打开的 Tab 列表）。"""

    @abstractmethod
    def appearance_store(self) -> 'AppearanceSettingsStore':
        """返回外观配置存取后端（偏好页外观 section 与启动配色使用）。"""

    @abstractmethod
    def create_preferences_controller(self) -> 'PreferencesControllerBase':
        """创建偏好（全局配置）草稿控制器。"""

    def create_splash_bridge(self) -> 'SplashBridge':
        """创建 Splash 桥接；下游可子类化以扩展信号。"""
        return SplashBridge()

    def startup(self, ctx: StartupContext) -> None:
        """后台线程启动钩子：执行阻塞初始化（如资源更新）。

        :param ctx: 启动上下文
        """

    def post_startup(self, ctx: StartupContext) -> None:
        """后台线程钩子：Tab 恢复后、UI 就绪前调用。

        :param ctx: 启动上下文
        """

    def post_ready(self, ctx: StartupContext) -> None:
        """后台线程钩子：UI 就绪后调用（如后台检查更新）。

        :param ctx: 启动上下文
        """

    def global_controllers(self, ctx: StartupContext) -> dict[str, QObject]:
        """返回全局控制器 role → QObject 映射（注册为 QML 上下文属性）。

        :param ctx: 启动上下文（Tab 管理器已就绪，供控制器构造引用）
        """
        return {}

    def global_dirty_guards(self) -> list[QObject]:
        """返回全局脏检查守卫（需实现 isDirty()/save()/discard()）。"""
        return []

    def shutdown(self, ctx: StartupContext) -> None:
        """事件循环结束后的清理钩子（后台资源停止等）。

        :param ctx: 启动上下文
        """
