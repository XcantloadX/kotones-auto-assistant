import os
from importlib import resources

from kaa.game_data.paths import get_game_data_dir

CACHE = os.path.join('cache')

if not os.path.exists(CACHE):
    os.makedirs(CACHE)

def cache(path: str) -> str:
    p = os.path.join(CACHE, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p

def resource(path: str) -> str:
    """返回游戏数据文件的路径（idol_cards/skill_cards/drinks）"""
    return str(get_game_data_dir() / path)

def get_ahk_path() -> str:
    """获取 AutoHotkey 可执行文件路径"""
    return str(resources.files('kaa.res.bin') / 'AutoHotkey.exe')
