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
    game_data_check: Literal['manual', 'startup', 'daily', 'weekly'] = 'startup'
    """游戏资源文件检查频率。manual=手动，startup=每次启动，daily=每天一次，weekly=每周一次。"""
    game_data_last_checked: str | None = None
    """上次检查游戏资源的时间（ISO 8601），由程序写入。"""
    last_seen_changelog: str | None = None
    """上次已展示更新日志的版本号，用于判断是否需要弹出新版提示。"""


class TelemetryConfig(BaseModel):
    sentry: bool | None = None
    """是否启用 Sentry 匿名错误报告。None 表示用户尚未选择。"""


class SharedConfig(BaseModel):
    version: int = 1
    profiles: ProfilesConfig = ProfilesConfig()
    misc: SharedMiscConfig = SharedMiscConfig()
    telemetry: TelemetryConfig = TelemetryConfig()
