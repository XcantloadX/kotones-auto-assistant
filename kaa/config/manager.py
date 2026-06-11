import json
import logging
from pathlib import Path
from typing import Literal, overload

from .schema import KaaConfig
from .shared import SharedConfig
from .migration import add_deferred_messages

logger = logging.getLogger(__name__)

conf_dir: str = './conf'
profiles_dir: str = './conf/profiles'

_shared: 'SharedConfig | None' = None
_migrated: bool = False


def _ensure_migrated() -> None:
    global _migrated
    if _migrated:
        return
    from .migrations import profile_migration_chain  # noqa: PLC0415
    messages = profile_migration_chain.run(Path(conf_dir))
    if messages:
        add_deferred_messages(messages)
    _migrated = True


def list_profiles() -> list[str]:
    """列出所有 profile 名称。"""
    d = Path(profiles_dir)
    if not d.exists():
        return []
    return sorted(f.stem for f in d.glob('*.json'))


def read_shared() -> SharedConfig:
    """返回共享配置单例，首次调用从磁盘读取。"""
    global _shared
    if _shared is not None:
        return _shared

    d = Path(conf_dir)
    d.mkdir(parents=True, exist_ok=True)

    shared_file = d / '_shared.json'
    if not shared_file.exists():
        _shared = SharedConfig()
        write_shared(_shared)
        return _shared

    _shared = SharedConfig.model_validate(json.loads(shared_file.read_text(encoding='utf-8')))
    return _shared


def update_shared(config: SharedConfig) -> None:
    """仅更新内存缓存，不写磁盘。"""
    global _shared
    _shared = config


def write_shared(config: SharedConfig) -> None:
    """写入 _shared.json，同时更新内存缓存。"""
    global _shared
    _shared = config
    d = Path(conf_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / '_shared.json').write_text(
        json.dumps(config.model_dump(), indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


def create(name: str, *, exist: Literal['raise', 'ok'] = 'raise') -> None:
    """创建一个新的 profile 文件（使用默认值）。"""
    d = Path(profiles_dir)
    d.mkdir(parents=True, exist_ok=True)
    config_file = d / f'{name}.json'
    if config_file.exists():
        if exist == 'raise':
            raise FileExistsError(f"Profile '{name}' already exists")
        return
    default_config = KaaConfig(name=name)
    config_file.write_text(
        json.dumps(default_config.model_dump(), indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


def remove(name: str, *, not_exist: Literal['raise', 'ok'] = 'raise') -> None:
    """删除一个 profile 文件。"""
    config_file = Path(profiles_dir) / f'{name}.json'
    if not config_file.exists():
        if not_exist == 'raise':
            raise FileNotFoundError(f"Profile '{name}' does not exist")
        return
    config_file.unlink()


def rename(old_name: str, new_name: str) -> None:
    """重命名一个 profile 文件。"""
    d = Path(profiles_dir)
    old_file = d / f'{old_name}.json'
    new_file = d / f'{new_name}.json'
    if not old_file.exists():
        raise FileNotFoundError(f"Profile '{old_name}' does not exist")
    if new_file.exists():
        raise FileExistsError(f"Profile '{new_name}' already exists")
    config_data = json.loads(old_file.read_text(encoding='utf-8'))
    config_data['name'] = new_name
    new_file.write_text(json.dumps(config_data, indent=2, ensure_ascii=False), encoding='utf-8')
    old_file.unlink()


@overload
def read(name: str, *, not_exist: Literal['raise', 'create'] | KaaConfig = 'raise') -> KaaConfig: ...

@overload
def read(name: str, *, not_exist: None) -> KaaConfig | None: ...

def read(name: str, *, not_exist: Literal['raise', 'create'] | KaaConfig | None = 'raise') -> KaaConfig | None:
    """读取一个 profile。

    :param not_exist: 'raise' 抛异常，'create' 创建默认值并返回，None 返回 None，或提供默认 KaaConfig。
    """
    _ensure_migrated()

    config_file = Path(profiles_dir) / f'{name}.json'
    if not config_file.exists():
        if not_exist == 'raise':
            raise FileNotFoundError(f"Profile '{name}' does not exist")
        elif not_exist == 'create':
            create(name, exist='ok')
            return read(name)
        elif not_exist is None:
            return None
        elif isinstance(not_exist, KaaConfig):
            return not_exist
        else:
            raise ValueError(f"Invalid not_exist value: {not_exist!r}")

    return KaaConfig.model_validate(json.loads(config_file.read_text(encoding='utf-8')))


def write(name: str, config: KaaConfig) -> None:
    """写入一个 profile。"""
    d = Path(profiles_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{name}.json').write_text(
        json.dumps(config.model_dump(), indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
