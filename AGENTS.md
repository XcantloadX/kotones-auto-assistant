# AGENTS.md

## 项目概述

Kotones Auto Assistant (ksaa, 琴音小助手) — 《学园偶像大师》(学マス) 自动化脚本。
Python 3.10, PySide6 QML 桌面 UI, Pydantic 配置管理。

## 配置系统

两种配置类型，不要搞混：

**SharedConfig** — 跨 profile 共享，存储在 `conf/_shared.json`
- 数据模型：`kaa/config/shared.py` → `SharedMiscConfig`
- 读取：`config_manager.read_shared()`
- 写入：`config_manager.write_shared(shared)`
- QML 绑定用 `mutateSharedMisc()`（自动写入 `_shared.json`）

**KaaConfig (Profile)** — 每个 profile 独立，存储在 `conf/profiles/{名称}.json`
- 数据模型：`kaa/config/schema.py` → `KaaConfig`
- 运行时访问：`conf()` （来自 `kaa_context`）
- QML 绑定用 `mutateConfig()`（自动写入 profile json）

## UI 系统

UI 基于 EuiShell 框架（同仓 `EuiShell/`，框架约定见其 `AGENTS.md`）。KAA 通过 `KaaPlugin`
（`kaa/application/ui/plugin.py`）接入，`ShellApp(plugin).run()` 启动；组合根为
`kaa/application/ui/qml/index.qml`（根元素 `EuiShellApp`），以 QML 扩展点属性声明插槽内容：
总览、标题栏指示器、窗口对话框、控制页附加、自定义页、全屏页、设置/偏好 section、关于页外链。

KAA 自身 QML 文件在 `kaa/application/ui/qml/`：
- `index.qml` → EuiShell 组合根，声明全部插槽内容
- `pages/ProducePage.qml` → 培育方案管理（自定义页）
- `pages/UpdatePage.qml` → 版本更新页（自定义页）
- `pages/SkillCardBrowserPage.qml` → 技能卡图鉴（全屏页）
- `pages/OverviewPage.qml` → 总览页（经 `slots/OverviewSlot.qml` 挂入总览插槽）
- `pages/sections/` → 设置页 section（基本/日常/培育/杂项）
- `pages/preferences/` → 偏好页 section（偏好页全屏独占，外观 section 由框架内置）
- `slots/` → 各扩展点插槽组件（窗口对话框、控制页通知/运行附加/底部、关于页附加）
- `components/` → 通用组件（`UpdateIndicator.qml` 标题栏更新指示器等）
- `dialogs/` → 窗口级对话框

Controllers 在 `kaa/application/ui/controllers/`（Tab 生命周期由框架 TabManager 管理）：
- `settings_controller.py` → 设置页配置草稿桥接
- `produce_controller.py` → 培育方案 CRUD
- `preferences_controller.py` → 偏好（SharedConfig）草稿控制器
- `shared_settings_controller.py` → 共享配置即时写盘桥接
- `control_controller.py` → 完成后操作（关机/休眠）即时配置桥接
- `update_controller.py` → 版本更新控制（后台线程加载版本信息）
- `game_data_controller.py` → 游戏数据后台更新检查
- `schedule_controller.py` → 定时任务管理桥接（全局上下文属性）
- `feedback_controller.py` → 反馈报告控制器
- `skill_card_browser_controller.py` → 技能卡图鉴数据桥接（按需分页）
- `debug_inspector_controller.py` → 游戏数据库原始数据查看（QB 桥接）
- `telemetry_consent_controller.py` → 匿名错误上报同意弹窗桥接

## 游戏数据更新系统

核心逻辑在 `kaa/game_data/updater.py` 的 `GameDataUpdater.check_and_update()`。
触发方式：
1. QML 启动时 → `KaaSplashBridge` 后台线程自动调用
2. 设置页手动检查 → `SettingsController.checkGameDataAsync()`
下载路径：`resources/game_data/{game.db, idol_cards/, skill_cards/, drinks/, version.txt}`

## 配置迁移系统

配置版本用于管理存量 config JSON 的向后兼容升级。

**版本号定义**（两个地方必须一致）：
- `kaa/config/schema.py` → `CONFIG_VERSION_CODE`（新建 profile 的默认版本）
- `kaa/config/migrations.py` → `LATEST_VERSION`（迁移链的目标版本）

**迁移基础设施**（`kaa/config/migration.py`）：
- `MigrationStep` — 抽象基类，实现 `check_needed()` 和 `apply()`
- `MigrationChain` — 按序执行多个 `MigrationStep`
- `MigrationMessage` — 记录每条迁移的文本说明，通过 `add_deferred_messages()` 延迟展示给 GUI

**迁移步骤**在 `kaa/config/migrations.py` 中实现，追加到 `profile_migration_chain` 末尾。

**触发时机**：
1. 应用启动时 → `kaa/main/kaa.py` 的 `upgrade_config()` 主动调用
2. 首次读取 profile 时 → `kaa/config/manager.py` 的 `_ensure_migrated()` 惰性触发

## 目录结构速查

- `kaa/config/` — 配置模型 (shared, schema, manager, base_config, produce, migration, migrations)
- `kaa/tasks/` — 自动化任务（daily, produce, actions）
- `kaa/application/ui/qml/` — KAA QML（`index.qml` 组合根 + 页面/section/slot/组件）
- `kaa/application/ui/plugin.py` — KaaPlugin，KAA 对 EuiShell 的插件实现
- `kaa/application/ui/controllers/` — Qt 控制器 (settings, produce, preferences, shared_settings, control, update, game_data, schedule, feedback, skill_card_browser, debug_inspector, telemetry_consent)
- `kaa/application/services/` — 服务层 (config, task, update, feedback)
- `kaa/game_data/` — 游戏数据管理 (updater, manifest, paths)
- `kaa/main/` — 入口 (cli, kaa, qml_app)
