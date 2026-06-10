from .schema import (
    BaseConfig,
    PurchaseConfig,
    ActivityFundsConfig,
    PresentsConfig,
    AssignmentConfig,
    ContestConfig,
    ProduceConfig,
    MissionRewardConfig,
    ClubRewardConfig,
    UpgradeSupportCardConfig,
    CapsuleToysConfig,
    TraceConfig,
    StartGameConfig,
    EndGameConfig,
    MiscConfig,
    IdleModeConfig,
)
from .const import (
    ConfigEnum,
    Priority,
    APShopItems,
    DailyMoneyShopItems,
    ProduceAction,
    RecommendCardDetectionMode,
)
from ..kaa_context import conf

# 配置升级逻辑
from .migrations import LATEST_VERSION, upgrade_config
from .migration import get_deferred_messages, MigrationMessage

__all__ = [
    # schema 导出
    "BaseConfig",
    "PurchaseConfig",
    "ActivityFundsConfig",
    "PresentsConfig",
    "AssignmentConfig",
    "ContestConfig",
    "ProduceConfig",
    "MissionRewardConfig",
    "ClubRewardConfig",
    "UpgradeSupportCardConfig",
    "CapsuleToysConfig",
    "TraceConfig",
    "StartGameConfig",
    "EndGameConfig",
    "MiscConfig",
    "IdleModeConfig",
    "conf",
    # const 导出
    "ConfigEnum",
    "Priority",
    "APShopItems",
    "DailyMoneyShopItems",
    "ProduceAction",
    "RecommendCardDetectionMode",
    # upgrade 导出
    "upgrade_config",
    "LATEST_VERSION",
    "get_deferred_messages",
    "MigrationMessage",
]