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
    conf,
)
from .const import (
    ConfigEnum,
    Priority,
    APShopItems,
    DailyMoneyShopItems,
    ProduceAction,
    RecommendCardDetectionMode,
)

# 配置升级逻辑
from .upgrade import upgrade_config
from .migrations import MIGRATION_REGISTRY, LATEST_VERSION

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
    "migrations",
    "MIGRATION_REGISTRY",
    "LATEST_VERSION",
]