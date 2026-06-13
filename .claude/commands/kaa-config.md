# KAA 配置变更指南

执行 KotonesAutoAssistant 配置系统相关的代码改动（新增字段、调整格式/类型、移除字段、重命名等）时，遵照本文档。

---

## 架构速览

```
kaa/config/
  schema.py          # KaaConfig 及所有子配置的 Pydantic 模型
  base_config.py     # BackendConfig（模拟器/连接）和 PushConfig
  shared.py          # SharedConfig（跨 profile 的杂项设置）
  const.py           # 枚举类型
  manager.py         # 读写 conf/profiles/*.json 和 conf/_shared.json
  migration.py       # MigrationStep/MigrationChain 基类
  migrations.py      # 具体迁移步骤（V1→V8）+ profile_migration_chain
  produce.py         # ProduceSolution 模型

kaa/application/
  services/config_service.py          # 业务层：验证、持久化
  ui/views/settings_view.py           # Gradio 设置页
```

**存储格式：**
- `conf/profiles/{name}.json`：单个 profile（`KaaConfig`）
- `conf/_shared.json`：跨 profile 的共享配置（`SharedConfig`）
- `conf/produce/*.json`：培育方案（`ProduceSolution`）

---

## 规则 1：确认字段归属

| 字段类型 | 所属模型 | 文件 |
|---|---|---|
| 模拟器/连接相关 | `BackendConfig` | `base_config.py` |
| 各任务开关和参数 | 对应子 Config（`ProduceConfig`、`ContestConfig` 等） | `schema.py` |
| 跨 profile 的全局设置（更新、日志等） | `SharedConfig.misc`（`MiscConfig`） | `shared.py` |

`MiscConfig` 的字段在 UI 里使用 `_bind_shared()`，其他字段用 `_bind()`。

---

## 场景 A：新增字段（无 breaking change）

Pydantic 在反序列化时会忽略 JSON 中不存在的字段并填入默认值，因此**只要新字段有默认值，无需迁移步骤**。

### 步骤

**1. 在 `schema.py`（或 `base_config.py` / `shared.py`）的对应模型类中添加字段**

```python
class SomeConfig(ConfigBaseModel):
    # 已有字段 ...
    new_field: bool = False
    """用中文说明此字段的作用。"""
```

约定：
- 继承 `ConfigBaseModel`（或 `BackendConfig` 继承的 `BaseModel`），两者均已设置 `use_attribute_docstrings=True`
- 字段文档用**中文属性文档字符串**（`"""`），紧接在字段声明下方
- 必须提供默认值，保证旧配置文件不崩溃

**2. 在 `settings_view.py` 的对应 `_create_*` 方法中添加 UI 组件**

```python
# 读取当前配置对象（opts = KaaConfig 的子对象）
opts = self.facade.config_service.get_options()

comp = gr.Checkbox(label="新功能", value=opts.some_section.new_field, interactive=True)
self._bind(comp, ref(of(opts).some_section.new_field))
```

若字段在 `SharedConfig.misc`，改用 `_bind_shared`：

```python
shared = self.facade.config_service.get_shared()
misc = shared.misc

comp = gr.Radio(label="...", choices=[...], value=misc.new_field, interactive=True)
self._bind_shared(comp, ref(of(misc).new_field), lambda: shared)
```

**3. 若有业务约束（如"启用 X 时 Y 不能为空"），在 `config_service.py::_validate()` 中添加校验。**

---

## 场景 B：移除字段

Pydantic 的 `model_validate` 默认忽略 JSON 中多余的键，**旧文件不会报错**，因此通常无需迁移。

### 步骤

1. 从 `schema.py`（或 `base_config.py` / `shared.py`）中删除字段声明和文档字符串。
2. 从 `settings_view.py` 中删除对应的 UI 组件和 `_bind()`。
3. 如果 `config_service.py::_validate()` 引用了该字段，一并移除。
4. 从 `const.py` 删除仅由该字段引用的枚举值。

> 若需要将历史 JSON 中的遗留键清理干净（非必须），可添加一个迁移步骤，参考场景 D。

---

## 场景 C：调整字段默认值或文档（无 breaking change）

直接修改 `schema.py` 中的默认值或文档字符串，无需迁移，无需 UI 改动（UI 读取的是实例的当前值）。

---

## 场景 D：重命名字段或更改类型（breaking change）

当 JSON 中的旧键名/值格式无法被 Pydantic 自动处理时，**必须写迁移步骤**并递增版本号。

### 步骤

**1. 在 `schema.py` 更新字段**（新名称/新类型，保留默认值）。

**2. 递增版本号**

```python
# schema.py
CONFIG_VERSION_CODE = 9  # 原来是 8，+1
```

**3. 在 `migrations.py` 新增迁移步骤**

迁移步骤操作的是 `conf/profiles/*.json`（多文件格式，V8+ 的当前格式）：

```python
# migrations.py
class ProfileV8ToV9(MigrationStep):
    """将 some_section.old_field 重命名为 some_section.new_field。"""

    def check_needed(self, ctx: MigrationContext) -> bool:
        # 遍历所有 profile 文件，看是否存在旧键
        profiles_dir = ctx.config_dir / 'profiles'
        if not profiles_dir.exists():
            return False
        for f in profiles_dir.glob('*.json'):
            data = json.loads(f.read_text(encoding='utf-8'))
            section = data.get('some_section', {})
            if 'old_field' in section:
                return True
        return False

    def apply(self, ctx: MigrationContext) -> None:
        profiles_dir = ctx.config_dir / 'profiles'
        migrated: list[str] = []
        for f in profiles_dir.glob('*.json'):
            data = json.loads(f.read_text(encoding='utf-8'))
            section = data.get('some_section', {})
            if 'old_field' in section:
                section['new_field'] = section.pop('old_field')
                data['some_section'] = section
                data['version'] = 9
                f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                migrated.append(f.stem)

        if migrated:
            ctx.messages.append(MigrationMessage(
                text=f"已将以下配置的 old_field 重命名为 new_field：{', '.join(migrated)}",
                old_version='v8',
                new_version='v9',
            ))
```

**迁移步骤规则：**
- `check_needed` 必须幂等：如果已迁移则返回 `False`
- `apply` 必须幂等：重复执行不出错，结果不变
- 不要假设字段一定存在（用 `.get()` 而非 `[]`）
- 若涉及旧版单文件格式（`conf/config.json`）的字段，参考现有的 `ProfileV1ToV6` 步骤，操作 `user_configs` 列表
- 若仅涉及多文件格式（V7→V8 后），操作 `conf/profiles/*.json`，参考上面模板

**4. 将新步骤追加到 `profile_migration_chain` 并更新 `LATEST_VERSION`：**

```python
# migrations.py 末尾
LATEST_VERSION: int = 9  # 更新

profile_migration_chain = MigrationChain(steps=[
    # ... 原有步骤 ...
    ProfileV7ToV8(),
    ProfileV8ToV9(),  # 新增
])
```

**5. 更新 UI**（同场景 A 步骤 2）。

---

## 场景 E：新增完整配置分组

**1. 在 `schema.py` 新建模型类：**

```python
class NewFeatureConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用新功能。"""
    # 其他字段 ...
```

**2. 在 `KaaConfig` 中添加字段：**

```python
class KaaConfig(ConfigBaseModel):
    # ... 已有字段 ...
    new_feature: NewFeatureConfig = NewFeatureConfig()
    """新功能配置"""
```

**3. 在 `settings_view.py` 的合适 Tab 中添加 `_create_new_feature_settings()` 方法，并在 `create_ui()` 中调用。**

无需迁移（新字段有默认值）。

---

## 常见错误和注意事项

**不要忘记 `interactive=True`**
Gradio 组件默认不可交互，必须显式传入 `interactive=True`。

**`_bind` 对 Textbox/Number 使用 `blur` 事件**
`_bind` 内部已自动处理：Textbox 和 Number 在失焦时保存，其他组件在变更时保存。无需手动设置事件。

**`ref(of(obj).field)` 层级要正确**
`of(opts).produce.enabled` 指向 `opts.produce.enabled`，`of(opts.produce).enabled` 同义。两种写法均可，保持和周围代码风格一致。

**SharedConfig 字段不在 profile JSON 里**
`MiscConfig` 的字段存储于 `conf/_shared.json`，迁移时操作的文件不同（若需迁移，直接读写 `ctx.config_dir / '_shared.json'`）。

**迁移步骤是全局的，对所有 profile 生效**
一个步骤会处理 `conf/profiles/` 下的所有 `.json` 文件，而非单个 profile。

**`CONFIG_VERSION_CODE` 和 `LATEST_VERSION` 必须同步**
`schema.py::CONFIG_VERSION_CODE` 和 `migrations.py::LATEST_VERSION` 应保持相同数值。

---

## 文件修改清单（速查）

| 改动类型 | schema.py | base_config.py / shared.py | settings_view.py | migrations.py | config_service.py |
|---|:---:|:---:|:---:|:---:|:---:|
| 新增字段（有默认值）| ✓ | 视情况 | ✓ | — | 视情况 |
| 移除字段 | ✓ | 视情况 | ✓ | — | 视情况 |
| 重命名/类型破坏性变更 | ✓ | 视情况 | ✓ | ✓ | 视情况 |
| 新增分组 | ✓ | — | ✓ | — | — |
| 仅改默认值/文档 | ✓ | 视情况 | — | — | — |
