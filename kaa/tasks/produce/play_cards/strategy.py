from typing import TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from .page import LessonBattleContext

class AbstractBattleStrategy(ABC):
    """考试或课程时出牌策略"""
    @abstractmethod
    def on_action(self, ctx: 'LessonBattleContext'):
        pass
