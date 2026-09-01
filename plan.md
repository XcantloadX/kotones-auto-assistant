# 定时执行功能开发计划

> 功能：软件运行期间生效的任务定时执行（不涉及系统级唤起）。
> 方案：独立调度配置文件 + 全局调度服务 + OverviewPage 卡片入口。

## 已确定基调（Feature 清单）

| 决策点 | 结论 |
|---|---|
| 触发类型 | **每日 HH:MM** + **每周指定星期几 HH:MM** |
| 任务范围 | 固定执行该 profile 已启用的全部任务（`start_all_tasks`，尊重任务页开关），不可选任务子集 |
| 冲突策略 | 不同 profile **并行**（沿用现有能力）；**同 profile 忙 → 跳过本次**并推送通知 |
| 补跑 | **不补跑**，仅软件运行期间生效；错过等下一个周期 |
| 存储 | 独立文件 `conf/_scheduler.json`（自带 version 字段），不动 profile schema、不写迁移 |
| UI | `OverviewPage` 增加「定时任务」卡片（显示下次触发）+ 点击打开管理 Dialog |

## 关键设计决策

### 调度器与 Tab 的会话冲突防护（最重要架构点）

- 若 profile 的 tab 已打开 → 复用该 tab 的 `KaaSession.task_service`；忙则跳过。
- 若 tab 未打开 → 调度器在后台线程创建**临时 `KaaSession`** 执行（不抢 active tab，不打扰用户）。
- **双向防护**：
  - 调度器运行某 profile 期间登记到 busy 集合，暴露 `isProfileBusyByScheduler(name)`；
  - `TabManager.openTab()` 增加检查，拒绝打开正被调度器占用的 profile（提示"该配置正在由定时任务执行"，走现有 `operationFailed` 信号通路）；
  - 反向：调度器 dispatch 前检查 `isTabOpen()`。

### 触发判定（纯函数，独立可测）

- 条目带 `last_run` 时间戳，判定条件：`last_run < 计划时刻 ≤ now` 且 `now - 计划时刻 ≤ 触发窗口（2 分钟）`。
- 窗口机制天然实现"不补跑"（系统休眠唤醒后错过窗口即跳过），同时防止 30s tick 重复触发。

---

## Phase 1 — 数据层（纯配置，无依赖）

1. **新建 `kaa/config/scheduler.py`**：
   - `ScheduleTrigger`：`type: Literal['daily','weekly']`、`time: str`（`HH:MM`）、`weekdays: list[int]`（0=周一…6=周日，daily 忽略）
   - `ScheduleEntry`：`id`（uuid4）、`enabled`、`name`、`profile_name`、`trigger`、`last_run: str | None`（ISO 格式）、`skip_if_running: bool = True`（v1 固定 True，字段预留）
   - `SchedulerConfig`：`version = 1`、`entries: list[ScheduleEntry]`
   - 纯函数：`compute_next_run(entry, now) -> datetime`、`should_fire(entry, now, window_minutes=2) -> bool`
2. **`kaa/config/manager.py` 追加**：`read_scheduler()` / `write_scheduler()`（仿照 `read_shared`/`write_shared` 的单例缓存 + `conf/_scheduler.json` 模式，校验失败时降级为默认配置并告警）。

## Phase 2 — 调度服务（核心）

3. **新建 `kaa/application/services/scheduler_service.py` → `SchedulerService(QObject)`**：
   - 构造时注入 `TabManager` 引用 + 可注入时钟（便于测试）
   - `QTimer` 每 30s tick（主线程），逐条检查 `should_fire`
   - dispatch 流程：`isTabOpen` ? 复用 session : 后台线程 `KaaSession(profile)` → `initialize()` → `task_service.start_all_tasks()` → 轮询等待结束 → `destroy()`；全程登记/释放 busy 集合；写回 `last_run`；emit `entryTriggered` / `entryFinished` / `entrySkipped(reason)`
   - 通过 `Notice` 后端推送"已触发 / 已跳过（任务运行中）/ 执行失败"
   - 启动时校验 entries 里的 `profile_name` 是否仍存在于 `manager.list_profiles()`，失效条目标记 invalid（不自动删除）
4. **`kaa/application/ui/controllers/tab_manager.py`**：`openTab()` 开头增加调度器占用检查。

## Phase 3 — 控制器

5. **新建 `kaa/application/ui/controllers/schedule_controller.py` → `ScheduleController(QObject)`**（全局单例，模式仿 `PreferencesController`）：
   - `entriesJson()`、`nextRunJson()`（供 Overview 卡片：最近的启用条目 + 下次时间描述）、`profilesJson()`（供下拉选择）
   - CRUD Slots：`addEntry(json)` / `updateEntry(id, json)` / `removeEntry(id)` / `setEntryEnabled(id, bool)`，每次写盘后 emit `entriesChanged`
   - 信号转发 `SchedulerService` 的触发事件
   - **集成点**：暴露 `handleProfileRemoved(name)` / `handleProfileRenamed(old, new)`，供删除/重命名配置的流程调用（`ConfigManagerDialog` 的删除流程 + `manager.rename` 调用点挂钩）
6. **`kaa/main/qml_app.py`**：创建 `SchedulerService` 与 `ScheduleController`，注册 `ScheduleController` context property，退出时停止调度器。

## Phase 4 — UI

7. **新建 `kaa/application/ui/qml/dialogs/ScheduleManagerDialog.qml`**：
   - 条目列表：启用开关、名称、目标 profile、触发描述（"每天 04:00" / "周一、周五 12:30"）、编辑/删除
   - 新建/编辑子表单：profile 下拉（来自 `profilesJson`）、类型选择（每日/每周）、星期多选 chips、HH:MM 时间输入
8. **修改 `kaa/application/ui/qml/pages/OverviewPage.qml`**：在品牌区下方增加「定时任务」卡片：下次触发摘要（无启用条目时显示"未设置"）+ "管理"按钮打开 Dialog（照 `configManagerDialog` 的 required property 传入模式）。
9. **修改 `kaa/application/ui/qml/main.qml`**：实例化 `ScheduleManagerDialog` 并传入 `OverviewPage`。

## Phase 5 — 测试与收尾

10. **单元测试**（`tests/kaa/`）：
    - `compute_next_run` / `should_fire`：跨午夜、daily/weekly 过滤、last_run 去重、窗口边界、休眠唤醒跳过
    - `SchedulerService`：注入假时钟 + mock session，验证 busy 跳过、tab 复用、last_run 写回
11. **UI e2e**：`tests/kaa/ui_e2e/` 中为 Overview 卡片和 Dialog 增加 smoke 测试（沿用 `conftest.py` 的 mock 模式）
12. **`docs/CHANGELOG.md`**：新增条目

## 交付顺序与依赖

```
Phase 1 (数据层) ──→ Phase 2 (调度服务) ──→ Phase 3 (控制器) ──→ Phase 4 (UI) ──→ Phase 5
   独立可测            依赖 TabManager 防护      依赖 1+2            依赖 3
```

## 明确不做（v1 范围外）

- 间隔循环 / 一次性触发
- 任务子集选择
- 错过后补跑
- 跨条目串行队列
- 软件未运行时的系统级定时（计划任务/注册表）
- 调度历史记录持久化
