"""
config_api：BASE=/api/config

GET actions:
* ACTION=get_root，IN=(action=get_root)，OUT=ApiResponse[RootConfig[BaseConfig]]，获取根配置
* ACTION=get_options，IN=(action=get_options)，OUT=ApiResponse[UserConfig[BaseConfig]]，获取当前 options
* ACTION=get_quick，IN=(action=get_quick)，OUT=ApiResponse[QuickSettingsDto]，获取快捷设置
* ACTION=get_idle，IN=(action=get_idle)，OUT=ApiResponse[IdleModeConfig]，获取空闲模式配置

POST actions (body: Pydantic request models):
* ACTION=save_options，IN=(SaveOptionsRequest)，OUT=ApiResponse[UserConfig[BaseConfig]]，保存 options
* ACTION=patch_options，IN=(PatchOptionsRequest)，OUT=ApiResponse[UserConfig[BaseConfig]]，深合并并保存 options（支持嵌套 path）
* ACTION=patch_quick，IN=(PatchQuickRequest)，OUT=ApiResponse[QuickSettingsDto]，修改快捷设置
* ACTION=patch_idle，IN=(PatchIdleRequest)，OUT=ApiResponse[IdleModeConfig]，修改空闲模式配置
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from kaa.application.ui.facade import KaaFacade
from kaa.application.services.config_service import ConfigService
from kaa.config.schema import BaseConfig, IdleModeConfig
from kotonebot.config.manager import RootConfig
from kotonebot.config.base_config import UserConfig

from .models import (
    ApiResponse,
    ErrorInfo,
)
from .tasks_api import get_facade


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


class QuickSettingItem(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    has_settings: bool = False
    value_key: Optional[str] = None


class QuickSettingsResponse(BaseModel):
    values: QuickSettingsDto
    items: list[QuickSettingItem]


class SaveOptionsRequest(BaseModel):
    action: str
    options: dict


class PatchOptionsRequest(BaseModel):
    action: str
    patch: dict


class PatchQuickRequest(BaseModel):
    action: str
    patch: dict


class PatchIdleRequest(BaseModel):
    action: str
    patch: dict


router = APIRouter()


def _get_quick_from_options(options: BaseConfig) -> QuickSettingsDto:
    end_action = "none"
    if options.end_game.shutdown:
        end_action = "shutdown"
    elif options.end_game.hibernate:
        end_action = "hibernate"

    return QuickSettingsDto(
        purchase=options.purchase.enabled,
        assignment=options.assignment.enabled,
        contest=options.contest.enabled,
        produce=options.produce.enabled,
        mission_reward=options.mission_reward.enabled,
        club_reward=options.club_reward.enabled,
        activity_funds=options.activity_funds.enabled,
        presents=options.presents.enabled,
        capsule_toys=options.capsule_toys.enabled,
        upgrade_support_card=options.upgrade_support_card.enabled,
        end_action=end_action,
    )


def _get_quick_definitions() -> list[QuickSettingItem]:
    return [
        QuickSettingItem(id='shop', name='商店', icon='store', has_settings=True, value_key='purchase'),
        QuickSettingItem(id='work', name='工作', icon='briefcase', has_settings=True, value_key='assignment'),
        QuickSettingItem(id='contest', name='竞赛', icon='trophy', has_settings=False, value_key='contest'),
        QuickSettingItem(id='training', name='培育', icon='sprout', has_settings=True, value_key='produce'),
        QuickSettingItem(id='mission', name='任务', icon='clipboard-check', has_settings=False, value_key='mission_reward'),
        QuickSettingItem(id='guild', name='社团', icon='account-group', has_settings=True, value_key='club_reward'),
        QuickSettingItem(id='activity', name='活动', icon='party-popper', has_settings=False, value_key='activity_funds'),
        QuickSettingItem(id='gift', name='礼物', icon='gift', has_settings=False, value_key='presents'),
        QuickSettingItem(id='gacha', name='扭蛋', icon='pokeball', has_settings=True, value_key='capsule_toys'),
    ]


def _apply_quick_patch(options: BaseConfig, patch: QuickSettingsPatch) -> None:
    if patch.purchase is not None:
        options.purchase.enabled = patch.purchase
    if patch.assignment is not None:
        options.assignment.enabled = patch.assignment
    if patch.contest is not None:
        options.contest.enabled = patch.contest
    if patch.produce is not None:
        options.produce.enabled = patch.produce
    if patch.mission_reward is not None:
        options.mission_reward.enabled = patch.mission_reward
    if patch.club_reward is not None:
        options.club_reward.enabled = patch.club_reward
    if patch.activity_funds is not None:
        options.activity_funds.enabled = patch.activity_funds
    if patch.presents is not None:
        options.presents.enabled = patch.presents
    if patch.capsule_toys is not None:
        options.capsule_toys.enabled = patch.capsule_toys
    if patch.upgrade_support_card is not None:
        options.upgrade_support_card.enabled = patch.upgrade_support_card

    if patch.end_action is not None:
        options.end_game.shutdown = patch.end_action == "shutdown"
        options.end_game.hibernate = patch.end_action == "hibernate"


def _deep_patch(options: Any, patch_data: dict) -> None:
    """对 BaseConfig 执行深合并，仅支持嵌套对象路径，不处理数组等复杂结构。"""
    for key, value in patch_data.items():
        if value is None:
            continue

        if not hasattr(options, key):
            continue

        current = options.__dict__.get(key)

        if isinstance(value, dict) and isinstance(current, BaseModel):
            _deep_patch(current, value)
        else:
            setattr(options, key, value)


@router.get("", response_model=ApiResponse[Any])
async def config_get(
    action: str = Query(...),
    facade: KaaFacade = Depends(get_facade),
):
    """Handle GET /api/config?action=... for config-related queries."""

    cfg_service: ConfigService = facade.config_service

    if action == "get_root":
        root: RootConfig[BaseConfig] = cfg_service.get_root_config()
        return ApiResponse[RootConfig[BaseConfig]](success=True, data=root)

    if action == "get_options":
        options = cfg_service.get_current_user_config()
        return ApiResponse[UserConfig[BaseConfig]](success=True, data=options)

    if action == "get_quick":
        options = cfg_service.get_options()
        quick = _get_quick_from_options(options)
        items = _get_quick_definitions()
        resp = QuickSettingsResponse(values=quick, items=items)
        return ApiResponse[QuickSettingsResponse](success=True, data=resp)

    if action == "get_idle":
        options = cfg_service.get_options()
        idle: IdleModeConfig = options.idle
        return ApiResponse[IdleModeConfig](success=True, data=idle)

    raise HTTPException(status_code=404, detail="Unknown action")


@router.post("", response_model=ApiResponse[Any])
async def config_post(
    payload: dict,
    facade: KaaFacade = Depends(get_facade),
):
    cfg_service: ConfigService = facade.config_service
    action = payload.get("action")

    if action == "save_options":
        try:
            req = SaveOptionsRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse[UserConfig[BaseConfig]](
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
        options_data = req.options
        if options_data is None:
            return ApiResponse[BaseConfig](
                success=False,
                error=ErrorInfo(code="OPTIONS_REQUIRED", message="必须提供 options"),
            )
        config = UserConfig[BaseConfig].model_validate(options_data)
        cfg_service.set_current_user_config(config)
        try:
            cfg_service.save()
        except Exception as e:
            return ApiResponse[UserConfig[BaseConfig]](
                success=False,
                error=ErrorInfo(code="CONFIG_VALIDATION_ERROR", message=str(e)),
            )
        return ApiResponse[UserConfig[BaseConfig]](success=True, data=config)
    if action == "patch_options":
        try:
            req = PatchOptionsRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse[UserConfig[BaseConfig]](
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
        patch_data: dict | None = req.patch
        if patch_data is None:
            return ApiResponse[UserConfig[BaseConfig]](
                success=False,
                error=ErrorInfo(code="PATCH_REQUIRED", message="必须提供 patch"),
            )
        config = cfg_service.get_current_user_config()
        _deep_patch(config, patch_data)
        try:
            cfg_service.save()
        except Exception as e:
            return ApiResponse[UserConfig[BaseConfig]](
                success=False,
                error=ErrorInfo(code="CONFIG_VALIDATION_ERROR", message=str(e)),
            )
        return ApiResponse[UserConfig[BaseConfig]](success=True, data=config)

    if action == "patch_quick":
        try:
            req = PatchQuickRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse[QuickSettingsDto](
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
        patch_raw = req.patch or {}
        patch = QuickSettingsPatch.model_validate(patch_raw)
        config = cfg_service.get_options()
        _apply_quick_patch(config, patch)
        try:
            cfg_service.save()
        except Exception as e:
            return ApiResponse[QuickSettingsDto](
                success=False,
                error=ErrorInfo(code="CONFIG_VALIDATION_ERROR", message=str(e)),
            )
        quick = _get_quick_from_options(config)
        items = _get_quick_definitions()
        resp = QuickSettingsResponse(values=quick, items=items)
        return ApiResponse[QuickSettingsResponse](success=True, data=resp)

    if action == "patch_idle":
        try:
            req = PatchIdleRequest.model_validate(payload)
        except Exception as e:
            return ApiResponse[IdleModeConfig](
                success=False,
                error=ErrorInfo(code="INVALID_PAYLOAD", message=str(e)),
            )
        patch_data: dict | None = req.patch
        if patch_data is None:
            return ApiResponse[IdleModeConfig](
                success=False,
                error=ErrorInfo(code="PATCH_REQUIRED", message="必须提供 patch"),
            )
        config = cfg_service.get_options()
        idle: IdleModeConfig = config.idle
        updated_idle = idle.model_copy(update=patch_data)
        config.idle = updated_idle
        try:
            cfg_service.save()
        except Exception as e:
            return ApiResponse[IdleModeConfig](
                success=False,
                error=ErrorInfo(code="CONFIG_VALIDATION_ERROR", message=str(e)),
            )
        return ApiResponse[IdleModeConfig](success=True, data=updated_idle)

    raise HTTPException(status_code=404, detail="Unknown action")
