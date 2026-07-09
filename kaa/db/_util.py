"""kaa/db 共享工具：JSON ID 解析、按需批量查询、缓存失效。"""
from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

from .sqlite import invalidate_connections, select_many

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)

_cache_clear_hooks: list[Callable[[], None]] = []


def register_cache_clear(fn: Callable[[], None]) -> None:
    _cache_clear_hooks.append(fn)


def clear_db_caches() -> None:
    for fn in _cache_clear_hooks:
        fn()
    invalidate_connections()


def row_dict(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    return dict(row)


def _preview_raw(raw: str, *, limit: int = 120) -> str:
    text = raw.strip()
    if len(text) <= limit:
        return text
    return f'{text[:limit]}...'


def parse_json_list(raw: str | None, *, context: str = '') -> list:
    if not raw:
        return []
    prefix = f'{context}: ' if context else ''
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error(
            '%sinvalid JSON, treating as empty list: %r (%s)',
            prefix,
            _preview_raw(raw),
            exc,
        )
        return []
    if isinstance(data, list):
        return data
    if raw.strip() not in ('', '[]'):
        logger.error(
            '%sexpected JSON array, got %s: %r',
            prefix,
            type(data).__name__,
            _preview_raw(raw),
        )
    return []


def parse_id_list(raw: str | None, *, context: str = '') -> list[str]:
    items = parse_json_list(raw, context=context)
    valid = [item for item in items if isinstance(item, str) and item]
    if items and len(valid) != len(items):
        logger.error(
            '%sID list contains %d non-string or empty item(s) in %r',
            f'{context}: ' if context else '',
            len(items) - len(valid),
            _preview_raw(raw or ''),
        )
    return valid


def collect_ids(rows: Iterable[Any], *json_columns: str) -> set[str]:
    ids: set[str] = set()
    for row in rows:
        row_id = row['id'] if isinstance(row, dict) else row['id']
        for column in json_columns:
            value = row[column] if isinstance(row, dict) else row[column]
            ids.update(parse_id_list(value, context=f'{row_id}.{column}'))
    return ids


def load_by_ids(table: str, ids: Iterable[str], *, columns: str = '*') -> list[sqlite3.Row]:
    id_list = sorted({item for item in ids if item})
    if not id_list:
        return []
    placeholders = ','.join('?' for _ in id_list)
    query = f'SELECT {columns} FROM {table} WHERE id IN ({placeholders});'
    return select_many(query, *id_list)


def parse_rows(rows: Iterable[Any], model: type[T]) -> list[T]:
    return [model.model_validate(row_dict(row)) for row in rows]


def load_row_map(
    table: str,
    ids: Iterable[str],
    model: type[T],
    *,
    columns: str = '*',
) -> dict[str, T]:
    return {item.id: item for item in parse_rows(load_by_ids(table, ids, columns=columns), model)}


def log_missing_ids(
    context: str,
    referenced_ids: Iterable[str],
    available: Mapping[str, Any] | Iterable[str],
) -> None:
    available_set = set(available) if not isinstance(available, Mapping) else set(available.keys())
    missing = [item for item in referenced_ids if item and item not in available_set]
    if not missing:
        return
    if len(missing) <= 10:
        preview = missing
    else:
        preview = [*missing[:10], f'... (+{len(missing) - 10} more)']
    logger.error('%s: %d missing id(s): %s', context, len(missing), preview)