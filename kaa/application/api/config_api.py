from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from kaa.application.ui.facade import KaaFacade
from kaa.application.services.config_service import ConfigService
from kaa.config.schema import BaseConfig, IdleModeConfig
from kotonebot.config.manager import RootConfig
from kotonebot.config.base_config import UserConfig

from .models import (
    ApiResponse,
    ErrorInfo,
    QuickSettingsDto,
    QuickSettingsPatch,
)
from .tasks_api import get_facade

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

    if action == "get_current_user":
        user_cfg: UserConfig[BaseConfig] = cfg_service.get_current_user_config()
        return ApiResponse[UserConfig[BaseConfig]](success=True, data=user_cfg)

    if action == "get_options":
        options: BaseConfig = cfg_service.get_options()
        return ApiResponse[BaseConfig](success=True, data=options)

    if action == "get_quick":
        options = cfg_service.get_options()
        quick = _get_quick_from_options(options)
        return ApiResponse[QuickSettingsDto](success=True, data=quick)

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
        options_data = payload.get("options")
        if options_data is None:
            return ApiResponse[BaseConfig](
                success=False,
                error=ErrorInfo(code="OPTIONS_REQUIRED", message="必须提供 options"),
            )
        current_user = cfg_service.get_current_user_config()
        current_user.options = BaseConfig.model_validate(options_data)
        try:
            cfg_service.save()
        except Exception as e:
            return ApiResponse[BaseConfig](
                success=False,
                error=ErrorInfo(code="CONFIG_VALIDATION_ERROR", message=str(e)),
            )
        return ApiResponse[BaseConfig](success=True, data=current_user.options)

    if action == "patch_options":
        patch_data: dict | None = payload.get("patch")
        if patch_data is None:
            return ApiResponse[BaseConfig](
                success=False,
                error=ErrorInfo(code="PATCH_REQUIRED", message="必须提供 patch"),
            )
        options = cfg_service.get_options()
        # 浅合并：仅覆盖顶层字段
        for key, value in patch_data.items():
            if hasattr(options, key) and value is not None:
                setattr(options, key, value)
        try:
            cfg_service.save()
        except Exception as e:
            return ApiResponse[BaseConfig](
                success=False,
                error=ErrorInfo(code="CONFIG_VALIDATION_ERROR", message=str(e)),
            )
        return ApiResponse[BaseConfig](success=True, data=options)

    if action == "patch_quick":
        patch_raw = payload.get("patch") or {}
        patch = QuickSettingsPatch.model_validate(patch_raw)
        options = cfg_service.get_options()
        _apply_quick_patch(options, patch)
        try:
            cfg_service.save()
        except Exception as e:
            return ApiResponse[QuickSettingsDto](
                success=False,
                error=ErrorInfo(code="CONFIG_VALIDATION_ERROR", message=str(e)),
            )
        quick = _get_quick_from_options(options)
        return ApiResponse[QuickSettingsDto](success=True, data=quick)

    if action == "patch_idle":
        patch_data: dict | None = payload.get("patch")
        if patch_data is None:
            return ApiResponse[IdleModeConfig](
                success=False,
                error=ErrorInfo(code="PATCH_REQUIRED", message="必须提供 patch"),
            )
        options = cfg_service.get_options()
        idle: IdleModeConfig = options.idle
        updated_idle = idle.model_copy(update=patch_data)
        options.idle = updated_idle
        try:
            cfg_service.save()
        except Exception as e:
            return ApiResponse[IdleModeConfig](
                success=False,
                error=ErrorInfo(code="CONFIG_VALIDATION_ERROR", message=str(e)),
            )
        return ApiResponse[IdleModeConfig](success=True, data=updated_idle)

    raise HTTPException(status_code=404, detail="Unknown action")
