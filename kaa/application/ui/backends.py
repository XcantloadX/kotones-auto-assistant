"""KAA 的 EuiShell 后端适配：Profile 管理、Tab 持久化、外观配置存取。"""
import logging

from euishell.exceptions import ProfileError
from euishell.session import AppearanceSettingsStore, OpenTabsState, TabPersistence
from euishell.session import ProfileProvider

from kaa.config import manager as config_manager

logger = logging.getLogger(__name__)


class KaaProfileProvider(ProfileProvider):
    """基于 kaa 配置系统的 Profile 管理后端。"""

    def list_profiles(self) -> list[str]:
        return config_manager.list_profiles()

    def create(self, name: str) -> None:
        try:
            config_manager.create(name, exist='ok')
        except Exception as exc:
            logger.exception('Failed to create profile: %s', name)
            raise ProfileError(str(exc), name) from exc

    def rename(self, old_name: str, new_name: str) -> None:
        try:
            config_manager.rename(old_name, new_name)
        except Exception as exc:
            logger.exception('Failed to rename profile: %s -> %s', old_name, new_name)
            raise ProfileError(str(exc), old_name) from exc

    def remove(self, name: str) -> None:
        try:
            config_manager.remove(name, not_exist='ok')
        except Exception as exc:
            logger.exception('Failed to remove profile: %s', name)
            raise ProfileError(str(exc), name) from exc


class KaaTabPersistence(TabPersistence):
    """基于 SharedConfig 的 Tab 持久化后端。"""

    def save_open_tabs(self, state: OpenTabsState) -> None:
        shared = config_manager.read_shared()
        shared.profiles.open_tabs = state.tab_ids
        shared.profiles.last_used = state.last_used
        config_manager.write_shared(shared)

    def load_open_tabs(self) -> OpenTabsState:
        shared = config_manager.read_shared()
        return OpenTabsState(
            tab_ids=shared.profiles.open_tabs or [],
            last_used=shared.profiles.last_used,
        )


class KaaAppearanceStore(AppearanceSettingsStore):
    """基于 SharedConfig 的外观配置存取后端。"""

    def get_color_scheme(self) -> str:
        return config_manager.read_shared().interface.color_scheme

    def set_color_scheme(self, value: str) -> None:
        shared = config_manager.read_shared()
        shared.interface.color_scheme = value  # type: ignore[assignment]
        config_manager.write_shared(shared)

    def get_theme_color(self) -> str | None:
        return config_manager.read_shared().interface.theme_color

    def set_theme_color(self, value: str | None) -> None:
        shared = config_manager.read_shared()
        shared.interface.theme_color = value
        config_manager.write_shared(shared)

    def get_window_style(self) -> str:
        return config_manager.read_shared().interface.window_style

    def set_window_style(self, value: str) -> None:
        shared = config_manager.read_shared()
        shared.interface.window_style = value
        config_manager.write_shared(shared)
