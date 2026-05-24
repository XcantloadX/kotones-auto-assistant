from pathlib import Path

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
