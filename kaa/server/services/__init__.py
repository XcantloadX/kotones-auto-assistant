"""
RPC Services
导入所有服务以注册 RPC 方法
"""
# 导入所有服务模块以触发 RPC 方法注册
from . import engine
from . import task
from . import config
from . import produce
from . import reports
from . import updates
from . import screen

__all__ = [
    'engine',
    'task',
    'config',
    'produce',
    'reports',
    'updates',
    'screen',
]

