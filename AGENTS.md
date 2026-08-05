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

PySide6 QML 桌面 UI，QML 文件在 `kaa/application/ui/qml/`：
- `pages/SettingsPage.qml` → 设置页（由 sections 子组件组合）
- `pages/ProducePage.qml` → 培育方案管理
- `pages/FeedbackPage.qml` → 反馈页
- `components/TabStrip.qml` → 多 Profile Tab 栏

Controllers 在 `kaa/application/ui/controllers/`：
- `tab_manager.py` → 多 Profile Tab 生命周期管理
- `run_controller.py` → 任务运行状态桥接
- `settings_controller.py` → 设置页数据桥接
- `produce_controller.py` → 培育方案 CRUD

## 游戏数据更新系统

核心逻辑在 `kaa/game_data/updater.py` 的 `GameDataUpdater.check_and_update()`。
触发方式：
1. QML 启动时 → `_SplashBridge` 后台线程自动调用
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
- `kaa/application/ui/qml/` — QML 页面和组件
- `kaa/application/ui/controllers/` — Qt 控制器 (tab_manager, run_controller, settings_controller, produce_controller)
- `kaa/application/ui/facade.py` — UI 与服务的桥梁
- `kaa/application/services/` — 服务层 (config, task, update, feedback)
- `kaa/game_data/` — 游戏数据管理 (updater, manifest, paths)
- `kaa/main/` — 入口 (cli, kaa, qml_app)
