import sqlite3
import threading
from logging import getLogger
from typing import Any, cast, Dict, List, Optional

from kaa import resources as res

_db_path = cast(str, res.__path__)[0] + '/game.db'

_db_dict = {}

logger = getLogger(__name__)

def _ensure_db() -> sqlite3.Connection:
    """
    确保数据库连接已建立
    培育过程是新开线程，不同线程的connection不能使用
    # TODO 培育结束需要关闭connection
    """
    global _db_dict
    thread_id = threading.current_thread().ident
    if thread_id not in _db_dict:
        _db_dict[thread_id] = sqlite3.connect(_db_path)
        _db_dict[thread_id].row_factory = sqlite3.Row
        logger.info("Database connection established for thread: %s", thread_id)
    return _db_dict[thread_id]


def select_many(query: str, *args) -> List[tuple[Any, ...]]:
    """执行查询并返回多行结果，每行为字典格式"""
    db = _ensure_db()
    c = db.cursor()
    c.execute(query, args)
    return c.fetchall()


def select(query: str, *args) -> Optional[tuple[Any, ...]]:
    """执行查询并返回单行结果，为字典格式"""
    db = _ensure_db()
    c = db.cursor()
    c.execute(query, args)
    return c.fetchone()