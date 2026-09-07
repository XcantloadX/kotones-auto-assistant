# AGENTS.md

EuiShell — 通用 PySide6 QML 桌面应用 Shell UI 框架。本框架只提供 Shell UI（Tab、窗口控制、页面骨架、日志、通知等），业务逻辑由下游项目通过插件 API 接入。

## 注释规范

### Python — Docstring 格式

使用 **reStructuredText (RST)** 格式，中文撰写：

```python
def func(param1: str, param2: int) -> bool:
    """简要描述功能。

    :param param1: 参数说明
    :param param2: 参数说明
    :returns: 返回值说明
    :raises SomeError: 异常说明
    """
```

#### 覆盖范围

| 元素 | 必须 | 格式 |
|------|------|------|
| 模块 | 是 | 文件顶部一行中文描述 |
| 类 | 是 | 类定义下方，中文 |
| 公开方法 | 是 | RST，中文 |
| 私有方法 | 推荐 | 一行 `#` 注释或 docstring |
| 属性（dataclass / pydantic field） | 推荐 | 字段后的注释 |

#### 代码行内注释

- 复杂逻辑段上方加 `#` 注释说明意图
- **禁止**写「这段代码做了什么」这类显而易见的注释，而应写「为什么要这样做」
- 中文注释

### TypeScript / React 代码

要求与 Python 保持一致，但使用 **JSDoc** 风格：

```ts
/** 简要描述功能。
 *
 * @param param1 - 参数说明
 * @param param2 - 参数说明
 * @returns 返回值说明
 */
function func(param1: string, param2: number): boolean { ... }
```

#### 覆盖范围

| 元素 | 必须 | 格式 |
|------|------|------|
| 模块/文件 | 是 | 文件顶部 `/** ... */` 或行注释 |
| 组件 | 是 | JSDoc，中文 |
| 公开函数/方法 | 是 | JSDoc，中文 |
| 私有方法/辅助函数 | 推荐 | JSDoc 或行注释 |
| Props 接口 / 类型定义 | 推荐 | 字段后注释 |

行内注释使用 `//`，中文，只写「为什么」不写「做了什么」。


## 通用规范
### 路径管理集中化

- **严格禁止**在代码中散落路径字符串字面量（包括文件系统路径与 API 路径）。
- 如果某个路径是项目内约定俗成的固定路径，例如 `./logs`、`./conf` 等，必须在某处专用管理路径的模块内提供常量与拼接函数。如果不存在这样的模块，先询问用户关于在哪里创建的意见。
- 对于约定好的固定路径，**绝对禁止**任何形式的裸露字符串插值。

### 兼容性

- 如果本次更改涉及配置、数据、公共 API 等兼容性问题，**总是显式询问**用户为兼容性更新还是破坏性更新。
- 如果本次更改仅涉及内部 API、方法、类等**更名**，**总是不需要兼容性**（除非用户提出）。并且必须一次性完成所有调用方的重命名。
- 如果需要移除某功能或 API，**严格禁止在任何位置留下"XXX已移除""XXX现已被XXX代替"等无意义说明。此项必须绝对执行！**

### 类型
- 对于 Python 与 TypeScript，必须严格执行类型标注。**除非极其困难，否则不得使用 any、unknown！**
- **除非极其困难，否则不得使用 `//ts-igore`、`# type: ignore` 等任意类型忽略！**
- 本次更改的代码中，若涉及 any、unknown 或任意类型 ignore，必须向用户报告。
- 对于 TS，**尽量避免**过长的 inline 类型。
- 对于 PySide/PyQt，类型忽略规则不适用，允许一定程度的类型忽略。

### 降级处理
- 任何时候，除非用户显式要求，否则**绝对禁止**编写任何形式的 fallback。
- **绝对禁止**任何形式的"简化处理"或"placeholder 代码"。如果是因为用户要求模糊导致，总是停下来询问用户，直到得出明确清晰的实现为止才开始编写代码。
- 总是遵循 fail fast 原则。

## Python 代码规范

### 禁止裸露 dict / tuple

- **绝对禁止**在代码中使用裸露的 `dict`（包括任意字面量 `{...}` 作为数据容器）。
- **绝对禁止**使用超过两个元素的裸露 `tuple`（两个元素的 `tuple` 仅限用于类似 `(x, y)` 坐标等明确场景）。
- 如果项目内需要大量利用数据类，**优先考虑使用 Pydantic 或 attrs+cattrs**。二者内优先采用项目内已有，如果都没有，询问用户是否装新库。

### import 规则

- 除非是重依赖懒加载、平台可选依赖、循环导入等场景，否则**严格禁止**在非文件顶部导入模块。
- 除非用户明确要求这是可选依赖，否则**严格禁止** try import except print("依赖未安装")。
- **import 库总是不考虑 try except 与 fallback**，除非这是平台兼容或 Python 兼容相关代码。

### 日志与异常处理
- raise 异常时，**尽可能避免** RuntimeError/Exception，而是定义足够语义化的异常。如果项目内还没有成体系的异常系统，总是先询问用户意见。
- 捕获异常后，**绝对需要**日志输出，哪怕这是预期中可被处理的情况。
- 在编写代码的过程中，**总是**有意识的输出可辅助调试与排查问题的日志。不要一条日志都没有，也不要过于 verbose。
- **禁止用裸露 print 输出日志**。总是采用 logging 库（或项目内已有的三方日志库，如有）。如果用 logging，优先采用下面的 pattern：
```python
import logging

logger = logging.getLogger(__name__) # 每个模块/文件都这么做

def foo(): logger.debug(...)

# 入口处。可能是调试入口，或 cli/gui 入口
if __name__ == "__main__":
    logger.basicConfig(...) # 默认 DEBUG level，展示格式"[2026-09-01 20:01:00,000][DEBUG][{logger name}] ..."
```

### HTTP 交互
- **绝对禁止**任何裸露 fetch/XHR/axios，而是使用项目内已有的请求体系。如果没有这样的体系，总是先询问用户是否建立。
- 在定义 API 请求与响应格式时，**总是**遵循项目内已有的体系。如果没有这样的体系，总是先询问用户是否建立。

### 杂项
- **任何时候都绝对禁止**使用 `from __future__ import annotations`。

## 代码质量

每次代码修改完成后，必须运行以下检查并确保全部通过：

| 范围 | 命令 | 说明 |
|------|------|------|
| Python lint | `uv run ruff check src tests` | ruff 规则检查 |
| Python type | `uv run pyright src tests` | pyright 类型检查 |
| Python tests | `uv run pytest` | 全部单测 |
| TS/React lint | `cd frontend && npm run lint` | ESLint 规则检查 |
| TS/React test | `cd frontend && npm run test` | Vitest 单元测试 |
| TS/React build | `cd frontend && npm run build` | 类型检查 + 生产构建 |

（EuiShell 无 frontend，TS 相关检查不适用。）


## Commit 规范

采用 Angular Commit Convention，message 用中文，scope 示例：

| Scope | 说明 |
|-------|------|
| **backend** | `src/maatune/` Python 代码 |
| **frontend** | `frontend/` React SPA |
| **docs** | `docs/`、`AGENTS.md`、`README.md` |
| **deps** | 依赖升级 |
| **ci** | `.github/workflows/`、构建配置 |

EuiShell 内 scope 统一使用 **shell**（如 `feat(shell): ...`）。

除非有特别原因或特殊情况，否则**绝对禁止**在 git commit message body 里复述一遍变更。

---

# EuiShell 框架约定

## 框架定位

EuiShell 只提供 **Shell UI**，不包含任何业务逻辑：

- 提供：窗口（无边框/Win32 特效）、多 Tab、页面骨架（控制/任务/设置/日志/关于/偏好）、日志桥接、Toast 通知、进度展示、Splash、导航守卫、主题调色板。
- 不提供：配置文件管理、任务调度、真实脚本逻辑。这些由下游项目实现框架定义的接口后注入。

## 下游接入方式

下游项目实现 `euishell.plugin.EuiShellPlugin`，构造 `ShellApp(plugin).run()` 即可启动 Shell。
engine 加载 `plugin.entry_qml()` 指向的下游组合根 `index.qml`（根元素须为 `EuiShellApp`），
加载失败抛 `QmlLoadError` fail-fast：

- `app_name` / `app_version` / `icon_path` — 应用元信息。QApplication 名称 / 窗口图标与
  Splash 配置都在 QML engine 加载之前需要，因此留在 Python 侧。
- `entry_qml()` — 返回下游组合根 `index.qml` 路径，插槽内容由 QML 扩展点属性声明（见下节）。
- `create_session(profile_id)` — 为每个 Tab 创建一个 `ShellSession`（下游业务会话）。
- `startup(ctx)` / `post_startup(ctx)` / `post_ready(ctx)` / `shutdown(ctx)` — 后台线程生命周期钩子。
- `global_controllers(ctx)` — 下游全局控制器，以 role 名注册为 QML context property，
  QML 中裸名引用。
- 其余接口见 `src/euishell/plugin.py` 与 `src/euishell/session.py` 的 docstring。

## QML 扩展点约定

下游在 `entry_qml()` 指向的 `index.qml` 中实例化 `EuiShellApp`，通过扩展点属性声明式传入
全部插槽内容（Component / spec 对象），实例化策略由框架内部决定：

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

spec 类型：

- `EuiPageSpec { title; source: Component }`
- `EuiFullscreenPageSpec { id: string; source: Component }` — id 与 `window.fullscreenMode`
  字符串匹配；内置偏好页 id 为 `"preferences"`
- `EuiSectionSpec { title; source: Component }`
- `EuiLink { label; url }`

### 下游内容根元素契约

下游组件被框架以 `Loader { sourceComponent: <下游 Component> }` 实例化，Component 的创建
上下文是 `index.qml`（而非挂载点页面），required 属性无法经创建上下文自动解析。约定：

- 根元素声明**非 required** 的可选注入属性：`property var tab`、`property var navigation`、
  `property var settingsCtrl`、`property var prefsCtrl`、`property var errors`、
  `property string fullscreenMode` 等；
- 框架 mount 在 `onLoaded` 中按 `hasOwnProperty` 逐个回填；
- 上下文捕获纪律：窗口级声明的对象天然被所有克隆共享（可依赖全局 context property）；
  **per-tab 状态只允许经注入的 `tab` / 控制器获取**，禁止在声明处捕获窗口级有状态对象。

### 控制器访问

- 全局控制器：`global_controllers()` 的 role → context property，裸名引用（如 `GameDataCtrl`）。
- Tab 内控制器：组件根元素经注入的 `tab` 访问 `tab.controller(role)` / `tab.settingsCtrl` /
  `tab.runCtrl`。

## 外观配置保留键

偏好配置 map 中以下键为 Shell 保留键（Shell 直接消费，下游 store 必须支持）：

- `interface.color_scheme`: `'auto' | 'light' | 'dark'`
- `interface.theme_color`: `str | None`
- `interface.window_style`: `'' | 'mica' | 'acrylic' | 'blur' | 'solid'`

## 路径常量

框架内所有固定路径（QML 目录、字体等）集中管理于 `src/euishell/paths.py`。
