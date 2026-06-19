---
name: config-item
description: >
  Add or modify a configuration item. Covers the full chain: decide Shared vs Profile,
  add the Pydantic field, wire the Gradio UI control, and read the value in business logic.
---

# Config Item

新增或修改配置项的标准流程。涉及四个环节：判断配置类型 → 数据模型 → UI 绑定 → 业务读取。

## Step 1 — 判断配置类型

| | SharedConfig | KaaConfig (Profile) |
|---|---|---|
| 存储文件 | `conf/_shared.json` | `conf/profiles/{名称}.json` |
| 数据模型 | `kaa/config/shared.py` → `SharedMiscConfig` | `kaa/config/schema.py` → 对应子类 |
| 运行时读取 | `manager.read_shared()` | `kaa_context.conf()` |
| UI 绑定方法 | `_bind_shared(comp, ref, lambda: shared)` | `_bind(comp, ref)` |
| 跨 profile 共享 | 是 | 否 |

跨 profile 共享的（更新时机、日志等级、遥测等）走 SharedConfig。
每个 profile 可独立设置的任务参数走 Profile KaaConfig。

## Step 2 — 数据模型

**SharedConfig** — 编辑 `kaa/config/shared.py`：

```python
class SharedMiscConfig(BaseModel):
    ...
    game_data_auto_update: bool = True
    """字段说明。"""
```

**Profile KaaConfig** — 编辑 `kaa/config/schema.py`，找到对应子类（如 `PurchaseConfig`）：

```python
class PurchaseConfig(BaseModel):
    ...
    new_field: bool = False
    """字段说明。"""
```

Pydantic 字段类型建议：

| UI 控件 | Pydantic 类型 |
|---|---|
| `gr.Checkbox` | `bool` |
| `gr.Radio` | `Literal['a', 'b', 'c']` |
| `gr.Dropdown(multiselect=True)` | `list[str] = []` |
| `gr.Number` | `int` / `float`，必要时加 `Field(ge=0)` |
| `gr.Textbox` | `str \| None = None` |

## Step 3 — UI 控件

编辑 `kaa/application/ui/views/settings_view.py`，在对应的 `_create_*_settings()` 方法中添加。

**SharedConfig** 用 `_bind_shared`：

```python
c = gr.Checkbox(
    label="自动安装游戏资源更新",
    value=misc.game_data_auto_update,
    interactive=True,
)
self._bind_shared(c, ref(of(misc).game_data_auto_update), lambda: shared)
```

**Profile KaaConfig** 用 `_bind`：

```python
c = gr.Checkbox(
    label="启用商店购买",
    value=opts.tasks.purchase.enabled,
    interactive=True,
)
self._bind(c, ref(of(opts).tasks.purchase.enabled))
```

## Step 4 — 业务逻辑读取

**SharedConfig**：

```python
from kaa.config import manager as config_manager
shared = config_manager.read_shared()
if not shared.misc.game_data_auto_update:
    log("自动安装已关闭，跳过更新")
    return False
```

**Profile KaaConfig**（运行时）：

```python
from kaa.kaa_context import conf
items = conf().tasks.purchase.money_items
```

## 改动的文件清单

SharedConfig 示例（新增 `game_data_auto_update`）：

| 文件 | 改动 |
|---|---|
| `kaa/config/shared.py` | `SharedMiscConfig` 新增字段 |
| `kaa/application/ui/views/settings_view.py` | 对应 `_create_misc_settings()` 新增控件 |
| `kaa/game_data/updater.py` | 在检测到新版本后判断新字段 |
| `conf/_shared.json` | 无需手改，管理器自动补缺省值 |

Profile KaaConfig 示例（新增某项任务开关）：

| 文件 | 改动 |
|---|---|
| `kaa/config/schema.py` | 对应子类新增字段 |
| `kaa/application/ui/views/settings_view.py` | 对应 `_create_*_settings()` 新增控件 |
| `kaa/tasks/xxx.py` | 任务逻辑中通过 `conf()` 读取 |
| `conf/profiles/*.json` | 无需手改，管理器自动补缺省值 |
