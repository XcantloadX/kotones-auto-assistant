from typing import Literal
from pydantic import BaseModel


class ProfilesConfig(BaseModel):
    last_used: str | None = None
    open_tabs: list[str] = []


class InterfaceConfig(BaseModel):
    window_style: str = ''
    theme_color: str | None = None
    color_scheme: Literal['auto', 'light', 'dark'] = 'auto'
    startup_page: Literal['overview', 'last_opened'] = 'last_opened'


class SharedMiscConfig(BaseModel):
    check_update: Literal['never', 'startup'] = 'startup'
    auto_install_update: bool = True
    update_channel: Literal['release', 'beta'] = 'release'
    log_level: Literal['debug', 'verbose'] = 'debug'
    game_data_check: Literal['manual', 'startup', 'daily', 'weekly'] = 'startup'
    game_data_auto_update: bool = True
    game_data_last_checked: str | None = None
    last_seen_changelog: str | None = None


class TelemetryConfig(BaseModel):
    sentry: bool | None = None


class PushConfig(BaseModel):
    enabled: bool = False
    type: Literal['custom', 'discord'] = 'custom'
    command: str = ''
    webhook_url: str = ''


class NotifyConfig(BaseModel):
    system: bool = True
    push: PushConfig = PushConfig()


class HotkeysConfig(BaseModel):
    start: str | None = None
    stop: str | None = None


class SharedConfig(BaseModel):
    version: int = 2
    profiles: ProfilesConfig = ProfilesConfig()
    interface: InterfaceConfig = InterfaceConfig()
    misc: SharedMiscConfig = SharedMiscConfig()
    telemetry: TelemetryConfig = TelemetryConfig()
    notify: NotifyConfig = NotifyConfig()
    hotkeys: HotkeysConfig = HotkeysConfig()
