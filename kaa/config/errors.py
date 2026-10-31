"""配置读写相关的异常类型。"""

from pathlib import Path


class ConfigLoadError(Exception):
    """配置文件存在但无法解析时抛出。"""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f'配置文件 {path} 格式有误：{reason}')
