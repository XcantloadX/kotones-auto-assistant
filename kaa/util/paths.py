import os
from typing import cast
from importlib import resources

from kaa import resources as res

CACHE = os.path.join('cache')
RESOURCE = cast(list[str], res.__path__)[0]

if not os.path.exists(CACHE):
    os.makedirs(CACHE)

def cache(path: str) -> str:
    p = os.path.join(CACHE, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p

def resource(path: str) -> str:
    return os.path.join(RESOURCE, path)

def get_ahk_path() -> str:
    """获取 AutoHotkey 可执行文件路径"""
    return str(resources.files('kaa.res.bin') / 'AutoHotkey.exe')