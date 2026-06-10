from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class MigrationMessage:
    """迁移消息，向用户展示迁移过程中的说明。"""
    text: str
    level: Literal['info', 'warning'] = 'info'
    old_version: str | None = None
    new_version: str | None = None


@dataclass
class MigrationContext:
    """迁移上下文，链中每个步骤共享。"""
    config_dir: Path
    """配置根目录（即 conf/ 目录）。"""
    messages: list[MigrationMessage] = field(default_factory=list)
    """收集到的迁移消息。"""


class MigrationStep(ABC):
    """迁移步骤基类。

    迁移步骤应当是幂等的，即多次执行结果一致。
    如果检测到需要迁移，执行 apply 并向 context 添加消息。
    """

    @abstractmethod
    def check_needed(self, ctx: MigrationContext) -> bool:
        """检查此步骤是否需要执行。"""

    @abstractmethod
    def apply(self, ctx: MigrationContext) -> None:
        """执行迁移。"""


class MigrationChain:
    """迁移链：按顺序执行迁移步骤。"""

    def __init__(self, *, steps: list[MigrationStep]) -> None:
        self._steps = list(steps)

    def run(self, config_dir: Path) -> list[MigrationMessage]:
        """执行所有迁移步骤。

        :param config_dir: 配置目录（conf/）
        :return: 迁移过程中产生的消息列表
        """
        ctx = MigrationContext(config_dir=config_dir)
        for step in self._steps:
            if step.check_needed(ctx):
                step.apply(ctx)
        return ctx.messages


# --- 全局延迟消息存储 ---

_deferred_messages: list[MigrationMessage] = []


def add_deferred_messages(messages: list[MigrationMessage]) -> None:
    """添加延迟消息，通常由 GUI 在启动后获取并展示。"""
    _deferred_messages.extend(messages)


def get_deferred_messages() -> list[MigrationMessage]:
    """获取并清空所有延迟消息。"""
    global _deferred_messages
    result = list(_deferred_messages)
    _deferred_messages = []
    return result
