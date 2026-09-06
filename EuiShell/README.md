# EuiShell

EuiShell 是一个通用的 PySide6 QML 桌面应用 **Shell UI 框架**：提供窗口（无边框 / Win32 特效）、
多 Tab、页面骨架（控制 / 任务 / 设置 / 日志 / 关于 / 偏好）、日志桥接、Toast 通知、进度展示、
Splash、导航守卫与主题调色板。业务逻辑不属于本框架——下游项目通过插件 API 接入自己的逻辑与 QML。

## 快速上手

```python
from pathlib import Path

from euishell import ShellApp, EuiShellPlugin, ShellRegistry
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

    def register(self, registry: ShellRegistry) -> None:
        ...  # 注册 slot 内容 / 自定义页面 / 设置与偏好 section

    def create_session(self, profile_id: str) -> ShellSession:
        return MySession(profile_id)

    ...


ShellApp(MyPlugin()).run()
```

## 下游接入总览

| 接口 | 位置 | 职责 |
|------|------|------|
| `EuiShellPlugin` | `euishell.plugin` | 应用元信息、注册、会话工厂、生命周期钩子、全局控制器 |
| `ShellSession` | `euishell.session` | 单个 Tab 的业务会话（初始化 / 销毁 / 运行态 / 控制器） |
| `TaskControl` / `TaskTogglesSource` | `euishell.session` | 控制页与任务页的数据源 |
| `SettingsControllerBase` | `euishell.controllers` | Tab 内设置草稿控制器的 QML 契约 |
| `PreferencesControllerBase` | `euishell.controllers` | 偏好（全局配置）草稿控制器基类 |
| `ProfileProvider` / `TabPersistence` / `AppearanceSettingsStore` | `euishell.session` | Profile 管理、Tab 持久化、外观配置存取 |
| `SlotSpec` / `SlotName` | `euishell.plugin` | 具名 QML slot 注入 |

完整的 slot 名称、外观保留键等框架约定见 [AGENTS.md](AGENTS.md)。

## 开发

```bash
uv sync --extra dev   # 安装依赖
uv run ruff check src tests
uv run pyright src tests
uv run pytest
```
