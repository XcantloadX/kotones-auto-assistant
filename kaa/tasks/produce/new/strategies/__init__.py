"""培育策略包。

对外暴露抽象基类 :class:`ProduceStrategy` 与默认实现 :class:`StandardStrategy`，
Controller 只需依赖抽象基类即可与任意策略解耦。
"""

from .base import ProduceStrategy
from .standard import StandardStrategy

__all__ = ['ProduceStrategy', 'StandardStrategy']