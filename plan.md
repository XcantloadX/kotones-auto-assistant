# KAA `gr.py` 重构计划 (v4)

## 1. 目标

-   **深度解耦**: 将 UI、业务逻辑、状态管理彻底分离。
-   **服务化**: 遵循项目现有 `core/` 目录的风格，将独立的业务逻辑（配置、培育方案）封装成专门的 `Service` 类。
-   **清晰的分层**: 构建一个清晰的 `View` -> `Facade` -> `Services` 调用链，使代码易于维护和扩展。
-   gr.py 的改动最小化

## 2. 架构设计

1.  **服务层 (Services Layer)**: 包含所有核心业务逻辑和状态，完全独立于上层。
    -   **`TaskControlService`**: 封装对 `Kaa` 实例的直接操作，管理 `is_running`, `run_status` 等**运行时状态**。
    -   **`ConfigService`**: 负责 `config.json` 的读取、校验、保存和热重载。
    -   **`ProduceSolutionService`**: 负责培育方案的增、删、改、查。
    -   `UpdateService`, `FeedbackService`, `IdleModeManager` (现有服务，将被 `Facade` 集成)。

2.  **外观层 (Facade Layer)**:
    -   `KaaFacade` 类将作为 **`View` 和 `Services` 之间的唯一桥梁**。
    -   **职责**:
        -   **容器**: 在 `__init__` 中，实例化所有的 `Service` 类。
        -   **外观/编排**: 暴露简洁的API给 `View` 调用。当 `View` 调用一个方法时（如 `facade.start_run()`），`Facade` 负责将请求**转发**给对应的 `Service` （如 `task_control_service.start()`）。
        -   **状态代理**: `Facade` 不持有状态，但它会提供方法从 `Service` 中获取状态，并传递给 `View`（如 `facade.is_running()` 内部调用 `task_control_service.is_running()`）。

3.  **视图层 (View Layer)**:
    -   `KaaGradioView` 类只负责 UI 的渲染和用户输入。
    -   **职责**:
        -   **只与 `Facade` 通信**。它不知道任何 `Service` 的存在。
        -   渲染 UI，将按钮事件绑定到 `facade` 的方法上。
        -   通过定时器调用 `facade` 的方法获取状态，并更新界面。

## 3. 实施步骤

1.  **创建文件结构**: (批准后执行)
    -   创建目录 `kaa/services` 用于存放新的 `Service` 类。
    -   创建文件：
        -   `kaa/services/task_control_service.py`
        -   `kaa/services/config_service.py`
        -   `kaa/services/produce_solution_service.py`
    -   创建目录 `kaa/ui`。
    -   创建文件：
        -   `kaa/ui/facade.py` (用于 `KaaFacade` 类)
        -   `kaa/ui/gradio_view.py` (用于 `KaaGradioView` 类)

2.  **实现 `Service` 层**:
    -   分别创建上述 `TaskControlService`, `ConfigService`, `ProduceSolutionService` 类，并从 `gr.py` 中剥离、迁移相应的逻辑。

3.  **实现 `Facade`**:
    -   在 `facade.py` 中创建 `KaaFacade` 类。
    -   在其构造函数中，实例化所有 `Service`。
    -   为 `View` 需要的每个操作/状态查询创建对应的代理方法。

4.  **实现 `View`**:
    -   在 `gradio_view.py` 中创建 `KaaGradioView` 类，迁移所有 UI 创建代码。
    -   重写所有事件回调，使其全部调用 `self.facade` 的方法。

5.  **更新入口文件 `gr.py`**:
    -   重写 `kaa/main/gr.py`，负责初始化 `Kaa`, `KaaFacade`, `KaaGradioView`，并将它们连接起来，最后启动 Gradio 服务。