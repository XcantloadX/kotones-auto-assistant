# EuiShell × KAA：插槽机制 QML 原生化重构计划

> 注：本文件原为「定时执行功能开发计划」，该功能已落地（`SchedulerService` /
> `ScheduleManagerDialog` 等），原文可在 git 历史中找回。本文件现记录插槽机制重构计划。

## 1. 背景与目标

EuiShell 当前的下游扩展机制是「注册制」：下游在 Python 侧调用 `registry.register_slot() /
register_page() / register_settings_section()` 等 API 提交 QML 文件路径，框架经
`ShellRegistry` 的 JSON 视图（`slotItemsJson()` 等）把数据搬回 QML，由 `SlotHost`
（Repeater + Loader file:// 动态加载）实例化。

本重构将扩展机制切换为 **QML 原生形式**：

- 下游拥有一个 `index.qml` 组合根，在其中实例化框架类型 `EuiShellApp`（ApplicationWindow），
  通过 **QML 属性**传入全部插槽内容（Component / spec 对象）。
- 删除整套注册制胶水：`ShellRegistry`、`SlotSpec` 系列 Pydantic 模型、JSON 桥、
  `SlotHost.qml`、`SlotName` 双语镜像及其同步测试、QML 文件路径的 Python 侧登记。
- **Python 入口不变**：`ShellApp(plugin).run()` 仍是唯一启动方式，engine、context
  property、splash 时序仍由框架保证；变化的只是 engine 加载的目标文件从框架内置
  `main.qml` 改为 `plugin.entry_qml()`（下游 index.qml）。

### 设计原则（已讨论确认的结论）

1. 所有扩展点在 QML 侧统一为 **Component 属性 / spec 列表**；「实例化几份、何时实例化」
   完全是框架内部决策（窗口级 1 份 / 每 Tab 1 份），由内建页面中的 `Loader {
   sourceComponent: ... }` 承担——与 delegate / `PageContainer.titleRightContent` 是同一套
   原生机制。
2. 下游 UI 组合全部收敛到一个 index.qml；Python 插件 API 收窄为纯生命周期 / 会话 / 控制器。
3. 错误处理从「运行时 RegistrationError」转为「QML 编译期错误」：属性拼错、类型不符在
   qmllint / 加载期暴露；index.qml 加载失败整体 fail-fast（`QmlLoadError`）。
4. 破坏性更新：EuiShell 尚无第三方下游（kaa 是同仓唯一下游），不做兼容层，一次性完成
   全部调用方迁移（符合 AGENTS.md「不留兼容说明」原则）。

## 2. 现状盘点（重构涉及面）

### 2.1 EuiShell Python（`EuiShell/src/euishell/`）

| 文件 | 与注册制相关的现状 |
|------|--------------------|
| `plugin.py` | `SlotName` / `PageId` / `AboutLink` / `PageSpec` / `SlotItemSpec` / `SlotSpec` / `SectionSpec` 七个声明；`ShellRegistry`（注册 API + 6 个 `*Json()` QML 视图 + `globalController`）；`EuiShellPlugin.register()` / `about_links()` 抽象 |
| `app.py` | `exec_with()`：创建 `ShellRegistry` → `set_app_info` → `plugin.register(registry)` → `setContextProperty('ShellRegistry', ...)` → `engine.load(QML_MODULE_DIR / 'main.qml')` |
| `exceptions.py` | `RegistrationError`（仅被注册校验与 kaa 的 `_qml()` 使用） |
| `paths.py` | `qml_url()`（无引用，随注册制失去意义）；`file_url()` 仍被 splash / 字体使用，**保留** |
| `__init__.py` | 导出 `ShellRegistry` / `SlotName` |
| `session.py` / `controllers/*` / `bridges/*` / `theme.py` / `win32.py` | 与插槽机制无关，**全部不动** |

### 2.2 EuiShell QML（`qml/EuiShell/`）

| 文件 | 现状 | 动作 |
|------|------|------|
| `main.qml` | Shell 窗口骨架；读 `ShellRegistry.fullscreenPagesJson()/hasOverview()`；3 处 `SlotHost` | 改造为 `EuiShellApp.qml` 类型 |
| `SlotHost.qml` / `SlotName.qml` | 注册制的 QML 消费端 | **删除** |
| `qmldir` | 注册 `SlotHost` / `singleton SlotName` | 更新 |
| `components/TabContent.qml` | 读 `customPagesJson()`；静态内建页 + Repeater(Loader/setSource url) | 改读属性 |
| `components/TabStrip.qml` | `titlebar.trailing` 的 SlotHost（窗口级单实例） | 改属性 |
| `components/TitleBar.qml` | `showOverview: ShellRegistry.hasOverview()` | 改属性 |
| `pages/ControlPage.qml` | `controlNotices` / `controlRunExtras` / `controlFooter` 三个 SlotHost（per-tab） | 改 Loader mount |
| `pages/AboutPage.qml` | `aboutJson()` + `about.extra` SlotHost（per-tab） | 改属性 |
| `pages/SettingsPage.qml` | `settingsSectionsJson()` + Repeater(Loader/setSource url)，errors 动态回填 | 改属性 |
| `pages/PreferencesPage.qml` | `preferenceSectionsJson()` + 内置外观 section | 改属性 |
| `pages/TaskPage.qml` / `LogPage.qml` / `SplashOverlay` / `LoadingOverlay` / `AppTheme` / `FluentIcons` / `form/` / `controls/` | 无插槽依赖 | 不动 |

### 2.3 KAA 侧

| 文件 | 现状 | 动作 |
|------|------|------|
| `kaa/application/ui/plugin.py` | `register()` 注册 2 个 Tab 页、1 个全屏页、7 个 slot、4 个设置 section、6 个偏好 section；`about_links()`；`_qml()` 路径存在性校验 | 大幅精简 |
| `kaa/main/qml_app.py` | `ShellApp(KaaPlugin()).run()` | 不变 |
| `qml/slots/EndActionRow.qml` 等 3 个 per-tab slot | 声明 `required property var tab`，经 `tab.controller("control"/"feedback")` 取控制器 | 契约微调（见 §3.5） |
| `qml/components/UpdateIndicator.qml` | titlebar.trailing 内容；注释提及 SlotHost | 仅注释清理 |
| `qml/pages/ProducePage.qml` / `UpdatePage.qml` | 自定义 Tab 页，`required property var tab`（由 `setSource` 初始属性满足） | 契约微调 |
| `qml/pages/SkillCardBrowserPage.qml` | 全屏页，`property var navigation`（已非 required） | 不动 |
| `qml/slots/KaaDialogs.qml` / `OverviewSlot.qml` / `GameDataVersionRow.qml` | 依赖全局 context property（`splash` / `TabManager` / `GameDataCtrl`），无 tab | 不动 |
| `kaa/application/ui/kaa_session.py` | `controllers()` 返回 `control/produce/update/feedback` 四个 role | 不动 |
| 各设置/偏好 section（4 + 6 个） | 声明 `required property var settingsCtrl` / `required property var prefsCtrl` | 改非 required |

### 2.4 测试

- **EuiShell**（`EuiShell/tests/`）：`conftest.py`（DummyPlugin 调 `register_slot`）、
  `test_app_smoke.py`、`test_registry.py`、`test_slot_name_sync.py`、
  `test_model_and_progress.py`。
- **KAA**（`tests/kaa/`）：`test_qml_app.py`（仅 sigint，不涉及）；`ui_e2e/` 全套 ——
  `conftest.py` 的 `_FakeShellRegistry` / `_install_production_context`、
  `test_main_smoke.py`（编译 Shell main.qml）、`test_qml_inventory.py`（文件清单 +
  `_shell_props` 注入表）、`NavigationHarness.qml` 及各页面测试。

## 3. 目标 API 设计

### 3.1 新增框架类型（`EuiShell/qml/EuiShell/` 根目录，登记入 qmldir）

```qml
// EuiPageSpec.qml —— Tab 内自定义页面（声明顺序即导航顺序，位于设置页之后、日志页之前）
QtObject {
    property string title        // 侧边导航标题
    property Component source    // 页面组件
}

// EuiFullscreenPageSpec.qml —— 全屏覆盖页（经 NavigationCoordinator 进入）
QtObject {
    property string id           // fullscreenMode 匹配用 id（必填）
    property Component source
}

// EuiSectionSpec.qml —— 设置页 / 偏好页 section
QtObject {
    property string title
    property Component source
}

// EuiLink.qml —— 关于页外链
QtObject {
    property string label
    property string url
}
```

> 与现 `PageSpec` 的差异：去掉 `id`（Tab 页 id 仅用于已废弃的 after 锚点校验，QML 侧
> 从未消费）与 `after`（QML 数组声明顺序天然表达插入位置，kaa 现用
> `after='settings'/'produce'` 的语义由声明顺序等价保留）。

### 3.2 `EuiShellApp.qml`（由 main.qml 改造）—— 扩展点属性表

| 属性 | 类型 | 实例化策略 | 取代现机制 |
|------|------|-----------|-----------|
| `overviewContent` | `Component`（默认 null） | 窗口级 1 份；**null → 总览 Tab 整体隐藏** | `SlotName.OVERVIEW` + `hasOverview()` |
| `titleBarTrailing` | `Component` | 窗口级 1 份（TabStrip 内 Loader） | `SlotName.TITLEBAR_TRAILING` |
| `windowDialogs` | `Component` | 窗口级 1 份（窗口级 Item 内 Loader） | `SlotName.WINDOW_DIALOGS` |
| `controlNotices` | `Component` | 每 Tab 1 份 | `SlotName.CONTROL_NOTICES` |
| `controlRunExtras` | `Component` | 每 Tab 1 份 | `SlotName.CONTROL_RUN_EXTRAS` |
| `controlFooter` | `Component` | 每 Tab 1 份 | `SlotName.CONTROL_FOOTER` |
| `aboutExtra` | `Component` | 每 Tab 1 份 | `SlotName.ABOUT_EXTRA` |
| `pages` | `list<EuiPageSpec>` | 每 Tab 1 份 | `register_page` + `customPagesJson` |
| `fullscreenPages` | `list<EuiFullscreenPageSpec>` | 窗口级 | `register_fullscreen_page` |
| `settingsSections` | `list<EuiSectionSpec>` | 每 Tab 1 份 | `register_settings_section` |
| `preferenceSections` | `list<EuiSectionSpec>` | 窗口级 1 份（偏好页全屏独占） | `register_preference_section` |
| `aboutLinks` | `list<EuiLink>` | 数据（无实例化） | `AboutLink` + `about_links()` + `aboutJson()` |

保留在 Python 侧的元信息（不进入 QML）：`app_name` / `app_version` / `icon_path` ——
QApplication、窗口图标、splash 配置均在 engine 加载之前需要它们。

### 3.3 KAA 的目标 index.qml（`kaa/application/ui/qml/index.qml`）

```qml
import QtQuick
import EuiShell
import "components"
import "dialogs"
import "pages"
import "pages/preferences"
import "pages/sections"
import "slots"

EuiShellApp {
    overviewContent: OverviewSlot { }
    titleBarTrailing: UpdateIndicator { }
    windowDialogs: KaaDialogs { }

    controlNotices: ProduceEngineNotice { }
    controlRunExtras: EndActionRow { }
    controlFooter: ControlFooterExtras { }
    aboutExtra: GameDataVersionRow { }

    pages: [
        EuiPageSpec { title: "方案"; source: ProducePage { } },
        EuiPageSpec { title: "更新"; source: UpdatePage { } }
    ]
    fullscreenPages: [
        EuiFullscreenPageSpec { id: "skillCardBrowser"; source: SkillCardBrowserPage { } }
    ]

    settingsSections: [
        EuiSectionSpec { title: "基本"; source: EmulatorSection { } },
        EuiSectionSpec { title: "日常"; source: DailySection { } },
        EuiSectionSpec { title: "培育"; source: ProduceSection { } },
        EuiSectionSpec { title: "杂项"; source: MiscSection { } }
    ]
    preferenceSections: [
        EuiSectionSpec { title: "启动"; source: InterfaceExtraSection { } },
        EuiSectionSpec { title: "更新"; source: UpdateSection { } },
        EuiSectionSpec { title: "游戏资源"; source: GameDataSection { } },
        EuiSectionSpec { title: "通知"; source: NotifySection { } },
        EuiSectionSpec { title: "快捷键"; source: HotkeysSection { } },
        EuiSectionSpec { title: "数据收集"; source: TelemetrySection { } }
    ]

    aboutLinks: [
        EuiLink { label: "GitHub"; url: "https://github.com/XcantloadX/kotones-auto-assistant" },
        EuiLink { label: "Bilibili"; url: "https://space.bilibili.com/3546853903698457" },
        EuiLink { label: "教程文档"; url: "https://www.kdocs.cn/l/cetCY8mGKHLj" },
        EuiLink { label: "QQ 群"; url: "https://qm.qq.com/q/OI0C3rMmAs" }
    ]
}
```

### 3.4 控制器访问约定（不变）

- 全局控制器：`global_controllers()` 返回的 role → QObject **已逐个注册为 context
  property**（`app.py:149-150`），下游 QML 直接裸名引用（`GameDataCtrl`、
  `ScheduleController` 等）—— 不变。
- Tab 内控制器：slot/页面根元素经注入的 `tab` 访问 `tab.controller(role)` /
  `tab.settingsCtrl` / `tab.runCtrl` —— 不变（kaa 现状即如此，见
  `EndActionRow.qml` / `ControlFooterExtras.qml`）。
- `SlotItemSpec.controllerRole` 机制连同 `SlotHost` 的注入逻辑一并删除（kaa 未使用）。

### 3.5 下游内容根元素契约（新的框架约定，写入 AGENTS.md）

下游组件被框架以 `Loader { sourceComponent: <下游 Component> }` 实例化。Component 的
创建上下文是 **index.qml**（而非挂载点页面），因此 required 属性无法像今天这样经
URL 加载的创建上下文自动解析（现状 `required property var tab` 之所以可用，正是因为
file:// 加载时创建上下文是 ControlPage 所在文档，作用域链上能解析到 `tab`）。新约定：

- 根元素声明**非 required** 的可选注入属性：`property var tab`、`property var
  navigation`、`property var settingsCtrl`、`property var errors` 等；
- 框架 mount 在 `onLoaded` 中按 `hasOwnProperty` 逐个回填（与现 SlotHost 注入
  `controller` 的约定完全同构）；
- 上下文捕获纪律：窗口级声明的对象天然被所有克隆共享（可依赖全局 context property）；
  **per-tab 状态只允许经注入的 `tab` / 控制器获取**，禁止在声明处捕获窗口级有状态对象。

## 4. 详细修改方案

### 4.1 EuiShell Python

**`app.py`（`exec_with`）**

- 删除：`registry = ShellRegistry()`、`registry.set_app_info(...)`、
  `plugin.register(registry)`、`registry.set_global_controllers(...)`、
  `context.setContextProperty('ShellRegistry', registry)`。
- `engine.load(...)` 目标改为 `plugin.entry_qml()`：

  ```python
  entry = plugin.entry_qml()
  engine.load(QUrl.fromLocalFile(str(entry)))
  if not engine.rootObjects():
      raise QmlLoadError(entry)
  ```

- 其余（样式、字体、context properties、win32 装配、启动线程、shutdown）不动。
- import 清理：`ShellRegistry` 等。

**`plugin.py`**

- 删除类型与类：`SlotName`、`PageId`、`AboutLink`、`PageSpec`、`SlotItemSpec`、
  `SlotSpec`、`SectionSpec`、`ShellRegistry`（整个类）。
- `EuiShellPlugin`：删除抽象方法 `register()` 与 `about_links()`；新增抽象方法：

  ```python
  @abstractmethod
  def entry_qml(self) -> Path:
      """返回下游组合根 index.qml 路径；根元素须为 EuiShellApp。"""
  ```

- 保留：`StartupContext` 及全部生命周期钩子、`global_controllers()`、
  `global_dirty_guards()`、会话/后端工厂。`json` import 随 JSON 视图删除。

**`exceptions.py`**：删除 `RegistrationError`（无其他使用方）。

**`paths.py`**：删除无引用的 `qml_url()`；`file_url()`、`QML_DIR`（仍作 EuiShell 模块
import path）、字体路径保留。

**`__init__.py`**：导出改为 `EuiShellPlugin`、`ShellApp`（`ShellRegistry`、`SlotName`
移除；可补充导出 `StartupContext` 方便下游类型标注）。

### 4.2 EuiShell QML

**`main.qml` → `EuiShellApp.qml`（重命名 + 改造）**

根元素 `ApplicationWindow` 不变；新增 §3.2 属性；内部差异逐点：

1. 全屏页列表：由 `ShellRegistry.fullscreenPagesJson()` 改为
   `[内置 preferences（inline component 包装）].concat(root.fullscreenPages)`；delegate
   Loader 改 `sourceComponent: modelData.source`；内置偏好页回填 `prefsCtrl`、下游页回填
   `navigation`（均 `onLoaded`）。
2. 总览页：`visible: root.overviewContent !== null`；SlotHost →
   `Loader { sourceComponent: root.overviewContent; anchors.fill: parent }`。
3. 窗口级对话框 slot：SlotHost → `Loader { sourceComponent: root.windowDialogs }`。
4. TabContent delegate 追加属性透传（见 TabContent 条目）。
5. TitleBar 绑定 `showOverview: root.overviewContent !== null`、
   `titleBarTrailing: root.titleBarTrailing`。
6. `hasOverview` 改为上述派生属性；`tabIndex` 偏移逻辑不变。
7. PreferencesPage（内置全屏页）的 `required property var prefsCtrl` 改为
   `property var prefsCtrl` + mount 处回填。

**`components/TabContent.qml`**

- 删除 `customPages: JSON.parse(ShellRegistry.customPagesJson())`；新增属性（全部带
  默认值——这使 e2e inventory 测试无需注入即可加载）：

  ```qml
  property list<EuiPageSpec> pages: []
  property Component controlNotices: null
  property Component controlRunExtras: null
  property Component controlFooter: null
  property Component aboutExtra: null
  property list<EuiSectionSpec> settingsSections: []
  property list<EuiLink> aboutLinks: []
  ```

- `pageTitles` 改为遍历 `root.pages[i].title`。
- 自定义页 delegate：`Loader { sourceComponent: modelData.source }` + `onLoaded` 回填
  `tab / navigation / fullscreenMode`。
- 转发：ControlPage 收 `controlNotices / controlRunExtras / controlFooter`；SettingsPage
  收 `settingsSections`；AboutPage 收 `aboutExtra / aboutLinks`。

**`components/TabStrip.qml`**：新增 `property Component titleBarTrailing: null`；
`titlebar.trailing` 的 SlotHost → `Loader { sourceComponent: root.titleBarTrailing }`
（保持 Loader 为 RowLayout 直接子项，布局语义与现状一致）。

**`components/TitleBar.qml`**：`showOverview` 保留为属性（由 EuiShellApp 绑定），删除
`ShellRegistry.hasOverview()` 引用；`configManagerDialog` 依赖不变。

**`pages/ControlPage.qml`**：新增三个 `property Component ...: null`；三处 SlotHost →

```qml
Loader {
    sourceComponent: root.controlNotices
    Layout.fillWidth: true
    onLoaded: if (item && item.hasOwnProperty("tab")) item.tab = root.tab
}
```

（行内 runExtras 的 mount 不带 `Layout.fillWidth`，与现状一致。）

**`pages/AboutPage.qml`**：删除 `aboutJson()` 调用；新增 `aboutLinks` / `aboutExtra`
属性；链接 Repeater 改 `model: root.aboutLinks`（`label` / `url` 取属性）；appName /
版本 / 图标仍取自 `splash` context property；`aboutExtra` SlotHost → Loader + 回填 tab。

**`pages/SettingsPage.qml`**：`Component.onCompleted` 中读取 `settingsSectionsJson()`
的逻辑删除，改 `property list<EuiSectionSpec> settingsSections: []`；section delegate
改 `Loader { sourceComponent: modelData.source }` + `onLoaded` 回填
`settingsCtrl / errors / navigation`；**保留**现有 `onErrorsChanged` 时向已加载 section
动态回填 `errors` 的 Connections。

**`pages/PreferencesPage.qml`**：内置外观 section 改为文件内 Component 与
`root.preferenceSections` 拼接；`required property var prefsCtrl` →
`property var prefsCtrl`；delegate 同 SettingsPage。

**删除文件**：`SlotHost.qml`、`SlotName.qml`、`main.qml`（内容并入 EuiShellApp.qml）。

**`qmldir`**：移除 `SlotHost` / `singleton SlotName`；新增 `EuiShellApp`、`EuiPageSpec`、
`EuiFullscreenPageSpec`、`EuiSectionSpec`、`EuiLink` 五个条目。

### 4.3 KAA 侧

**`kaa/application/ui/qml/index.qml`**：新增，内容见 §3.3。

**`kaa/application/ui/plugin.py`**

- 删除：`register()`、`about_links()`、`_qml()`；import 中的 `AboutLink`、`PageSpec`、
  `ShellRegistry`、`SlotItemSpec`、`SlotName`、`SlotSpec`、`SectionSpec`、
  `RegistrationError` 全部移除。
- 新增：

  ```python
  def entry_qml(self) -> Path:
      return QML_DIR / 'index.qml'
  ```

- 其余（元信息、会话工厂、后端、生命周期钩子、全局控制器接线）不动。

**下游 QML 契约调整（`required property var X` → `property var X`）**：

- per-tab slot（3 个）：`EndActionRow.qml`、`ControlFooterExtras.qml`、
  `ProduceEngineNotice.qml`（`tab`）；
- 自定义页（2 个）：`ProducePage.qml`、`UpdatePage.qml`（`tab`）；
- 设置 section（4 个）+ 偏好 section（6 个）：`settingsCtrl` / `prefsCtrl`；
- 其余（`OverviewSlot` / `KaaDialogs` / `GameDataVersionRow` / `UpdateIndicator` /
  `SkillCardBrowserPage`）无契约变化；`UpdateIndicator.qml` 中提及 SlotHost 的注释同步
  修正。

### 4.4 测试改造

**EuiShell（`EuiShell/tests/`）**

| 文件 | 动作 |
|------|------|
| `test_slot_name_sync.py` | **删除**（双语镜像不复存在） |
| `test_registry.py` | **删除**（注册 API 不复存在） |
| `conftest.py` | `DummyPlugin` 删 `register()`，新增 `entry_qml()`：向 `tmp_path` 写入最小 index.qml（`import EuiShell` + `EuiShellApp { }`，带 `overviewContent: Component { Item {} }` 验证总览路径）；移除 `SlotSpec` / `SlotName` import |
| `test_app_smoke.py` | 断言不变（splash ready + 退出码），随 DummyPlugin 自动适配 |
| 新增 `test_shell_app_slots.py` | 定制 index.qml 验证：(a) `overviewContent` 为 null 时总览 Tab 隐藏、非 null 时可见；(b) 打开一个 Tab 后 per-tab slot 组件被实例化（slot 根元素调用 DummyPlugin 提供的计数器 QObject），关闭 Tab 后销毁 |

**KAA（`tests/kaa/`）**

| 文件 | 动作 |
|------|------|
| `ui_e2e/conftest.py` | `_FakeShellRegistry` 类删除；`_install_production_context` 的 objects 表移除 `"ShellRegistry"` 条目；其余 fake（TabManager、splash、控制器等）保留——下游 QML 依赖的全局 context property 全部不变 |
| `ui_e2e/test_main_smoke.py` | 编译目标从 Shell `main.qml` 改为 `EuiShellApp.qml`（standalone 编译检查）+ `kaa/application/ui/qml/index.qml`（真实组合根编译检查） |
| `ui_e2e/test_qml_inventory.py` | `SHELL_QML_ROOTS`：删 `SlotHost.qml` / `SlotName.qml`，增 `EuiShellApp.qml` / 四个 spec 类型；`KAA_QML_ROOTS`：增 `index.qml`；`_shell_props` 无需为新增属性注入（默认值可加载） |
| `ui_e2e/NavigationHarness.qml` 及其余页面/导航/设置/偏好测试 | 不依赖注册制，预期不变；直接构造页面的测试由属性默认值保证可加载 |
| `test_qml_app.py` | 不涉及（sigint 逻辑不动） |

### 4.5 文档

- `EuiShell/README.md`：重写「下游接入总览 / 快速上手」——插件示例删 `register()`、增
  `entry_qml()`；新增 index.qml 示例与扩展点属性表；删除 slot 名称表引用。
- `EuiShell/AGENTS.md`：「下游接入方式」「QML slot 约定」章节按 §3 重写；新增 §3.5 的
  下游内容根元素契约（非 required 注入属性 + 上下文捕获纪律）。
- 根 `AGENTS.md`（KAA）：「UI 系统」章节仍描述 pre-EuiShell 结构（`SettingsPage.qml 由
  sections 子组件组合` 等），顺带同步为 index.qml + KaaPlugin 的事实描述。

## 5. 实施与提交序列

EuiShell 与 kaa 在同一仓库，kaa 是唯一下游，无法在中间态保持全绿地拆出「只改框架」
提交。推荐序列：

1. **Commit 1 — `feat(shell): 新增 EuiShellApp 声明式扩展点类型`**
   仅新增文件：`EuiShellApp.qml`（暂为 main.qml 的复制 + 扩展点属性 + 属性化 mounts）、
   4 个 spec 类型、qmldir 追加、`EuiShellPlugin.entry_qml()` 抽象方法 +
   `DummyPlugin` 适配。此提交结束时注册制仍在运行（main.qml 仍被加载），全部检查通过。

2. **Commit 2 — `refactor(shell): 切换组合根至下游 index.qml 并移除注册制`**
   - `app.py` 加载 `plugin.entry_qml()`、删除 ShellRegistry 装配；
   - `plugin.py` / `exceptions.py` / `paths.py` / `__init__.py` 按 §4.1 清理；
   - `main.qml` / `SlotHost.qml` / `SlotName.qml` 删除；TabContent / TabStrip /
     TitleBar / ControlPage / AboutPage / SettingsPage / PreferencesPage 按 §4.2 改造；
   - KAA：新增 index.qml、plugin.py 精简、15 个 QML 文件契约调整；
   - 两侧测试按 §4.4 更新。
   此提交完成功能等价迁移，`ruff` / `pyright` / `pytest`（两仓）全绿。

3. **Commit 3 — `docs(shell): 更新 README 与 AGENTS.md 的接入约定`**（§4.5）。

> 若希望 review 粒度更细，Commit 2 可拆为 (a) EuiShell QML + kaa QML 迁移、
> (b) EuiShell Python 清理两步，但 (a) 结束时 Python 注册代码已无调用方、(b) 结束时才
> 恢复全绿，需在提交说明中注明中间态状态。

## 6. 风险与实施注意点

1. **Component 隐式包装**：`source: ProducePage { }`（对象字面量赋给 `property
   Component`）依赖 Qt 的隐式 Component 包装，与 `Control.contentItem` / delegate 是
   同一机制（Qt 6 全系支持）。个别场景若显式 `source: Component { ... }` 更清晰，允许
   混用。
2. **required → 非 required 的根因**要写进 AGENTS.md（§3.5），避免后续贡献者把
   `property var tab` 改回 required 导致运行期 "Required property was not initialized"。
3. **布局语义**：mount Loader 直接作为布局子项（替换 SlotHost 的 Repeater 位置），
   Loader 以内容 implicit size 参与 RowLayout/ColumnLayout——与现状逐点一致；下游根
   元素上的 Layout attached 属性现状即不生效（挂在 Loader 内层），不做行为变更。
4. **errors 动态回填**：SettingsPage 的校验错误分发依赖 `onErrorsChanged` 时向已加载
   section 回填 `errors`，迁移后必须保留该 Connections（Loader 重建时经 `onLoaded`
   重新注入当前值）。
5. **全屏页 id**：`EuiFullscreenPageSpec.id` 与 `window.fullscreenMode` 字符串匹配
   （kaa 用 `skillCardBrowser`，内置 `preferences`）——迁移时逐字保留。
6. **离屏平台**：EuiShellApp.qml 的 win32 分支逻辑（`flags` 按 `Qt.platform.os`）照搬
   自 main.qml，`offscreen` 测试路径不受影响。
7. **app 元信息时序**：`app_name` / `icon_path` / `app_version` 留在 Python 的原因
   （QApplication 图标、`splash.configure` 均先于 engine 加载）写入 README，防止后续
   把它们搬进 QML 属性。
8. **后续可选（非本次范围）**：下游 index.qml 与 EuiShell 模块接入 qmlcachegen /
   qmlsc AOT 编译，把属性类型检查前移到构建期。

## 7. 验证清单

每个提交执行：

```bash
# EuiShell
cd EuiShell && uv run ruff check src tests && uv run pyright src tests && uv run pytest

# KAA
uv run ruff check kaa tests && uv run pyright kaa tests && uv run pytest tests/kaa
```

手工冒烟（win32 实机）：

- [ ] 启动 → Splash（游戏数据更新流程）→ 主界面；
- [ ] 总览页可见（OverviewSlot + 配置/调度对话框可用）；index.qml 临时移除
      `overviewContent` 时总览 Tab 隐藏；
- [ ] 打开 ≥2 个 Tab：控制页通知 / 行内附加控件 / 页脚在**每个 Tab 各一份**且控制器
      随 Tab 隔离（`EndActionRow` 写入各自 profile 的配置）；
- [ ] 设置页 4 个 section 切换、校验错误内联展示与保存流程；
- [ ] 偏好页外观 section 置首 + 6 个下游 section，保存后主题实时生效；
- [ ] 方案 / 更新自定义 Tab 页、卡片图鉴全屏页进入与返回；
- [ ] 标题栏更新指示器、关于页外链与游戏数据版本行；
- [ ] 更新日志 / 配置迁移 / 遥测同意弹窗（window.dialogs + splash 信号）；
- [ ] 多 Tab 关闭 / 批量运行 / 未保存更改守卫不回归。
