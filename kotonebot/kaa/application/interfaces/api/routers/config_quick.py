from fastapi import APIRouter
from ..schemas import QuickSettings, SaveResult, EndAction
from kotonebot.config.manager import load_config, save_config
from kotonebot.kaa.config import BaseConfig
from kotonebot.config.base_config import RootConfig

router = APIRouter(tags=["config"]) 


@router.patch("/config/quick", response_model=QuickSettings)
async def patch_config_quick(patch: QuickSettings) -> QuickSettings:
    root = load_config("config.json", type=BaseConfig)
    user = root.user_configs[0]
    # 映射 QuickSettings 到 BaseConfig 字段
    user.options.purchase.money_enabled = patch.purchase
    user.options.assignment.enabled = patch.assignment
    user.options.contest.enabled = patch.contest
    user.options.produce.enabled = patch.produce
    user.options.mission_reward.enabled = patch.mission_reward
    user.options.club_reward.enabled = patch.club_reward
    user.options.activity_funds.enabled = patch.activity_funds
    user.options.presents.enabled = patch.presents
    user.options.capsule_toys.enabled = patch.capsule_toys
    user.options.upgrade_support_card.enabled = patch.upgrade_support_card
    save_config(root, "config.json")
    return patch


@router.put("/config/end_action", response_model=SaveResult)
async def put_config_end_action(action: EndAction) -> SaveResult:
    try:
        root = load_config("config.json", type=BaseConfig)
        user = root.user_configs[0]
        # 简化映射：仅设置 shutdown/hibernate；do nothing 清空
        user.options.end_game.shutdown = (action == EndAction.SHUTDOWN)
        user.options.end_game.hibernate = (action == EndAction.HIBERNATE)
        # 其他联动按旧 UI 语义保留默认
        save_config(root, "config.json")
        return SaveResult(ok=True, message="结束动作已保存")
    except Exception as e:
        return SaveResult(ok=False, message=f"保存失败：{e}") 