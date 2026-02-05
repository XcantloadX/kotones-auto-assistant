import os
import logging

format = '[%(asctime)s][%(levelname)s][%(name)s:%(lineno)d] %(message)s'
root_logger = logging.getLogger()
log_formatter = logging.Formatter(format)

def setup():
    # 初始化日志

    logging.basicConfig(level=logging.INFO, format=format)

    root_logger.setLevel(logging.INFO)

    logging.getLogger("kaa").setLevel(logging.DEBUG)
    logging.getLogger("kotonebot").setLevel(logging.DEBUG)
    logging.getLogger("httpx").setLevel(logging.WARNING)

def add_file_logger(log_path: str):
    log_dir = os.path.abspath(os.path.dirname(log_path))
    os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)