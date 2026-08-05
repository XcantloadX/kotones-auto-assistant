# KAA UI 迁移计划：Gradio → QML

## 目标

将 KAA 现有的 Gradio Web UI 完全替换为 QML 原生 UI，并向 IAA 抽象出的框架模式对齐，为后续迁移至共用框架做准备。

**约束条件：**
- UI 逻辑完全放在 QML 层，不使用 IAA 中的 Python DSL 模式
- QML 持有完整的配置数据作为本地 JS 对象，仅在读取/提交时与 Python 交换完整 JSON
- Python 侧不为每个字段单独暴露 Slot，无字段感知
- Python Slot 只用于 QML 无法完成的副作用：平台 SDK 调用、磁盘 I/O、异步耗时操作

---

## 架构原则

### Python ↔ QML 数据边界

```
QML 本地状态（JS 对象）
    ↕  configJson()        读：初始化时拉取一次完整快照
    ↕  saveConfig(json)    写：提交时发送完整对象

只有以下情况才需要额外 Slot：
  - 枚举模拟器多开实例（调平台 SDK）
  - 异步耗时操作（版本检查、游戏资源检查）
  - 文件系统副作用（导出日志、保存反馈报告）
```

### Controller 职责

每个 Controller 是一个 `QObject`，职责单一，通过 `TabManager` 按 profile 索引分配给对应的 `TabContent.qml`。

---

## Phase 0 — 解耦 `KaaSession`

**目标：** 将「Kaa + KaaFacade 生命周期」从「Gradio 挂载」中切开，作为所有后续 Controller 的基础依赖。

### 新建 `kaa/application/ui/kaa_session.py`

```python
class KaaSession:
    def __init__(self, profile_name: str) -> None

    def initialize(self) -> None
    # 创建 Kaa(profile_name) + KaaFacade(kaa, profile_name)
    # 原 ProfileRunner.mount() 的前半段

    def destroy(self) -> None
    # kaa.stop() + 清空引用
    # 原 ProfileRunner.unmount() 的核心

    @property def profile_name(self) -> str
    @property def kaa(self) -> Kaa | None
    @property def facade(self) -> KaaFacade | None
    @property def is_running(self) -> bool
    # → facade.task_service.is_running()，加 ContextNotInitializedError 保护
```

### 修改 `profile_runner.py`

- 构造参数改为接受 `KaaSession`，不再自建 Kaa
- `mount()` 改为：调 `session.initialize()`（如果还没初始化），再创建 `gr.Blocks`，再挂 FastAPI
- `unmount()` 只清理 Blocks，不再负责 Kaa 生命周期

### 修改 `tab_manager.py`

```python
@dataclass
class _TabEntry:
    session: KaaSession
    runner: ProfileRunner | None = None   # 过渡期保留

    @property def config_name(self) -> str: return self.session.profile_name
    @property def is_running(self) -> bool: return self.session.is_running
```

`_create_entry()` 先建 `KaaSession`，再可选建 `ProfileRunner`。`_destroy_entry()` 统一调 `session.destroy()`。

---

## Phase 1 — `RunController`

**目标：** 用 QObject 包装 `KaaFacade.task_service`，替换 Gradio 的 `gr.Timer` 轮询，让 QML 直接绑定任务运行状态。

### 新建 `kaa/application/ui/controllers/run_controller.py`

```python
class RunController(QObject):
    stateChanged = Signal()
    tasksChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
```

### Qt Properties（300ms QTimer 驱动 `stateChanged`）

| Property | 来源 |
|---|---|
| `running: bool` | `task_service.is_running()` |
| `isStopping: bool` | `task_service.is_stopping` |
| `isPaused: bool` | `task_service.get_pause_status() is True` |
| `currentTaskName: str` | 遍历 `get_task_statuses()` 找第一个 `'running'` |

### Slots

```python
# 运行控制
@Slot() def start(self)
@Slot() def stop(self)
@Slot() def togglePause(self)
@Slot(str) def runTask(self, name: str)

# 数据查询（QML 按需调用）
@Slot(result=str)
def tasksJson(self) -> str
# → [{"name": "商店购买", "path": "tasks.purchase.enabled",
#      "enabled": true, "status": "pending"}, ...]
# status ∈ {"pending", "running", "done", "error"}

# 批量开关（通用 dot_path 写法，避免逐任务暴露 Slot）
@Slot(str, bool) def setTaskEnabled(self, dot_path: str, enabled: bool)
@Slot(bool) def selectAllTasks(self, value: bool)
@Slot() def selectOnlyProduce(self)

# 完成后动作
@Slot(str) def setEndAction(self, action: str)
# action ∈ {"nothing", "shutdown", "hibernate"}
```

### TabManager 扩展

```python
@dataclass
class _TabEntry:
    session: KaaSession
    run_ctrl: RunController
    runner: ProfileRunner | None = None

@Slot(int, result=QObject)
def runCtrlAt(self, index: int) -> RunController | None
```

---

## Phase 2 — `ControlPage.qml` + 重构 `TabContent.qml`

**目标：** 删除 `main.qml` 中的 `WebEngineView` 和 JavaScript tab 切换，改为真实 QML 页面。

### 修改 `main.qml`

删除整个 `WebEngineView` + `SideNavigationBar` JS 交互块，改为：

```qml
Repeater {
    model: window.tabList
    delegate: TabContent {
        required property int index
        runCtrl: TabManager.runCtrlAt(index)
        // settingsCtrl: TabManager.settingsCtrlAt(index)  ← Phase 3 填入
    }
}
```

Splash 条件改为布尔 `splash.ready` 信号，不再依赖 `splash.gradioUrl`。

### 重写 `kaa/application/ui/qml/components/TabContent.qml`

```qml
Item {
    id: root
    required property var runCtrl
    property var settingsCtrl: null
    property var produceCtrl: null

    RowLayout {
        anchors.fill: parent; spacing: 0

        SideNavigationBar {
            id: sideNav
            Layout.fillHeight: true
            model: ["控制", "设置", "方案", "更新", "反馈"]
        }

        StackLayout {
            currentIndex: sideNav.currentIndex

            ControlPage  { runCtrl: root.runCtrl }
            SettingsPage { settingsCtrl: root.settingsCtrl }
            ProducePage  { produceCtrl: root.produceCtrl }
            UpdatePage   {}
            FeedbackPage {}
        }
    }
}
```

### 新建 `kaa/application/ui/qml/pages/ControlPage.qml`

```qml
PageContainer {
    id: root
    required property var runCtrl

    readonly property bool ctrl_running:  runCtrl?.running   ?? false
    readonly property bool ctrl_stopping: runCtrl?.isStopping ?? false
    readonly property bool ctrl_paused:   runCtrl?.isPaused  ?? false
    readonly property string ctrl_task:   runCtrl?.currentTaskName ?? ""

    property var tasks: []
    function reloadTasks() { tasks = runCtrl ? JSON.parse(runCtrl.tasksJson()) : [] }

    Component.onCompleted: reloadTasks()
    Connections { target: runCtrl; function onTasksChanged() { reloadTasks() } }
    Connections { target: runCtrl; function onStateChanged() { reloadTasks() } }

    ColumnLayout {
        anchors.fill: parent; spacing: 12

        // 运行控制
        GroupBox {
            title: "运行控制"; Layout.fillWidth: true
            RowLayout {
                Button {
                    text: ctrl_running ? (ctrl_stopping ? "停止中..." : "停止") : "启动"
                    highlighted: !ctrl_running
                    enabled: !ctrl_stopping
                    onClicked: ctrl_running ? runCtrl.stop() : runCtrl.start()
                }
                Button {
                    text: ctrl_paused ? "恢复" : "暂停"
                    enabled: ctrl_running && !ctrl_stopping
                    onClicked: runCtrl.togglePause()
                }
                ComboBox {
                    model: ["完成后什么都不做", "完成后关机", "完成后休眠"]
                    onActivated: runCtrl.setEndAction(
                        ["nothing", "shutdown", "hibernate"][currentIndex])
                }
                Item { Layout.fillWidth: true }
                Label { text: ctrl_task ? "正在执行: " + ctrl_task : "" }
            }
        }

        // 快速任务开关
        GroupBox {
            title: "快速设置"; Layout.fillWidth: true
            ColumnLayout {
                RowLayout {
                    Button { text: "全选";   onClicked: runCtrl.selectAllTasks(true) }
                    Button { text: "清空";   onClicked: runCtrl.selectAllTasks(false) }
                    Button { text: "只选培育"; onClicked: runCtrl.selectOnlyProduce() }
                }
                Flow {
                    spacing: 8; Layout.fillWidth: true
                    Repeater {
                        model: root.tasks
                        CheckBox {
                            text: modelData.name
                            checked: modelData.enabled
                            onToggled: runCtrl.setTaskEnabled(modelData.path, checked)
                        }
                    }
                }
            }
        }

        // 任务状态列表
        GroupBox {
            title: "任务状态"; Layout.fillWidth: true; Layout.fillHeight: true
            ListView {
                anchors.fill: parent; clip: true
                model: root.tasks
                delegate: ItemDelegate {
                    width: parent.width
                    contentItem: RowLayout {
                        Label { text: modelData.name; Layout.fillWidth: true }
                        Label {
                            text: ({ pending: "等待", running: "运行中",
                                      done: "完成", error: "出错" })[modelData.status]
                                  ?? modelData.status
                        }
                    }
                }
            }
        }
    }
}
```

---

## Phase 3 — `SettingsController` + `SettingsPage.qml`

**目标：** QML 持有完整 config 对象，自由编辑，提交时发回 Python 写盘。Python 侧无字段感知。

### 新建 `kaa/application/ui/controllers/settings_controller.py`

```python
class SettingsController(QObject):
    configChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    # 核心读写（唯二的数据 Slots）

    @Slot(result=str)
    def configJson(self) -> str:
        """返回完整 config 快照。
        结构：
        {
          "profile":  {...},   # user_config（含 backend）
          "options":  {...},   # get_options() 的 Pydantic model_dump
          "shared":   {...}    # 全局 shared 配置中与该 profile 相关部分
        }
        直接用 Pydantic model_dump(mode='json')，不做二次转换。
        """

    @Slot(str, result=bool)
    def saveConfig(self, json_str: str) -> bool:
        """接收完整 config JSON，Pydantic 校验后写盘。
        校验失败时 emit operationFailed，返回 False。
        """

    # Python-only 副作用 Slots

    @Slot(str)
    def listEmulatorInstancesAsync(self, emulator_type: str) -> None:
        """后台线程枚举多开实例（调平台 SDK），完成后 emit emulatorInstancesReady。"""

    emulatorInstancesReady = Signal(str, str)
    # (emulator_type, json)  json = [{"id": 0, "name": "MuMu-0"}, ...]

    @Slot()
    def checkGameDataAsync(self) -> None:
        """触发游戏资源检查，流式 emit gameDataProgress。"""

    gameDataProgress = Signal(str)
    gameDataDone = Signal()

    @Slot()
    def resetGameWindow(self) -> None
```

### QML 侧联动规则（纯 JS，无需 Python）

模拟器类型切换时的多字段联动完全在 QML 中处理：

```qml
readonly property var validScreenshotMethods: ({
    mumu12:    ["nemu_ipc", "adb", "uiautomator2"],
    mumu12v5:  ["nemu_ipc", "adb", "uiautomator2"],
    leidian:   ["adb", "uiautomator2"],
    custom:    ["adb", "uiautomator2"],
    dmm:       ["windows_native", "windows_background", "windows"],
    playcover: ["macos"]
})

function onEmulatorTypeSelected(type) {
    cfg.profile.backend.lifecycle.type = type
    var valid = validScreenshotMethods[type]
    if (!valid.includes(cfg.profile.backend.screenshot_impl))
        cfg.profile.backend.screenshot_impl = valid[0]
    modified()
    settingsCtrl.listEmulatorInstancesAsync(type)   // 仅实例枚举需要 Python
}
```

### 新建 `kaa/application/ui/qml/pages/SettingsPage.qml`

```qml
PageContainer {
    id: root
    required property var settingsCtrl

    property var cfg: ({})
    property bool dirty: false

    function load() { cfg = JSON.parse(settingsCtrl.configJson()); dirty = false }
    function save() { if (settingsCtrl.saveConfig(JSON.stringify(cfg))) dirty = false }

    Component.onCompleted: load()
    Connections { target: settingsCtrl; function onConfigChanged() { load() } }

    ColumnLayout {
        // 未保存提示条
        Pane {
            visible: root.dirty; Layout.fillWidth: true
            RowLayout {
                Label { text: "有未保存的更改"; Layout.fillWidth: true }
                Button { text: "保存"; onClicked: root.save() }
                Button { text: "放弃"; onClicked: root.load() }
            }
        }

        TabBar {
            id: settingsTabs
            TabButton { text: "基本" }    // 模拟器 + 启动/结束游戏
            TabButton { text: "日常" }    // 商店 / 工作 / 竞赛 / 奖励
            TabButton { text: "培育" }    // 当前使用哪个方案等
            TabButton { text: "杂项" }    // idle / debug / shared 设置
        }

        StackLayout {
            currentIndex: settingsTabs.currentIndex
            EmulatorSection { cfg: root.cfg; onModified: root.markDirty(); settingsCtrl: root.settingsCtrl }
            DailySection    { cfg: root.cfg; onModified: root.markDirty() }
            ProduceSection  { cfg: root.cfg; onModified: root.markDirty() }
            MiscSection     { cfg: root.cfg; onModified: root.markDirty(); settingsCtrl: root.settingsCtrl }
        }
    }
}
```

### TabManager 扩展

```python
@dataclass
class _TabEntry:
    session: KaaSession
    run_ctrl: RunController
    settings_ctrl: SettingsController
    runner: ProfileRunner | None = None

@Slot(int, result=QObject)
def settingsCtrlAt(self, index: int) -> SettingsController | None
```

---

## Phase 4 — `ProgressBridge` + `LogBridge`

**目标：** 替换 Gradio 的 `gr.Timer` 状态轮询，进度和日志实时推送到 QML。

### 新建 `kaa/application/ui/controllers/progress_bridge.py`

```python
class ProgressBridge(QObject):
    changed = Signal()

    statusText      = Property(str, ..., notify=changed)
    progressPercent = Property(int, ..., notify=changed)   # 0–100
    lastErrorText   = Property(str, ..., notify=changed)
```

接入方式：`KaaSession.initialize()` 之后向 `kaa.events.task_status_changed` 注册回调（该事件在 `TaskService` 中已存在）。注意回调在子线程触发，需用 `QMetaObject.invokeMethod` 切换到 Qt 主线程。

### 新建 `kaa/application/ui/controllers/log_bridge.py`

```python
class LogBridge(QObject):
    newLine = Signal(str)   # 每条日志行 emit 一次，QML append 到 ListView

    def install(self) -> None
    # 注册 logging.Handler，捕获日志后 emit newLine
    # 子线程安全：通过 Qt.QueuedConnection 切换线程
```

### `_TabEntry` 最终形态（此阶段）

```python
@dataclass
class _TabEntry:
    session: KaaSession
    run_ctrl: RunController
    settings_ctrl: SettingsController
    progress_bridge: ProgressBridge
    log_bridge: LogBridge
    runner: ProfileRunner | None = None
```

### TabManager 新增

```python
@Slot(int, result=QObject) def progressBridgeAt(self, index) -> ProgressBridge | None
@Slot(int, result=QObject) def logBridgeAt(self, index) -> LogBridge | None
```

### `TabContent.qml` 完整 property 列表

```qml
required property var runCtrl
required property var settingsCtrl
required property var progressCtrl     // ProgressBridge
required property var logBridge
property var produceCtrl: null         // Phase 5
```

---

## Phase 5 — `ProduceController` + `ProducePage.qml`

**目标：** 培育方案的 CRUD，数据层只做 JSON 传输。

### 新建 `kaa/application/ui/controllers/produce_controller.py`

```python
class ProduceController(QObject):
    solutionsChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    # 方案列表
    @Slot(result=str)
    def solutionsJson(self) -> str
    # → [{"id": "...", "name": "...", "description": "..."}, ...]

    # 单方案读写
    @Slot(str, result=str)
    def solutionJson(self, solution_id: str) -> str
    # → 完整 ProduceSolution 的 model_dump(mode='json')

    @Slot(str, result=bool)
    def saveSolution(self, json_str: str) -> bool
    # 接收完整 ProduceSolution JSON（含 id），写盘，emit solutionsChanged

    # CRUD
    @Slot(str, result=str)
    def createSolution(self, name: str) -> str
    # 创建新方案，返回新方案的完整 JSON，emit solutionsChanged

    @Slot(str, result=bool)
    def deleteSolution(self, solution_id: str) -> bool

    # 静态枚举数据（初始化一次，QML 缓存）
    @Slot(result=str)
    def idolCardsJson(self) -> str
    # → [{"skin_id": "...", "name": "...", "another_name": "...", "is_another": bool}, ...]

    @Slot(result=str)
    def produceActionsJson(self) -> str
    # → [{"value": "...", "display_name": "..."}, ...]

    @Slot(result=str)
    def detectModesJson(self) -> str
    # → [{"value": "...", "display_name": "..."}, ...]
```

### `ProducePage.qml` 数据流

```qml
PageContainer {
    required property var produceCtrl

    property var solutions: []
    property var currentSolution: null   // 完整 solution 对象副本
    property bool dirty: false

    function loadSolutions() { solutions = JSON.parse(produceCtrl.solutionsJson()) }
    function selectSolution(id) {
        currentSolution = JSON.parse(produceCtrl.solutionJson(id))
        dirty = false
    }
    function save() {
        if (produceCtrl.saveSolution(JSON.stringify(currentSolution)))
            dirty = false
    }

    // 左侧方案列表 + 右侧编辑表单
    // 表单直接读写 currentSolution.data.*，改动时 dirty = true
}
```

---

## Phase 6 — `UpdateController` + `FeedbackController`

### 新建 `kaa/application/ui/controllers/update_controller.py`

```python
class UpdateController(QObject):
    versionsLoaded = Signal(str)   # JSON {installed, latest, launcher, versions:[...]}
    loadFailed = Signal(str)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    @Slot() def loadVersionsAsync(self) -> None
    # 后台线程调 update_service.list_remote_versions()，完成后 emit versionsLoaded

    @Slot(str) def installVersion(self, version: str) -> None

    @Slot(result=str) def changelogText(self) -> str
    # 从 kaa.metadata.CHANGELOG 读取
```

### 新建 `kaa/application/ui/controllers/feedback_controller.py`

```python
class FeedbackController(QObject):
    reportProgress = Signal(str, float)   # (description, 0.0–1.0)
    reportDone = Signal(str)
    reportFailed = Signal(str)

    @Slot(str, str, bool)
    def submitReport(self, title: str, description: str, upload: bool) -> None
    # 后台线程调 feedback_service.report(...)，通过 on_progress 回调 emit reportProgress

    @Slot(result=str)
    def exportLogsZip(self) -> str
    # 调 facade.export_logs_as_zip()，返回文件路径
```

---

## Phase 7 — 删除 Gradio 层

**前置条件：** 所有 6 个页面的 QML 实现全部完成并验证可用。

### 删除顺序（避免 import 报错）

1. `kaa/application/ui/views/` 下全部 View 文件
2. `kaa/application/ui/gradio_view.py`
3. `kaa/application/ui/common.py`（`GradioComponents` 等）
4. `kaa/application/ui/profile_runner.py`
5. `kaa/main/gr.py`
6. `tab_manager.py` 中所有 `runner`、`mount_path`、`FastAPI`、`gradioUrlAt` 相关代码
7. `main.qml` 中残余的 `splash.gradioUrl` 条件、`WebEngineView` import
8. `index.py` 中的 FastAPI 服务器启动代码
9. `pyproject.toml` 移除 `gradio`、`fastapi`、`uvicorn`；`PySide6-QtWebEngine` 也可移除

---

## 文件变更总览

| 操作 | 文件 | Phase |
|---|---|---|
| 新建 | `kaa/application/ui/kaa_session.py` | 0 |
| 改造 | `kaa/application/ui/profile_runner.py` | 0 |
| 改造 | `kaa/application/ui/tab_manager.py` | 0、1、3、4、5 |
| 新建 | `kaa/application/ui/controllers/run_controller.py` | 1 |
| 重写 | `kaa/application/ui/qml/components/TabContent.qml` | 2 |
| 新建 | `kaa/application/ui/qml/pages/ControlPage.qml` | 2 |
| 修改 | `kaa/application/ui/qml/main.qml` | 2 |
| 新建 | `kaa/application/ui/controllers/settings_controller.py` | 3 |
| 新建 | `kaa/application/ui/qml/pages/SettingsPage.qml` | 3 |
| 新建 | `kaa/application/ui/qml/pages/sections/EmulatorSection.qml` 等 | 3 |
| 新建 | `kaa/application/ui/controllers/progress_bridge.py` | 4 |
| 新建 | `kaa/application/ui/controllers/log_bridge.py` | 4 |
| 新建 | `kaa/application/ui/controllers/produce_controller.py` | 5 |
| 新建 | `kaa/application/ui/qml/pages/ProducePage.qml` | 5 |
| 新建 | `kaa/application/ui/controllers/update_controller.py` | 6 |
| 新建 | `kaa/application/ui/controllers/feedback_controller.py` | 6 |
| 新建 | `kaa/application/ui/qml/pages/UpdatePage.qml` | 6 |
| 新建 | `kaa/application/ui/qml/pages/FeedbackPage.qml` | 6 |
| 删除 | `kaa/application/ui/views/*`、`gradio_view.py`、`common.py`、`profile_runner.py` 等 | 7 |
