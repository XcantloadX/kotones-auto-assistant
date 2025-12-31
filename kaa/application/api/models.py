from typing import Generic, Optional, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class ErrorInfo(BaseModel):
    code: str
    message: str
    detail: Optional[dict] = None


class ApiResponse(GenericModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorInfo] = None


class TaskStatusDto(BaseModel):
    name: str
    status: str  # pending / running / finished / error / cancelled


class PauseToggleResult(BaseModel):
    paused: Optional[bool]


class RunButtonStatus(BaseModel):
    status: str      # "start" / "stop" / "stopping"
    interactive: bool


class PauseButtonStatus(BaseModel):
    status: str      # "pause" / "resume"
    interactive: bool


class TaskRuntimeDto(BaseModel):
    display: str     # 始终为 "HH:MM:SS" 形式
    seconds: int     # 总秒数
    running: bool    # 是否当前有任务在运行


class TaskOverviewDto(BaseModel):
    paused: Optional[bool]
    run_button: RunButtonStatus
    pause_button: PauseButtonStatus
    runtime: TaskRuntimeDto


class QuickSettingsDto(BaseModel):
    purchase: bool
    assignment: bool
    contest: bool
    produce: bool
    mission_reward: bool
    club_reward: bool
    activity_funds: bool
    presents: bool
    capsule_toys: bool
    upgrade_support_card: bool
    end_action: str   # "none" / "shutdown" / "hibernate"


class QuickSettingsPatch(BaseModel):
    purchase: Optional[bool] = None
    assignment: Optional[bool] = None
    contest: Optional[bool] = None
    produce: Optional[bool] = None
    mission_reward: Optional[bool] = None
    club_reward: Optional[bool] = None
    activity_funds: Optional[bool] = None
    presents: Optional[bool] = None
    capsule_toys: Optional[bool] = None
    upgrade_support_card: Optional[bool] = None
    end_action: Optional[str] = None


class LogExportResult(BaseModel):
    message: str
    zip_path: Optional[str] = None


class DesktopShortcutRequest(BaseModel):
    action: str = "create_desktop_shortcut"
    start_immediately: bool = False


class IdleStatusDto(BaseModel):
    enabled: bool
    idle_seconds_config: int
    system_idle_seconds: int
    running: bool
    paused: bool
