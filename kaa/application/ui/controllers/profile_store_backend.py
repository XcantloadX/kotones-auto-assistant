"""ProfileStoreBackend — Profile 列表桥接。"""

import json
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QObject, Property, Signal

if TYPE_CHECKING:
    from .tab_manager import TabManager


class ProfileStoreBackend(QObject):
    currentProfileChanged = Signal()
    profilesChanged = Signal()

    def __init__(self, tab_manager: 'TabManager', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tab_manager = tab_manager
        self._current_profile_name = ''
        self._profiles_json = '{"profiles":[]}'

        self._refresh_current_profile()
        self._refresh_profiles()

        tab_manager.activeTabChanged.connect(self._on_active_tab_changed)
        tab_manager.tabsChanged.connect(self._on_tabs_changed)

    def _on_active_tab_changed(self) -> None:
        self._refresh_current_profile()
        self._refresh_profiles_signal()

    def _on_tabs_changed(self) -> None:
        self._refresh_current_profile()
        self._refresh_profiles_signal()

    def _refresh_current_profile(self) -> None:
        name = cast(str, self._tab_manager.activeConfigName) or ''
        if name == self._current_profile_name:
            return
        self._current_profile_name = name
        self.currentProfileChanged.emit()

    def _refresh_profiles_signal(self) -> None:
        next_json = self._build_profiles_json()
        if next_json == self._profiles_json:
            return
        self._profiles_json = next_json
        self.profilesChanged.emit()

    def _refresh_profiles(self) -> None:
        self._profiles_json = self._build_profiles_json()

    def _build_profiles_json(self) -> str:
        try:
            from kaa.config import manager
            names = manager.list_profiles()
            profiles = [{'label': n, 'value': n} for n in names]
            return json.dumps({'profiles': profiles}, ensure_ascii=False)
        except Exception:
            return '{"profiles":[]}'

    def _get_current_profile_name(self) -> str:
        return self._current_profile_name

    def _get_profiles_json(self) -> str:
        return self._profiles_json

    currentProfileName = Property(str, _get_current_profile_name, notify=currentProfileChanged)
    profilesJson = Property(str, _get_profiles_json, notify=profilesChanged)
