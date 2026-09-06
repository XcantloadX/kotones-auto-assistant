"""Shell 控制器层：Tab 生命周期、任务运行、设置/偏好草稿、Profile 存储。"""

from euishell.controllers.preferences_controller import PreferencesControllerBase
from euishell.controllers.profile_store import ProfileStoreBackend
from euishell.controllers.run_controller import RunController
from euishell.controllers.settings_controller import SettingsControllerBase
from euishell.controllers.tab_controller import TabController
from euishell.controllers.tab_manager import TabManager
from euishell.controllers.task_toggles_model import TaskTogglesModel

__all__ = [
    'PreferencesControllerBase',
    'ProfileStoreBackend',
    'RunController',
    'SettingsControllerBase',
    'TabController',
    'TabManager',
    'TaskTogglesModel',
]
