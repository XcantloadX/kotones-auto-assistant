import os
import runpy
import shutil
import argparse
import importlib
from pathlib import Path
from threading import Thread

from . import debug
from kotonebot.backend.context import init_context

def _task_thread(task_module: str):
    """任务线程。"""
    runpy.run_module(task_module, run_name="__main__")

def _parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description='KotoneBot visual debug tool')
    parser.add_argument(
        '-s', '--save', 
        help='Save dump image and results to the specified folder',
        type=str,
        metavar='PATH'
    )
    parser.add_argument(
        '-c', '--clear',
        help='Clear the dump folder before running',
        action='store_true'
    )
    parser.add_argument(
        '-t', '--config-type',
        help='The full path of the config data type. e.g. `kotonebot.tasks.common.BaseConfig`',
        type=str,
        metavar='TYPE',
        required=True
    )
    parser.add_argument(
        'input_module',
        help='The module to run'
    )
    return parser.parse_args()

def _start_task_thread(module: str):
    """启动任务线程。"""
    thread = Thread(target=_task_thread, args=(module,))
    thread.start()

if __name__ == "__main__":
    args = _parse_args()
    debug.enabled = True
    
    # 设置保存路径
    if args.save:
        save_path = Path(args.save)
        debug.save_to_folder = str(save_path)
        if not os.path.exists(save_path):
            os.makedirs(save_path)
    if args.clear:
        if debug.save_to_folder:
            shutil.rmtree(debug.save_to_folder)

    # 初始化上下文
    module_name, class_name = args.config_type.rsplit('.', 1)
    class_ = importlib.import_module(module_name).__getattribute__(class_name)
    init_context(config_type=class_)
    
    # 启动服务器
    from .server import app
    import uvicorn
    
    # 启动任务线程
    _start_task_thread(args.input_module)
    
    # 启动服务器
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level='critical' if debug.hide_server_log else None)
