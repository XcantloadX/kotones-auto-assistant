import os
import sqlite3
from typing import Any, cast, Dict, List, Optional

from kotonebot.kaa import resources as res

_db: sqlite3.Connection | None = None
_db_path = cast(str, res.__path__)[0] + '/game.db'

def _dict_factory(cursor, row):
    """将查询结果转换为字典格式"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def _ensure_db() -> sqlite3.Connection:
    """确保数据库连接已建立"""
    global _db
    if not _db:
        _db = sqlite3.connect(_db_path)
        _db.row_factory = _dict_factory
    return _db

def select_many(query: str, *args) -> List[Dict[str, Any]]:
    """执行查询并返回多行结果，每行为字典格式"""
    db = _ensure_db()
    c = db.cursor()
    c.execute(query, args)
    return c.fetchall()


def select(query: str, *args) -> Optional[Dict[str, Any]]:
    """执行查询并返回单行结果，为字典格式"""
    db = _ensure_db()
    c = db.cursor()
    c.execute(query, args)
    return c.fetchone()
