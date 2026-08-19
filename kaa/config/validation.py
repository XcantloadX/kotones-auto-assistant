"""配置业务规则校验的统一基础设施。

提供结构化的 ``ConfigIssue`` 结果模型与聚合异常 ``ConfigValidationError``，
以及 KaaConfig（Profile 设置页）的业务规则校验函数 ``validate_profile_config``。

与 Pydantic 的字段类型校验互补：这里只表达跨字段、跨选项的业务规则。
校验结果以结构化列表返回，由服务层（UI / 运行时）决定如何展示与拦截。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .base_config import TcpConnection
from .schema import KaaConfig


class ConfigIssue(BaseModel):
    """配置校验结果条目。

    与 Pydantic 的字段类型校验互补：这里只表达跨字段、跨选项的业务规则。
    结果不直接抛出，而是以结构化列表返回，由服务层（UI / 运行时）决定如何展示与拦截。
    """
    model_config = ConfigDict(use_attribute_docstrings=True)

    severity: Literal['error', 'warning'] = 'warning'
    """严重程度：'error'（阻止保存/运行）或 'warning'（提示）。"""
    field: str | None = None
    """关联的字段 dot path（供 UI 定位），可为 None。"""
    message: str = ''
    """面向用户的提示文本。"""


class ConfigValidationError(ValueError):
    """配置业务规则校验失败（存在 error 级 ConfigIssue）。

    聚合所有 error 级消息，供「不关心结构化结果、只需拦截」的调用方使用
    （如 ConfigService.save() 的兜底校验）。
    """
    pass


def validate_profile_config(config: KaaConfig) -> list[ConfigIssue]:
    """校验 KaaConfig（Profile 设置页）的业务规则。

    :param config: 待校验的配置对象。
    :return: 校验问题列表，为空表示无问题。
    """
    issues: list[ConfigIssue] = []

    backend = config.backend
    lc_type = backend.lifecycle.type
    valid_screenshot_methods = {
        'mumu12': ['adb', 'uiautomator2', 'nemu_ipc'],
        'mumu12v5': ['adb', 'uiautomator2', 'nemu_ipc'],
        'leidian': ['adb', 'uiautomator2'],
        'custom': ['adb', 'uiautomator2'],
        'dmm': ['windows', 'windows_native', 'windows_background'],
        'playcover': ['macos'],
    }
    if backend.screenshot_impl not in valid_screenshot_methods.get(lc_type, []):
        issues.append(ConfigIssue(
            severity='error',
            field='backend.screenshot_impl',
            message=(
                f"截图方法 '{backend.screenshot_impl}' "
                f"不适用于当前选择的模拟器类型 '{lc_type}'。"
            ),
        ))

    conn = backend.connection
    if isinstance(conn, TcpConnection) and conn._ip_contains_port():
        issues.append(ConfigIssue(
            severity='error',
            field='backend.connection.ip',
            message=(
                f"ADB IP 地址中不应包含端口（当前填了 '{conn.ip}'）。"
                f"请将 IP 与端口分开填写：IP 填 '{conn.ip.split(':')[0]}'，端口填 '{conn.ip.split(':')[1]}'。"
            ),
        ))

    if config.tasks.produce.enabled and not config.tasks.produce.selected_solution_id:
        issues.append(ConfigIssue(
            severity='error',
            field='tasks.produce.enabled',
            message='启用培育时，必须选择培育方案。',
        ))

    if config.tasks.purchase.ap_enabled and not config.tasks.purchase.ap_items:
        issues.append(ConfigIssue(
            severity='error',
            field='tasks.purchase.ap_enabled',
            message='启用AP购买时，AP商店购买物品不能为空。',
        ))

    if config.tasks.purchase.money_enabled and not config.tasks.purchase.money_items:
        issues.append(ConfigIssue(
            severity='error',
            field='tasks.purchase.money_enabled',
            message='启用金币购买时，金币商店购买物品不能为空。',
        ))

    return issues