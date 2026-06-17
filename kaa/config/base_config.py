from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


# ── 设备生命周期 ──────────────────────────────────────────────────────────────

class MuMu12Device(BaseModel):
    type: Literal['mumu12']
    instance_id: str | None = None
    """模拟器实例 ID。"""
    mumu_background_mode: bool = False
    """MuMu12 模拟器后台保活模式"""
    check_and_start: bool = False
    """启动脚本时，若模拟器未运行则自动启动（通过 MuMu SDK）。"""


class MuMu12V5Device(BaseModel):
    type: Literal['mumu12v5']
    instance_id: str | None = None
    """模拟器实例 ID。"""
    mumu_background_mode: bool = False
    """MuMu12 模拟器后台保活模式"""
    check_and_start: bool = False
    """启动脚本时，若模拟器未运行则自动启动（通过 MuMu SDK）。"""


class LeidianDevice(BaseModel):
    type: Literal['leidian']
    instance_id: str | None = None
    """模拟器实例 ID。"""
    adb_emulator_name: str | None = None
    """
    adb 连接的模拟器名，用于 自动启动模拟器 功能。

    雷电模拟器需要设置正确的模拟器名，否则 自动启动模拟器 功能将无法正常工作。
    其他功能不受影响。
    """
    check_and_start: bool = False
    """启动脚本时，若模拟器未运行则自动启动（通过雷电 SDK）。"""


class DmmDevice(BaseModel):
    type: Literal['dmm']
    check_and_start: bool = False
    """启动脚本时，若 DMM 未运行则自动启动。"""
    emulator_path: str | None = None
    """DMM 可执行文件路径"""
    emulator_args: str = ""
    """启动时的命令行参数"""
    cursor_wait_speed: float = -1
    """
    使用 DMM 版后台挂机功能时，在点击前会尝试等待光标静止，以避免发生点击偏移。
    此项规定了速度小于多少时认为光标静止，单位为像素/秒。

    -1 表示使用内置默认值，0 表示禁用该功能。
    """
    windows_window_title: str = 'gakumas'
    """Windows 截图方式的窗口标题"""
    windows_ahk_path: str | None = None
    """Windows 截图方式的 AutoHotkey 可执行文件路径，为 None 时使用默认路径"""


class PlayCoverDevice(BaseModel):
    type: Literal['playcover']


class CustomDevice(BaseModel):
    type: Literal['custom']
    check_and_start: bool = False
    """启动脚本时，若设备未运行则自动启动。"""
    emulator_path: str | None = None
    """设备启动命令或 exe 路径"""
    emulator_args: str = ""
    """启动时的命令行参数"""


DeviceLifecycle = Annotated[
    MuMu12Device | MuMu12V5Device | LeidianDevice | DmmDevice | PlayCoverDevice | CustomDevice,
    Field(discriminator='type')
]


# ── ADB 连接 ──────────────────────────────────────────────────────────────────

class AutoConnection(BaseModel):
    """MuMu 专用，连接信息由程序从 MuMu SDK 自动获取。"""
    type: Literal['auto']


class TcpConnection(BaseModel):
    type: Literal['tcp']
    ip: str = '127.0.0.1'
    """adb 连接的 ip 地址。"""
    port: int = 5555
    """adb 连接的端口。"""


DeviceConnection = Annotated[
    AutoConnection | TcpConnection,
    Field(discriminator='type')
]


# ── 设备总配置 ────────────────────────────────────────────────────────────────

class BackendConfig(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)

    lifecycle: DeviceLifecycle = Field(default_factory=lambda: CustomDevice(type='custom'))
    """设备生命周期配置。"""
    connection: DeviceConnection = Field(default_factory=lambda: TcpConnection(type='tcp'))
    """ADB 连接配置。"""
    screenshot_impl: Literal['adb', 'uiautomator2', 'nemu_ipc', 'windows', 'windows_native', 'windows_background', 'macos'] = 'adb'
    """
    截图方法。暂时推荐使用【adb】截图方式。

    """
    target_screenshot_interval: float | None = None
    """最小截图间隔，单位为秒。为 None 时不限制截图速度。"""

