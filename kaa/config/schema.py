from typing import TypeVar, Literal, Sequence
from pydantic import BaseModel, ConfigDict

from kotonebot import config
from kaa.config.produce import ProduceSolution, ProduceSolutionManager
from kaa.errors import NoProduceSolutionSelectedError
from .const import (
    ConfigEnum,
    Priority,
    APShopItems,
    DailyMoneyShopItems,
)

T = TypeVar('T')

class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)

class PurchaseConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用商店购买"""
    money_enabled: bool = False
    """是否启用金币购买"""
    money_items: list[DailyMoneyShopItems] = []
    """金币商店要购买的物品"""
    money_refresh: bool = True
    """
    是否使用每日一次免费刷新金币商店。
    """
    ap_enabled: bool = False
    """是否启用AP购买"""
    ap_items: Sequence[Literal[0, 1, 2, 3]] = []
    """AP商店要购买的物品"""


class ActivityFundsConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用收取活动费"""


class PresentsConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用收取礼物"""


class AssignmentConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用工作"""

    mini_live_reassign_enabled: bool = False
    """是否启用重新分配 MiniLive"""
    mini_live_duration: Literal[4, 6, 12] = 12
    """MiniLive 工作时长"""

    online_live_reassign_enabled: bool = False
    """是否启用重新分配 OnlineLive"""
    online_live_duration: Literal[4, 6, 12] = 12
    """OnlineLive 工作时长"""


class ContestConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用竞赛"""

    select_which_contestant: Literal[1, 2, 3] = 1
    """选择第几个挑战者"""

    when_no_set: Literal['remind', 'wait', 'auto_set', 'auto_set_silent'] = 'remind'
    """竞赛队伍未编成时应该：remind=通知我并跳过竞赛，wait=提醒我并等待手动编成，auto_set=使用自动编成并提醒，auto_set_silent=使用自动编成不提醒"""


class ProduceConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用培育"""
    selected_solution_id: str | None = None
    """选中的培育方案ID"""
    produce_count: int = 1
    """培育的次数。"""
    produce_timeout_cd: int = 60
    """推荐卡检测用时上限；若超时，则随机选择卡片打出。单位为秒，最少为20sec，DMM用户可以设置为30sec"""
    interrupt_timeout: int = 90
    """检测超时时间。单位秒。"""
    enable_fever_month: Literal['on', 'off', 'ignore'] = 'ignore'
    """
    是否自动启用强化月间。

    * on: 自动启用
    * off: 自动禁用
    * ignore: 不改变当前状态
    """

class MissionRewardConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用领取任务奖励"""

class ClubRewardConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用领取社团奖励"""

    selected_note: DailyMoneyShopItems = DailyMoneyShopItems.AnomalyNoteVisual
    """想在社团奖励中获取到的笔记"""

class UpgradeSupportCardConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用支援卡升级"""

class CapsuleToysConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用扭蛋机"""

    friend_capsule_toys_count: int = 0
    """好友扭蛋机次数"""

    sense_capsule_toys_count: int = 0
    """感性扭蛋机次数"""

    logic_capsule_toys_count: int = 0
    """理性扭蛋机次数"""

    anomaly_capsule_toys_count: int = 0
    """非凡扭蛋机次数"""

class TraceConfig(ConfigBaseModel):
    recommend_card_detection: bool = False
    """跟踪推荐卡检测"""

class StartGameConfig(ConfigBaseModel):
    enabled: bool = True
    """是否启用自动启动游戏。默认为True"""

    start_through_kuyo: bool = False
    """是否通过Kuyo来启动游戏"""

    game_package_name: str = 'com.bandainamcoent.idolmaster_gakuen'
    """游戏包名"""

    kuyo_package_name: str = 'org.kuyo.game'
    """Kuyo包名"""

    disable_gakumas_localify: bool = False
    """
    自动检测并禁用 Gakumas Localify 汉化插件。

    （目前仅对 DMM 版有效。）
    """

    dmm_game_path: str | None = None
    """
    DMM 版游戏路径。若不填写，会自动检测。

    例：`F:\\Games\\gakumas\\gakumas.exe`
    """

    dmm_bypass: bool = False
    """绕过 DMM 启动器直接启动游戏（实验性）"""

class EndGameConfig(ConfigBaseModel):
    exit_kaa: bool = False
    """退出 kaa"""
    kill_game: bool = False
    """关闭游戏"""
    kill_dmm: bool = False
    """关闭 DMMGamePlayer"""
    kill_emulator: bool = False
    """关闭模拟器"""
    shutdown: bool = False
    """关闭系统"""
    hibernate: bool = False
    """休眠系统"""
    restore_gakumas_localify: bool = False
    """
    恢复 Gakumas Localify 汉化插件状态至启动前。通常与
    `disable_gakumas_localify` 配对使用。

    （目前仅对 DMM 版有效。）
    """

class MiscConfig(ConfigBaseModel):
    check_update: Literal['never', 'startup'] = 'startup'
    """
    检查更新时机。

    * never: 从不检查更新。
    * startup: 启动时检查更新。
    """
    auto_install_update: bool = True
    """
    是否自动安装更新。

    若启用，则每次自动检查更新时若有新版本会自动安装，否则只是会提示。
    """
    expose_to_lan: bool = False
    """
    是否允许局域网访问 Web 界面。

    启用后，局域网内的其他设备可以通过本机 IP 地址访问 Web 界面。
    """
    update_channel: Literal['release', 'beta'] = 'release'
    """
    更新通道。

    * release: 只使用稳定版。
    * beta: 包含预发布版本（如 alpha/beta/rc）。
    """

class IdleModeConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用闲置挂机（任意键暂停、闲置自动恢复）"""
    idle_seconds: int = 30
    """暂停状态下，超过该闲置秒数将自动恢复"""
    minimize_on_pause: bool = True
    """按键触发暂停时最小化游戏窗口"""

class BaseConfig(ConfigBaseModel):
    purchase: PurchaseConfig = PurchaseConfig()
    """商店购买配置"""

    activity_funds: ActivityFundsConfig = ActivityFundsConfig()
    """活动费配置"""

    presents: PresentsConfig = PresentsConfig()
    """收取礼物配置"""

    assignment: AssignmentConfig = AssignmentConfig()
    """工作配置"""

    contest: ContestConfig = ContestConfig()
    """竞赛配置"""

    produce: ProduceConfig = ProduceConfig()
    """培育配置"""

    mission_reward: MissionRewardConfig = MissionRewardConfig()
    """领取任务奖励配置"""

    club_reward: ClubRewardConfig = ClubRewardConfig()
    """领取社团奖励配置"""

    upgrade_support_card: UpgradeSupportCardConfig = UpgradeSupportCardConfig()
    """支援卡升级配置"""

    capsule_toys: CapsuleToysConfig = CapsuleToysConfig()
    """扭蛋机配置"""

    trace: TraceConfig = TraceConfig()
    """跟踪配置"""

    start_game: StartGameConfig = StartGameConfig()
    """启动游戏配置"""

    end_game: EndGameConfig = EndGameConfig()
    """关闭游戏配置"""

    misc: MiscConfig = MiscConfig()
    """杂项配置"""

    idle: IdleModeConfig = IdleModeConfig()
    """闲置挂机配置"""


def conf() -> BaseConfig:
    """获取当前配置数据"""
    c = config.to(BaseConfig).current
    return c.options

def produce_solution() -> ProduceSolution:
    """获取当前培育方案"""
    id = conf().produce.selected_solution_id
    if id is None:
        raise NoProduceSolutionSelectedError()
    # TODO: 这里需要缓存，不能每次都从磁盘读取
    return ProduceSolutionManager().read(id)
