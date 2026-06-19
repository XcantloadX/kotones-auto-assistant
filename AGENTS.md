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

## 目录结构速查

- `kaa/config/` — 配置模型 (shared, schema, manager, base_config, produce)
- `kaa/tasks/` — 自动化任务（daily, produce, actions）
- `kaa/application/ui/views/` — Gradio UI 视图
- `kaa/application/ui/facade.py` — UI 与服务的桥梁
- `kaa/application/services/` — 服务层 (config, task, update, feedback)
- `kaa/game_data/` — 游戏数据管理 (updater, manifest, paths)
- `kaa/main/` — 入口 (cli, kaa, gr, qml_app)
