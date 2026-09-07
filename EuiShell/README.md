# EuiShell

EuiShell 是一个通用的 PySide6 QML 桌面应用 **Shell UI 框架**：提供窗口（无边框 / Win32 特效）、
多 Tab、页面骨架（控制 / 任务 / 设置 / 日志 / 关于 / 偏好）、日志桥接、Toast 通知、进度展示、
Splash、导航守卫与主题调色板。业务逻辑不属于本框架——下游项目通过插件 API 接入自己的逻辑与 QML。

## 快速上手

**1. 实现插件（Python）**——提供应用元信息与组合根 QML 路径，接线业务会话与生命周期钩子：

```python
from pathlib import Path

from euishell import ShellApp, EuiShellPlugin
from euishell.session import ShellSession


class MySession(ShellSession):
    """一个 Tab 会话：由下游实现业务生命周期。"""
    ...


class MyPlugin(EuiShellPlugin):
    @property
    def app_name(self) -> str:
        return "My App"

    @property
    def app_version(self) -> str:
        return "1.0.0"

    @property
    def icon_path(self) -> Path:
        return Path("icon.png")

    def entry_qml(self) -> Path:
        return Path("qml/index.qml")  # 下游组合根，根元素须为 EuiShellApp

    def create_session(self, profile_id: str) -> ShellSession:
        return MySession(profile_id)

    ...


ShellApp(MyPlugin()).run()
```

`app_name` / `app_version` / `icon_path` 留在 Python 侧是出于时序原因：QApplication 的应用名与
窗口图标、以及 Splash 配置都在 QML engine 加载之前就需要它们，无法由 QML 提供。

**2. 声明组合根（QML）**——在 `entry_qml()` 指向的 `index.qml` 中实例化 `EuiShellApp`，
以 QML 属性声明全部插槽内容：

```qml
import QtQuick
import EuiShell
import "pages"
import "slots"

EuiShellApp {
    overviewContent: OverviewSlot { }      // 总览 Tab 内容（null 时总览 Tab 整体隐藏）
    titleBarTrailing: UpdateIndicator { }  // 标题栏按钮区末尾
    windowDialogs: AppDialogs { }          // 窗口级对话框 / 非可视组件

    pages: [
        EuiPageSpec { title: "方案"; source: ProducePage { } }
    ]
    fullscreenPages: [
        EuiFullscreenPageSpec { id: "browser"; source: BrowserPage { } }
    ]

    settingsSections: [
        EuiSectionSpec { title: "基本"; source: BasicSection { } }
    ]
    preferenceSections: [
        EuiSectionSpec { title: "更新"; source: UpdateSection { } }
    ]

    aboutLinks: [
        EuiLink { label: "GitHub"; url: "https://github.com/example/my-app" }
    ]
}
```

### EuiShellApp 扩展点

| 属性 | 类型 | 实例化策略 |
|------|------|-----------|
| `overviewContent` | `Component`（默认 null） | 窗口级 1 份；null → 总览 Tab 整体隐藏 |
| `titleBarTrailing` | `Component` | 窗口级 1 份 |
| `windowDialogs` | `Component` | 窗口级 1 份 |
| `controlNotices` | `Component` | 每 Tab 1 份 |
| `controlRunExtras` | `Component` | 每 Tab 1 份 |
| `controlFooter` | `Component` | 每 Tab 1 份 |
| `aboutExtra` | `Component` | 每 Tab 1 份 |
| `pages` | `list<EuiPageSpec>` | 每 Tab 1 份；声明顺序即导航顺序，位于设置页之后、日志页之前 |
| `fullscreenPages` | `list<EuiFullscreenPageSpec>` | 窗口级；经 NavigationCoordinator 进入 |
| `settingsSections` | `list<EuiSectionSpec>` | 每 Tab 1 份 |
| `preferenceSections` | `list<EuiSectionSpec>` | 窗口级 1 份（偏好页全屏独占，外观 section 内置并置首） |
| `aboutLinks` | `list<EuiLink>` | 纯数据 |

spec 类型：`EuiPageSpec { title; source: Component }`、
`EuiFullscreenPageSpec { id: string; source: Component }`（id 与 `window.fullscreenMode`
字符串匹配，内置偏好页 id 为 `"preferences"`）、`EuiSectionSpec { title; source: Component }`、
`EuiLink { label; url }`。

下游内容根元素契约（可选注入属性、上下文捕获纪律）、控制器访问方式等完整约定见
[AGENTS.md](AGENTS.md)。

## 下游接入总览

| 接口 | 位置 | 职责 |
|------|------|------|
| `EuiShellPlugin` | `euishell.plugin` | 应用元信息、组合根 QML 路径（`entry_qml()`）、会话工厂、生命周期钩子、全局控制器 |
| `ShellSession` | `euishell.session` | 单个 Tab 的业务会话（初始化 / 销毁 / 运行态 / 控制器） |
| `TaskControl` / `TaskTogglesSource` | `euishell.session` | 控制页与任务页的数据源 |
| `SettingsControllerBase` | `euishell.controllers` | Tab 内设置草稿控制器的 QML 契约 |
| `PreferencesControllerBase` | `euishell.controllers` | 偏好（全局配置）草稿控制器基类 |
| `ProfileProvider` / `TabPersistence` / `AppearanceSettingsStore` | `euishell.session` | Profile 管理、Tab 持久化、外观配置存取 |
| `EuiShellApp`（`import EuiShell`） | 框架 QML | 声明式 QML 扩展点：总览、标题栏、窗口对话框、控制页附加、自定义页、全屏页、设置/偏好 section、关于页外链（spec 类型 `EuiPageSpec` / `EuiFullscreenPageSpec` / `EuiSectionSpec` / `EuiLink`） |

完整的扩展点约定、下游内容根元素契约、外观保留键等框架约定见 [AGENTS.md](AGENTS.md)。

## 开发

```bash
uv sync --extra dev   # 安装依赖
uv run ruff check src tests
uv run pyright src tests
uv run pytest
```
