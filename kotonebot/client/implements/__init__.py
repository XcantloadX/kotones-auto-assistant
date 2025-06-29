# 导入所有内置实现，以触发它们的 @register_impl 装饰器
from . import adb  # noqa: F401
from . import adb_raw  # noqa: F401
from . import remote_windows  # noqa: F401
from . import uiautomator2  # noqa: F401
from . import windows  # noqa: F401