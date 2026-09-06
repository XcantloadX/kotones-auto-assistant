"""下游插件 API：注册规格模型、ShellRegistry 与 EuiShellPlugin 抽象基类。"""
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from PySide6.QtCore import QObject, Slot

from euishell import paths
from euishell.bridges.splash import SplashBridge
from euishell.exceptions import RegistrationError

if TYPE_CHECKING:
    from PySide6.QtCore import QObject

    from euishell.controllers.preferences_controller import PreferencesControllerBase
    from euishell.controllers.tab_manager import TabManager
    from euishell.session import (
        AppearanceSettingsStore,
        ProfileProvider,
        ShellSession,
        TabPersistence,
    )

logger = logging.getLogger(__name__)


class SlotName:
    """Shell 内置 slot 名称常量。"""

    OVERVIEW = 'overview.content'
    """总览 Tab 内容；不注册则隐藏总览 Tab。"""
    TITLEBAR_TRAILING = 'titlebar.trailing'
    """标题栏按钮区末尾。"""
    WINDOW_DIALOGS = 'window.dialogs'
    """主窗口级对话框 / 非可视组件。"""
    ABOUT_EXTRA = 'about.extra'
    """关于页附加内容。"""
    CONTROL_RUN_EXTRAS = 'control.runExtras'
    """控制页运行控制行内附加控件。"""
    CONTROL_NOTICES = 'control.notices'
    """控制页顶部通知区。"""
    CONTROL_FOOTER = 'control.footer'
    """控制页底部附加区。"""

    ALL: tuple[str, ...] = (
        OVERVIEW,
        TITLEBAR_TRAILING,
        WINDOW_DIALOGS,
        ABOUT_EXTRA,
        CONTROL_RUN_EXTRAS,
        CONTROL_NOTICES,
        CONTROL_FOOTER,
    )


class PageId:
    """Shell 内置页面 id 常量（供自定义页面 after 定位锚点使用）。"""

    CONTROL = 'control'
    TASK = 'task'
    SETTINGS = 'settings'
    LOG = 'log'
    ABOUT = 'about'


class AboutLink(BaseModel):
    """关于页外链条目。"""

    label: str
    """链接显示文本。"""
    url: str
    """链接目标 URL。"""


class PageSpec(BaseModel):
    """自定义页面规格。

    QML 文件的根元素应声明 ``required property var tab``（Tab 内页面）
    或直接使用全局上下文属性（全屏页面）。
    """

    id: str
    """页面唯一 id。"""
    title: str
    """侧边导航显示标题。"""
    qml_file: Path
    """页面 QML 文件路径。"""
    after: str | None = None
    """插入锚点：置于指定页面 id 之后；为 None 时追加到设置页之后、日志页之前。"""
    controller_role: str | None = Field(default=None, alias='controllerRole')
    """该页面默认控制器的 role 名；由 ``TabController.controller(role)`` 解析。"""

    model_config = {'populate_by_name': True}


class SlotItemSpec(BaseModel):
    """slot 内单个 QML 组件规格。"""

    qml_file: Path
    """组件 QML 文件路径。"""
    controller_role: str | None = Field(default=None, alias='controllerRole')
    """组件所需控制器 role；Tab 内 slot 由 TabController 解析，全局 slot 由 ShellRegistry 解析。"""

    model_config = {'populate_by_name': True}


class SlotSpec(BaseModel):
    """具名 slot 规格。"""

    name: str
    """slot 名称，必须取自 :class:`SlotName`。"""
    items: list[SlotItemSpec]
    """slot 内容组件列表，按注册顺序渲染。"""


class SectionSpec(BaseModel):
    """设置页 / 偏好页 section 规格。

    QML 文件的根元素应声明 ``required property var settingsCtrl``
    （设置 section）或 ``required property var prefsCtrl``（偏好 section）。
    """

    id: str
    """section 唯一 id。"""
    title: str
    """section 显示标题。"""
    qml_file: Path
    """section QML 文件路径。"""


@dataclass
class StartupContext:
    """传给插件生命周期钩子的上下文对象。"""

    splash: 'SplashBridge'
    """Shell Splash 桥接，可用于更新启动状态文本与下载进度。"""
    tab_manager: 'TabManager'
    """Shell Tab 管理器。"""


class ShellRegistry(QObject):
    """收集插件注册内容，并向 QML 暴露只读 JSON 视图。

    同时承载插件全局控制器的 role → QObject 映射（由 ShellApp 填充）。
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._custom_pages: list[PageSpec] = []
        self._fullscreen_pages: list[PageSpec] = []
        self._slots: dict[str, list[SlotItemSpec]] = {}
        self._settings_sections: list[SectionSpec] = []
        self._preference_sections: list[SectionSpec] = []
        self._global_controllers: dict[str, QObject] = {}
        self._app_name: str = ''
        self._about_links: list[AboutLink] = []

    # ── 注册 API（插件在 register() 中调用）────────────────────

    def set_app_info(self, app_name: str, links: list[AboutLink]) -> None:
        """写入应用名与关于页外链（由 ShellApp 在 register 前调用）。

        :param app_name: 应用显示名
        :param links: 关于页外链列表
        """
        self._app_name = app_name
        self._about_links = list(links)

    def register_page(self, spec: PageSpec) -> None:
        """注册一个 Tab 内自定义页面。

        :param spec: 页面规格
        :raises RegistrationError: 页面 id 重复或锚点非法时抛出
        """
        self._ensure_unique_page_id(spec.id)
        if spec.after is not None:
            self._ensure_valid_anchor(spec.after)
        self._custom_pages.append(spec)
        logger.debug("Registered custom page '%s' (%s)", spec.id, spec.qml_file)

    def register_fullscreen_page(self, spec: PageSpec) -> None:
        """注册一个全屏覆盖页面（通过 NavigationCoordinator 进入）。

        :param spec: 页面规格；title 不使用
        :raises RegistrationError: 页面 id 重复时抛出
        """
        self._ensure_unique_page_id(spec.id)
        self._fullscreen_pages.append(spec)
        logger.debug("Registered fullscreen page '%s'", spec.id)

    def register_slot(self, spec: SlotSpec) -> None:
        """注册一个具名 slot 的内容。

        :param spec: slot 规格
        :raises RegistrationError: slot 名未知或重复注册时抛出
        """
        if spec.name not in SlotName.ALL:
            raise RegistrationError(f'未知 slot: {spec.name}')
        if spec.name in self._slots:
            raise RegistrationError(f'slot "{spec.name}" 已注册')
        self._slots[spec.name] = list(spec.items)
        logger.debug("Registered slot '%s' with %d item(s)", spec.name, len(spec.items))

    def register_settings_section(self, spec: SectionSpec) -> None:
        """注册设置页 section（按注册顺序渲染为 Tab）。

        :param spec: section 规格
        :raises RegistrationError: section id 重复时抛出
        """
        self._ensure_unique_section_id(spec.id, self._settings_sections, 'settings')
        self._settings_sections.append(spec)

    def register_preference_section(self, spec: SectionSpec) -> None:
        """注册偏好页 section（按注册顺序渲染；外观 section 由 Shell 内置并置首）。

        :param spec: section 规格
        :raises RegistrationError: section id 重复时抛出
        """
        self._ensure_unique_section_id(spec.id, self._preference_sections, 'preference')
        self._preference_sections.append(spec)

    def set_global_controllers(self, controllers: dict[str, QObject]) -> None:
        """写入插件全局控制器（由 ShellApp 调用）。"""
        self._global_controllers = dict(controllers)

    # ── 内部校验 ────────────────────────────────────────────────

    def _ensure_unique_page_id(self, page_id: str) -> None:
        existing = [p.id for p in self._custom_pages] + [p.id for p in self._fullscreen_pages]
        if page_id in existing:
            raise RegistrationError(f'页面 id 重复: {page_id}')

    def _ensure_valid_anchor(self, anchor: str) -> None:
        builtins = {PageId.CONTROL, PageId.TASK, PageId.SETTINGS, PageId.LOG, PageId.ABOUT}
        custom_ids = [p.id for p in self._custom_pages]
        # 锚点允许指向尚未注册的自定义页面（后续注册），此处仅校验非内建锚点格式。
        if anchor not in builtins and anchor not in custom_ids:
            logger.warning("Page anchor '%s' is not builtin or (yet) registered", anchor)

    def _ensure_unique_section_id(self, section_id: str, sections: list[SectionSpec], kind: str) -> None:
        if any(s.id == section_id for s in sections):
            raise RegistrationError(f'{kind} section id 重复: {section_id}')

    # ── Python 侧访问 ───────────────────────────────────────────

    def custom_pages(self) -> list[PageSpec]:
        """返回全部 Tab 内自定义页面。"""
        return list(self._custom_pages)

    def settings_sections(self) -> list[SectionSpec]:
        """返回全部设置页 section。"""
        return list(self._settings_sections)

    def preference_sections(self) -> list[SectionSpec]:
        """返回全部偏好页 section。"""
        return list(self._preference_sections)

    # ── QML Slots ───────────────────────────────────────────────

    @Slot(str, result=str)
    def slotItemsJson(self, name: str) -> str:
        """返回指定 slot 的内容组件列表 JSON。"""
        items = self._slots.get(name, [])
        return json.dumps(
            [
                {'url': paths.file_url(item.qml_file), 'controllerRole': item.controller_role or ''}
                for item in items
            ],
            ensure_ascii=False,
        )

    @Slot(result=bool)
    def hasOverview(self) -> bool:
        """总览 slot 是否已注册内容。"""
        return bool(self._slots.get(SlotName.OVERVIEW))

    @Slot(result=str)
    def customPagesJson(self) -> str:
        """返回全部 Tab 内自定义页面 JSON。"""
        return json.dumps(
            [
                {'id': p.id, 'title': p.title, 'url': paths.file_url(p.qml_file), 'after': p.after or ''}
                for p in self._custom_pages
            ],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def settingsSectionsJson(self) -> str:
        """返回全部设置页 section JSON。"""
        return json.dumps(
            [{'id': s.id, 'title': s.title, 'url': paths.file_url(s.qml_file)} for s in self._settings_sections],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def preferenceSectionsJson(self) -> str:
        """返回全部偏好页 section JSON（不含内置外观 section）。"""
        return json.dumps(
            [{'id': s.id, 'title': s.title, 'url': paths.file_url(s.qml_file)} for s in self._preference_sections],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def fullscreenPagesJson(self) -> str:
        """返回全部全屏覆盖页面 JSON。"""
        return json.dumps(
            [{'id': p.id, 'url': paths.file_url(p.qml_file)} for p in self._fullscreen_pages],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def aboutJson(self) -> str:
        """返回关于页信息 JSON（应用名 + 外链）。"""
        return json.dumps(
            {
                'appName': self._app_name,
                'links': [{'label': link.label, 'url': link.url} for link in self._about_links],
            },
            ensure_ascii=False,
        )

    @Slot(str, result='QVariant')  # type: ignore
    def globalController(self, role: str) -> QObject | None:
        """按 role 返回插件全局控制器。

        :param role: 控制器 role 名
        """
        return self._global_controllers.get(role)


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
    def register(self, registry: ShellRegistry) -> None:
        """注册页面、slot、section 等自定义内容。

        :param registry: Shell 注册表
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

    def about_links(self) -> list[AboutLink]:
        """返回关于页外链列表。"""
        return []

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
