from typing import Literal
from pydantic import BaseModel


class ProfilesConfig(BaseModel):
    last_used: str | None = None
    open_tabs: list[str] = []


class SharedMiscConfig(BaseModel):
    check_update: Literal['never', 'startup'] = 'startup'
    auto_install_update: bool = True
    expose_to_lan: bool = False
    update_channel: Literal['release', 'beta'] = 'release'
    log_level: Literal['debug', 'verbose'] = 'debug'


class TelemetryConfig(BaseModel):
    sentry: bool | None = None
    """是否启用 Sentry 匿名错误报告。None 表示用户尚未选择。"""


class SharedConfig(BaseModel):
    version: int = 1
    profiles: ProfilesConfig = ProfilesConfig()
    misc: SharedMiscConfig = SharedMiscConfig()
    telemetry: TelemetryConfig = TelemetryConfig()
