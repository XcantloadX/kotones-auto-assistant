"""ProfileStoreBackend — Profile 列表桥接（配置管理对话框数据源）。"""
import json
import logging
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QObject, Property, Signal

from euishell.session import ProfileProvider

if TYPE_CHECKING:
    from euishell.controllers.tab_manager import TabManager

logger = logging.getLogger(__name__)


class ProfileStoreBackend(QObject):
    """Profile 列表桥接：当前 profile 名 + 全部 profile 列表 JSON。"""

    currentProfileChanged = Signal()
    profilesChanged = Signal()

    def __init__(
        self,
        tab_manager: 'TabManager',
        provider: ProfileProvider,
        parent: QObject | None = None,
    ) -> None:
        """
        :param tab_manager: Tab 管理器（活跃 Tab → 当前 profile）
        :param provider: profile 管理后端
        :param parent: Qt 父对象
        """
        super().__init__(parent)
        self._tab_manager = tab_manager
        self._provider = provider
        self._current_profile_id = ''
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
        name = cast(str, self._tab_manager.activeProfileId) or ''
        if name == self._current_profile_id:
            return
        self._current_profile_id = name
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
            names = self._provider.list_profiles()
            profiles = [{'label': n, 'value': n} for n in names]
            return json.dumps({'profiles': profiles}, ensure_ascii=False)
        except Exception:
            logger.exception('Failed to list profiles')
            return '{"profiles":[]}'

    def _get_current_profile_id(self) -> str:
        return self._current_profile_id

    def _get_profiles_json(self) -> str:
        return self._profiles_json

    currentProfileName = Property(str, _get_current_profile_id, notify=currentProfileChanged)
    profilesJson = Property(str, _get_profiles_json, notify=profilesChanged)
