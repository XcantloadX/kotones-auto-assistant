# AGENTS.md

## 项目概述

Kotones Auto Assistant (ksaa, 琴音小助手) — 《学园偶像大师》(学マス) 自动化脚本。
Python 3.10, Gradio Web UI + PySide6 QML 桌面壳, Pydantic 配置管理。

## 配置系统

两种配置类型，不要搞混：

**SharedConfig** — 跨 profile 共享，存储在 `conf/_shared.json`
- 数据模型：`kaa/config/shared.py` → `SharedMiscConfig`
- 读取：`config_manager.read_shared()`
- 写入：`config_manager.write_shared(shared)`
- UI 绑定用 `_bind_shared()`（自动写入 `_shared.json`），**不用** `_bind()`

**KaaConfig (Profile)** — 每个 profile 独立，存储在 `conf/profiles/{名称}.json`
- 数据模型：`kaa/config/schema.py` → `KaaConfig`
- 运行时访问：`conf()` （来自 `kaa_context`）
- UI 绑定用 `_bind()`（自动写入 profile json）

## UI 系统

Gradio Web UI，视图在 `kaa/application/ui/views/`：
- `settings_view.py` → 设置页（6 个 Tab：基本/日常/培育/杂项/闲置/调试）
- `produce_view.py` → 培育方案管理
- `status_view.py` → 状态页
- `task_view.py` → 任务页
- `update_view.py` → 更新页

组件绑定：
- `_bind(component, ref)` → 绑定到 Profile config
- `_bind_shared(component, ref, shared_getter)` → 绑定到 SharedConfig
- 都用 `ref(of(obj).field)` 创建 Ref，不要直接操作配置对象

## 游戏数据更新系统

核心逻辑在 `kaa/game_data/updater.py` 的 `GameDataUpdater.check_and_update()`。
触发方式：
1. QML 启动时 → `_StartupWorker` 后台线程自动调用
2. Gradio 手动检查 → `facade.check_game_data()` 流式输出到 Textbox
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

**当前版本历史**：

| 从 | 到 | 步骤 | 内容 |
|---|---|---|---|
| V1 | V2 | ProfileV1ToV2 | 偶像字符串列表 → 整数枚举 |
| V2 | V3 | ProfileV2ToV3 | 整数枚举 → skin_id 字符串 |
| V3 | V4 | ProfileV3ToV4 | 修正游戏包名拼写（`bandinamcoent` → `bandainamcoent`） |
| V4 | V5 | ProfileV4ToV5 | windows/remote_windows 截图方式 → backend.type='dmm' |
| V5 | V6 | ProfileV5ToV6 | 培育参数 → ProduceSolution 独立文件 |
| V6 | V7 | ProfileV6ToV7 | adb_raw 截图方式 → adb |
| V7 | V8 | ProfileV7ToV8 | 单文件 → 多文件（`conf/profiles/*.json` + `conf/_shared.json`） |
| — | — | SharedV1ToV2 | `conf/telemetry` 文件 → `_shared.json.telemetry.sentry` |
| V8 | V9 | ProfileV8ToV9 | backend 平铺 → lifecycle/connection 嵌套；任务配置收拢到 tasks |
| V9 | V10 | ProfileV9ToV10 | DMM 截图方式 windows → windows_native |
| V10 | V11 | ProfileV10ToV11 | 移除 4 个已改硬编码的配置字段 |

## 目录结构速查

- `kaa/config/` — 配置模型 (shared, schema, manager, base_config, produce, migration, migrations)
- `kaa/tasks/` — 自动化任务（daily, produce, actions）
- `kaa/application/ui/views/` — Gradio UI 视图
- `kaa/application/ui/facade.py` — UI 与服务的桥梁
- `kaa/application/services/` — 服务层 (config, task, update, feedback)
- `kaa/game_data/` — 游戏数据管理 (updater, manifest, paths)
- `kaa/main/` — 入口 (cli, kaa, gr, qml_app)
