import os
from importlib.resources import files

CACHE = os.path.join('cache')

if not os.path.exists(CACHE):
    os.makedirs(CACHE)

def cache(path: str) -> str:
    p = os.path.join(CACHE, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p

def resource(path: str) -> str:
    return str(files('kaa.resource.game').joinpath(path))

def get_ahk_path() -> str:
    """获取 AutoHotkey 可执行文件路径"""
    return str(files('kaa.res.bin') / 'AutoHotkey.exe')