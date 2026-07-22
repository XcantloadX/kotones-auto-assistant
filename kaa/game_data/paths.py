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


def _abs(p: Path) -> str:
    return str(p.resolve()).replace('\\', '/')


# 角色 ID 集，派生自 CharacterId 枚举（单一事实来源）
_CHAR_IDS = frozenset({m.name for m in CharacterId})


@dataclass(frozen=True)
class SkillCardIndex:
    exact: dict[str, str]        # stem -> abs path
    by_asset: dict[str, str]  # base asset -> any-character fallback


@lru_cache(maxsize=1)
def skill_card_index() -> SkillCardIndex:
    """扫描 skill_cards 目录，建立立绘索引。"""
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
