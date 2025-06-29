from dataclasses import dataclass
from typing import TypeVar, Callable, Dict, Type, Any, overload, Literal, cast, TYPE_CHECKING

from ..errors import KotonebotError
from .device import Device
if TYPE_CHECKING:
    from .implements.adb import AdbImplConfig
    from .implements.remote_windows import RemoteWindowsImplConfig
    from .implements.windows import WindowsImplConfig

AdbBasedImpl = Literal['adb', 'adb_raw', 'uiautomator2']
DeviceImpl = str | AdbBasedImpl | Literal['windows', 'remote_windows']

# --- 核心类型定义 ---

class ImplRegistrationError(KotonebotError):
    """与 impl 注册相关的错误"""
    pass

@dataclass
class ImplConfig:
    """所有设备实现配置模型的名义上的基类，便于类型约束。"""
    pass

T_Config = TypeVar("T_Config", bound=ImplConfig)

# 定义两种创建者函数类型
CreatorWithConfig = Callable[[Any], Device]
CreatorWithoutConfig = Callable[[], Device]

# --- 底层 API: 公开的注册表 ---

# 注册表结构: {'impl_name': (创建函数, 配置模型类 或 None)}
DEVICE_CREATORS: Dict[str, tuple[Callable[..., Device], Type[ImplConfig] | None]] = {}


def register_impl(name: str, config_model: Type[ImplConfig] | None = None) -> Callable[..., Any]:
    """
    一个统一的装饰器，用于向 DEVICE_CREATORS 注册表中注册一个设备实现。

    :param name: 实现的名称 (e.g., 'windows', 'adb')
    :param config_model: (可选) 与该实现关联的 dataclass 配置模型
    """
    def decorator(creator_func: Callable[..., Device]) -> Callable[..., Device]:
        if name in DEVICE_CREATORS:
            raise ImplRegistrationError(f"实现 '{name}' 已被注册。")
        DEVICE_CREATORS[name] = (creator_func, config_model)
        return creator_func
    return decorator


# --- 高层 API: 带 overload 的便利函数 ---

# 为需要配置的已知 impl 提供 overload
@overload
def create_device(impl_name: Literal['windows'], config: 'WindowsImplConfig') -> Device: ...

@overload
def create_device(impl_name: Literal['remote_windows'], config: 'RemoteWindowsImplConfig') -> Device: ...

@overload
def create_device(impl_name: AdbBasedImpl, config: 'AdbImplConfig') -> Device: ...

# 函数的实际实现
def create_device(impl_name: DeviceImpl, config: ImplConfig | None = None) -> Device:
    """
    根据名称和可选的配置对象，统一创建设备。
    """
    creator_tuple = DEVICE_CREATORS.get(impl_name)
    if not creator_tuple:
        raise ImplRegistrationError(f"未找到名为 '{impl_name}' 的实现。")

    creator_func, registered_config_model = creator_tuple

    # 情况 A: 实现需要配置
    if registered_config_model is not None:
        creator_with_config = cast(CreatorWithConfig, creator_func)
        if config is None:
            raise ValueError(f"实现 '{impl_name}' 需要一个配置对象，但传入的是 None。")
        if not isinstance(config, registered_config_model):
            raise TypeError(f"为 '{impl_name}' 传入的配置类型错误，应为 '{registered_config_model.__name__}'，实际为 '{type(config).__name__}'。")
        return creator_with_config(config)
    
    # 情况 B: 实现无需配置
    else:
        creator_without_config = cast(CreatorWithoutConfig, creator_func)
        if config is not None:
            print(f"提示：实现 '{impl_name}' 无需配置，但你提供了一个配置对象，它将被忽略。")
        return creator_without_config()
