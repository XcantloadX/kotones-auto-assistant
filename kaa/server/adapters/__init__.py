"""
Adapters - 封装业务逻辑到后端的适配层
"""
from .kaa_runtime import KaaRuntime, get_runtime

__all__ = ['KaaRuntime', 'get_runtime']

