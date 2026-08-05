from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from kaa.db.constants import CharacterId

_GAME_DATA_DIR = Path('./resources/game_data')

def get_game_data_dir() -> Path:
    _GAME_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _GAME_DATA_DIR

def game_db_path() -> Path:
    return get_game_data_dir() / 'game.db'

def sprites_path(category: str) -> Path:
    """category: 'idol_cards' | 'skill_cards' | 'drinks'"""
    return get_game_data_dir() / category

def version_path() -> Path:
    return get_game_data_dir() / 'version.txt'


# ── Staging 暂存目录路径 ─────────────────────────────────────────────────────

def staging_dir() -> Path:
    """staging 下载暂存目录。"""
    return get_game_data_dir() / '.staging'

def staging_complete_marker() -> Path:
    """staging 完整性标记文件路径。"""
    return staging_dir() / '.complete'

def staging_game_db_path() -> Path:
    return staging_dir() / 'game.db'

def staging_sprites_path(category: str) -> Path:
    return staging_dir() / category

def staging_version_path() -> Path:
    return staging_dir() / 'version.txt'

def staging_cache_dir() -> Path:
    """staging 图像索引缓存目录。"""
    return Path('./cache/.staging')


def _abs(p: Path) -> str:
    return str(p.resolve()).replace('\\', '/')


# 角色 ID 集，派生自 CharacterId 枚举（单一事实来源）
_CHAR_IDS = frozenset({m.name for m in CharacterId})


@dataclass(frozen=True)
class SkillCardIndex:
    exact: dict[str, str]        # stem -> abs path
    by_asset: dict[str, str]  # base asset -> any-character fallback


_cache_clear_registered = False


def _register_cache_clear() -> None:
    """惰性注册 skill_card_index 缓存失效钩子（首次调用索引时）。

    无法在模块顶层注册：``kaa.db._util`` 传递依赖 ``kaa.db.sqlite``，
    而 ``kaa.db.sqlite`` 又 import 本模块，模块顶层 import 会形成循环导入。
    首次调用时各模块均已加载完毕，此时注册安全。
    """
    global _cache_clear_registered
    if _cache_clear_registered:
        return
    from kaa.db._util import register_cache_clear

    register_cache_clear(skill_card_index.cache_clear)
    _cache_clear_registered = True


@lru_cache(maxsize=1)
def skill_card_index() -> SkillCardIndex:
    """扫描 skill_cards 目录，建立立绘索引。"""
    _register_cache_clear()
    base = sprites_path('skill_cards')
    exact: dict[str, str] = {}
    by_asset: dict[str, str] = {}
    if base.is_dir():
        for p in base.glob('*.png'):
            stem = p.stem
            ap = _abs(p)
            exact[stem] = ap
            if '-' in stem:
                char = stem.rsplit('-', 1)[-1]
                if char in _CHAR_IDS:
                    by_asset.setdefault(stem[:-(len(char) + 1)], ap)
    return SkillCardIndex(exact, by_asset)


def skill_card_path(asset_id: str, character: str | None = None) -> str:
    """asset_id 已是完整资源名，如 img_general_skillcard_act-0_001。"""
    if not asset_id:
        return ''
    idx = skill_card_index()
    if character and f'{asset_id}-{character}' in idx.exact:
        return idx.exact[f'{asset_id}-{character}']
    return idx.exact.get(asset_id) or idx.by_asset.get(asset_id, '')
