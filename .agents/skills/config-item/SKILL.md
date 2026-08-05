---
name: config-item
description: >
  Add or modify a configuration item. Covers the full chain: decide Shared vs Profile,
  add the Pydantic field, wire the QML UI control, and read the value in business logic.
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

## Step 3 — UI 控件

编辑对应的 QML 页面文件（如 `pages/sections/MiscSection.qml` 或 `pages/sections/BasicSection.qml`）。

**SharedConfig** — 在 MiscSection.qml 中添加控件，使用 `mutateSharedMisc` 更新：

```qml
CheckBox {
    text: "新功能"
    checked: sharedMisc.new_field ?? false
    onToggled: mutateSharedMisc(function(m) { m.new_field = checked })
}
```

**Profile KaaConfig** — 在对应 Section QML 中添加控件，使用 `mutateConfig` 更新：

```qml
CheckBox {
    text: "启用商店购买"
    checked: cfg?.profile?.tasks?.purchase?.enabled ?? false
    onToggled: mutateConfig(function(c) { c.tasks.purchase.enabled = checked })
}
```

常见 QML 控件对照：

| Pydantic 类型 | QML 控件 |
|---|---|
| `bool` | `CheckBox` |
| `Literal['a', 'b', 'c']` | `SegmentedButton` 或 `ComboBox` |
| `list[str] = []` | `TagInput` 或自定义多选 |
| `int` / `float` | `SpinBox` 或 `TextField` |
| `str \| None = null` | `TextField` |

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

## Step 5 — 配置迁移（删除/改型/改名时必须）

改动涉及**删除字段**、**修改字段类型/默认值**、**改名**时，存量 JSON 文件不会自动适配，必须新增迁移步骤。

### 什么时候不需要迁移

- 新增字段（Pydantic 默认值自动补缺）
- 已有字段保持类型和语义不变，仅改 docstring

### 迁移基础设施

- `kaa/config/migration.py` → `MigrationStep`（基类）、`MigrationChain`、`MigrationMessage`
- `kaa/config/migrations.py` → 具体的迁移步骤文件

版本号定义：
- `kaa/config/schema.py` → `CONFIG_VERSION_CODE`（新建 profile 用的默认版本）
- `kaa/config/migrations.py` → `LATEST_VERSION`（迁移链的目标版本）
- **两者必须一致**：每新增一个迁移步骤，同时 +1

### 编写迁移步骤

在 `kaa/config/migrations.py` 末尾新增一个 `MigrationStep` 子类，追加到 `profile_migration_chain`。

Profile V10→V11（删除 4 个字段）的完整示例：

```python
class ProfileV10ToV11(MigrationStep):
    """一句话描述迁移做什么。"""

    def check_needed(self, ctx: MigrationContext) -> bool:
        profiles_dir = ctx.config_dir / 'profiles'
        if not profiles_dir.exists():
            return False
        for f in profiles_dir.glob('*.json'):
            data = json.loads(f.read_text(encoding='utf-8'))
            if data.get('version', 0) < 11:
                return True
        return False

    def apply(self, ctx: MigrationContext) -> None:
        profiles_dir = ctx.config_dir / 'profiles'
        if not profiles_dir.exists():
            return
        migrated: list[str] = []
        for f in profiles_dir.glob('*.json'):
            data = json.loads(f.read_text(encoding='utf-8'))
            if data.get('version', 0) >= 11:
                continue

            # TODO: 在这里写实际的迁移逻辑
            # 例如 data['tasks']['start_game'].pop('game_package_name', None)

            data['version'] = 11
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            migrated.append(f.stem)

        if migrated:
            ctx.messages.append(MigrationMessage(
                text="迁移说明文字",
                old_version='v10',
                new_version='v11',
            ))
```

### 关键要点

- **幂等性**：迁移步骤多次执行结果一致（`check_needed` 和 `apply` 都判断 `version >= target`）
- **V8+ 的多文件格式**：遍历 `conf/profiles/*.json`，操作每个文件的 `data` 字典
- **`_shared.json` 迁移**：可直接读写 `ctx.config_dir / '_shared.json'`
- **`SharedConfig` 有独立版本号**：`shared.py` 中的 `version: int = 1`，需要时也新建 `SharedVXToVY` 步骤
- **迁移消息**用 `MigrationMessage(text, old_version, new_version)` 记录，通过 `add_deferred_messages()` 展示给 GUI

### 更新迁移链

在文件末尾：

```python
# 1. 更新版本常量
LATEST_VERSION: int = 11  # 原来的值 +1

# 2. 将新步骤追加到迁移链末尾
profile_migration_chain = MigrationChain(steps=[
    ...
    ProfileV9ToV10(),
    ProfileV10ToV11(),  # ← 新增
])
```

## 改动的文件清单

所有情况都自动调整（管理器默认值补缺，无需迁移）：

| 文件 | 改动 |
|---|---|
| `kaa/config/shared.py` 或 `kaa/config/schema.py` | 对应子类新增字段 |
| `kaa/application/ui/qml/pages/sections/*.qml` | 对应 Section 新增控件 |
| 业务代码文件（如 `kaa/tasks/xxx.py`） | 通过 `conf()` 或 `manager.read_shared()` 读取 |

需要迁移的情况（删除/改型/改名），在以上基础上增加：

| 文件 | 改动 |
|---|---|
| `kaa/config/schema.py` 或 `kaa/config/shared.py` | 修改或删除字段 |
| `kaa/config/migrations.py` | 新增 `MigrationStep` 子类 + `LATEST_VERSION` + 迁移链追加 |
| `conf/profiles/*.json` 或 `conf/_shared.json` | 无需手改，迁移步骤自动清理 |
