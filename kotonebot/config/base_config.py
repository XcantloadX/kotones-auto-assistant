import uuid
from typing import Generic, TypeVar, Literal

from pydantic import BaseModel, ConfigDict

from kotonebot.client import DeviceImpl

T = TypeVar('T')
BackendType = Literal['custom', 'mumu12', 'leidian', 'dmm']

class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)

class BackendConfig(ConfigBaseModel):
    type: BackendType = 'custom'
    """后端类型。"""
    instance_id: str | None = None
    """模拟器实例 ID。"""
    adb_ip: str = '127.0.0.1'
    """adb 连接的 ip 地址。"""
    adb_port: int = 5555
    """adb 连接的端口。"""
    adb_emulator_name: str | None = None
    """
    adb 连接的模拟器名，用于 自动启动模拟器 功能。
    
    雷电模拟器需要设置正确的模拟器名，否则 自动启动模拟器 功能将无法正常工作。
    其他功能不受影响。
    """
    screenshot_impl: DeviceImpl = 'adb'
    """
    截图方法。暂时推荐使用【adb】截图方式。

    如果使用 remote_windows，需要在 adb_ip 中填写远程 Windows 的 IP 地址，在 adb_port 中填写远程 Windows 的端口号。
    """
    check_emulator: bool = False
    """
    检查并启动模拟器

    启动脚本的时候，如果检测到模拟器未启动，则自动启动模拟器。
    如果模拟器已经启动，则不启动。
    """
    emulator_path: str | None = None
    """模拟器 exe 文件路径"""
    emulator_args: str = ""
    """模拟器启动时的命令行参数"""
    windows_window_title: str = 'gakumas'
    """Windows 截图方式的窗口标题"""
    windows_ahk_path: str | None = None
    """Windows 截图方式的 AutoHotkey 可执行文件路径，为 None 时使用默认路径"""

class PushConfig(ConfigBaseModel):
    """推送配置。"""

    wx_pusher_enabled: bool = False
    """是否启用 WxPusher 推送。"""
    wx_pusher_app_token: str | None = None
    """WxPusher 的 app token。"""
    wx_pusher_uid: str | None = None
    """WxPusher 的 uid。"""

    free_image_host_key: str | None = None
    """FreeImageHost API key。用于在推送通知时显示图片。"""

class UserConfig(ConfigBaseModel, Generic[T]):
    """用户可以自由添加、删除的配置数据。"""

    name: str = 'default_config'
    """显示名称。通常由用户输入。"""
    id: str = uuid.uuid4().hex
    """唯一标识符。"""
    category: str = 'default'
    """类别。如：'global'、'china'、'asia' 等。"""
    description: str = ''
    """描述。通常由用户输入。"""
    backend: BackendConfig = BackendConfig()
    """后端配置。"""
    keep_screenshots: bool = False
    """
    是否保留截图。
    若启用，则会保存每一张截图到 `dumps` 目录下。启用该选项有助于辅助调试。
    """
    options: T
    """下游脚本储存的具体数据。"""


class RootConfig(ConfigBaseModel, Generic[T]):
    version: int = 5
    """配置版本。"""
    user_configs: list[UserConfig[T]] = []
    """用户配置。"""

