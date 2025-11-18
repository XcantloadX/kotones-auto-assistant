# 计划：将资源文件分离为独立的资源包

本计划旨在为“纯资源包”设计一套可复用的约定，并详细说明将当前 `kaa/resources` 目录内容迁移至一个全新、独立包的具体步骤。

## 1. 设计：纯资源包约定

为了标准化管理资源文件，我们将采纳以下约定。此约定可被项目内未来的其他资源包（如 sprites、models 等）复用。

### a. 命名空间与包名

- 所有资源包都将存在于一个共同的命名空间下：`kaa.resource`。
- 可安装的包名（Package Name）将遵循 `kaa-resource-<name>` 的格式。
- 本次迁移的第一个包，包含游戏数据库和卡面图片，其包名将是 `kaa-resource-game`，并通过 `kaa.resource.game` 的模块路径（Module Path）进行导入。

### b. 包结构

每个资源包都将是一个标准的 Python 包，其目录结构如下：

```
kaa-resource-game/
├── pyproject.toml
└── kaa/
    └── resource/
        ├── __init__.py  # 命名空间包标记
        └── game/
            ├── __init__.py
            ├── version.json # 版本文件
            ├── game.db
            ├── idol_cards/
            │   └── ...
            └── drinks/
                └── ...
```

### c. 资源访问模式

- **所有**对包内资源的访问**必须**通过 Python 内置的 `importlib.resources.files()` API 完成。
- 这是一个健壮、标准的机制，无论包是通过 wheel、egg 还是以可编辑模式（editable mode）安装，它都能正常工作。
- 本约定明确禁止任何直接的路径操作（例如使用 `__path__[0]`）。

## 2. 设计：资源版本系统

为了确保主程序与资源包的兼容性，我们设计了以下版本系统。

### a. 版本号方案

- 采用 `主版本号.次版本号` (例如 `1.0`) 的版本格式。
- **主版本号 (MAJOR)**: 代表 **Schema 版本**。当资源结构发生不兼容变更（例如数据库表结构修改、资源目录重命名）时，主版本号递增。这被视为 **Breaking Change**。
- **次版本号 (MINOR)**: 代表 **数据版本**。当资源内容更新或增加，但结构保持兼容时（例如新增卡面图片、修正数据库错别字），次版本号递增。

### b. 版本存储

- 版本号将存储在资源包内部的 `kaa/resource/game/version.json` 文件中。内容示例: `{ "version": "1.0" }`。
- `kaa-resource-game/pyproject.toml` 文件中的 `version` 字段将与此版本号保持同步。

### c. 版本校验

- 主程序 `kaa` 将在其配置中定义一个它所兼容的 `COMPATIBLE_RESOURCE_MAJOR_VERSION` (兼容的资源主版本号)。
- 在主程序启动时，会增加一个校验步骤：
    1. 读取 `kaa.resource.game` 包内的 `version.json` 文件。
    2. 解析出版本号，并提取主版本号。
    3. 将资源包的主版本号与程序要求的 `COMPATIBLE_RESOURCE_MAJOR_VERSION`进行比较。
    4. 如果不匹配，程序将抛出一个明确的错误并终止运行，以防范因资源不兼容导致的潜在问题。

## 3. 详细迁移计划

为完成本次迁移，将执行以下步骤。

### 步骤 1: 创建新的 `kaa-resource-game` 包

1.  **创建目录结构**:
    - `mkdir -p kaa-resource-game/kaa/resource/game`
    - `touch kaa-resource-game/kaa/__init__.py`
    - `touch kaa-resource-game/kaa/resource/__init__.py`
    - `touch kaa-resource-game/kaa/resource/game/__init__.py`

2.  **为新包创建 `pyproject.toml`**:
    - 创建新文件 `kaa-resource-game/pyproject.toml`，定义 `kaa-resource-game` 包并声明其版本（初始为 `1.0`）。

3.  **创建版本文件**:
    - 创建 `kaa-resource-game/kaa/resource/game/version.json`，并写入初始版本信息：`{ "version": "1.0" }`。

4.  **移动现有资源**:
    - 将 `kaa/resources/` 目录下的所有内容移动到 `kaa-resource-game/kaa/resource/game/`。

### 步骤 2: 更新资源生成脚本

1.  **修改 `tools/db/extract_resources.py`**:
    - 更新脚本中的输出路径，使其指向新包的位置。
    - 脚本执行时，开发者需要根据修改内容决定是否以及如何提升 `version.json` 和 `pyproject.toml` 中的版本号。

2.  **修改 `tools/db/extract_schema.py`**:
    - 更新调用此脚本的地方（如 `justfile`），使其将数据库生成到新包的正确路径下。

### 步骤 3: 更新代码以使用新资源包并添加校验

1.  **在主程序入口添加版本校验**:
    - 在 `kaa/main/kaa.py` 或类似的启动文件中，添加一个新的函数 `check_resource_version()`。
    - 此函数将执行在 **2.c 版本校验** 中描述的逻辑。
    - 程序启动时将首先调用此函数。

2.  **修改 `kaa/util/paths.py`**:
    - **修改前**:
      ```python
      from kaa import resources as res
      RESOURCE = cast(list[str], res.__path__)[0]
      def resource(path: str) -> str:
          return os.path.join(RESOURCE, path)
      ```
    - **修改后**:
      ```python
      from importlib.resources import files
      def resource(path: str) -> str:
          return str(files('kaa.resource.game').joinpath(path))
      ```

3.  **修改 `kaa/db/sqlite.py`**:
    - **修改前**:
      ```python
      from kaa import resources as res
      _db_path = cast(str, res.__path__)[0] + '/game.db'
      ```
    - **修改后**:
      ```python
      from kaa.util import paths
      _db_path = paths.resource('game.db')
      ```

### 步骤 4: 更新构建与依赖配置

1.  **修改 `pyproject.toml` (主项目)**:
    - 添加 `kaa-resource-game` 作为项目的依赖项。
      ```toml
      [project]
      dependencies = [
          # ... 其他依赖
          "kaa-resource-game @ file:./kaa-resource-game",
      ]
      ```

2.  **修改 `requirements.dev.txt`**:
    - 添加新包的可编辑模式安装。
      ```
      -e ./kaa-resource-game
      ```

3.  **修改 `MANIFEST.in`**:
    - 移除 `graft kaa/resources` 这一行。

### 步骤 5: 清理工作

1.  **删除 `kaa/resources`**:
    - 在所有迁移和更新完成后，原有的 `kaa/resources` 目录将被删除。
