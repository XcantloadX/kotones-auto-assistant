"""KaaPreferencesController — KAA 偏好（SharedConfig）草稿控制器。"""
import logging

from PySide6.QtCore import QObject

from euishell.controllers.preferences_controller import PreferencesControllerBase

from kaa.config import manager as config_manager
from kaa.config.shared import SharedConfig

logger = logging.getLogger(__name__)


class PreferencesController(PreferencesControllerBase):
    """偏好控制器：dot-path 草稿 + SharedConfig 校验落盘。"""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def _load_config(self) -> dict:
        shared = config_manager.read_shared()
        return shared.model_dump(mode='json')

    def _commit_config(self, merged: dict) -> None:
        candidate = SharedConfig.model_validate(merged)
        config_manager.write_shared(candidate)
