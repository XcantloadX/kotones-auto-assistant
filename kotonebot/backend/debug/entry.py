import sys
import runpy
from threading import Thread
from typing import Callable

from . import debug

def _task_thread(task_module: str):
    """任务线程。"""
    runpy.run_module(task_module, run_name="__main__")

def _start_task_thread():
    """启动任务线程。"""
    module = sys.argv[1]
    thread = Thread(target=_task_thread, args=(module,))
    thread.start()

if __name__ == "__main__":
    debug.enabled = True
    # 启动服务器
    from .server import app
    import uvicorn
    
    # 启动任务线程
    _start_task_thread()
    
    # 启动服务器
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level='critical' if debug.hide_server_log else None)
