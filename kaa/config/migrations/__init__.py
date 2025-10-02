from typing import Callable, Any, Dict

# 迁移函数类型：接收单个 user_config(dict)，就地修改并返回提示信息
Migration = Callable[[dict[str, Any]], str | None]

# 导入各版本迁移实现
from . import _v1_to_v2
from . import _v2_to_v3
from . import _v3_to_v4
from . import _v4_to_v5
from . import _v5_to_v6

# 注册表：键为旧版本号，值为迁移函数
MIGRATION_REGISTRY: Dict[int, Migration] = {
    1: _v1_to_v2.migrate,
    2: _v2_to_v3.migrate,
    3: _v3_to_v4.migrate,
    4: _v4_to_v5.migrate,
    5: _v5_to_v6.migrate,
}

# 当前最新配置版本
LATEST_VERSION: int = 6

__all__ = [
    "MIGRATION_REGISTRY",
    "LATEST_VERSION",
] 