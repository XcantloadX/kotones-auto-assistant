"""EuiShell 异常体系。"""

from pathlib import Path


class EuiShellError(Exception):
    """EuiShell 所有异常的基类。"""


class MissingResourceError(EuiShellError):
    """框架内置资源缺失。"""


class PluginLifecycleError(EuiShellError):
    """插件生命周期调用失败。"""


class TaskControlError(EuiShellError):
    """任务运行控制操作失败（由下游 TaskControl 实现抛出）。"""


class ProfileError(EuiShellError):
    """Profile 管理操作失败。

    :param message: 错误描述
    :param profile: 相关 profile 名称
    """

    def __init__(self, message: str, profile: str) -> None:
        super().__init__(message)
        self.profile = profile


class QmlLoadError(EuiShellError):
    """QML 加载失败。

    :param path: 加载失败的 QML 文件
    """

    def __init__(self, path: Path) -> None:
        super().__init__(f'QML 文件加载失败: {path}')
        self.path = path
