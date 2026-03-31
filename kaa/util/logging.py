import os
import sys
import logging
import threading

format = '[%(asctime)s][%(levelname)s][%(name)s:%(lineno)d] %(message)s'
logger = logging.getLogger(__name__)
root_logger = logging.getLogger()
log_formatter = logging.Formatter(format)

def _install():
    # 主线程
    def handle_sys_exception(exc_type, exc_value, exc_traceback):
        # 忽略键盘中断 (Ctrl+C)，让用户可以正常终止程序
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Uncaught System Exception (Main Thread):", 
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_sys_exception

    # 子线程
    def handle_threading_exception(args):
        # args.thread 是线程对象，args.exc_type 是异常类型...
        logger.critical(
            f"Uncaught Thread Exception (Thread '{args.thread.name}'):",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
        )

    threading.excepthook = handle_threading_exception

def setup():
    logging.basicConfig(level=logging.INFO, format=format)
    root_logger.setLevel(logging.INFO)
    logging.getLogger("kaa").setLevel(logging.DEBUG)
    logging.getLogger("kotonebot").setLevel(logging.DEBUG)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _install()

def add_file_logger(log_path: str):
    log_dir = os.path.abspath(os.path.dirname(log_path))
    os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)