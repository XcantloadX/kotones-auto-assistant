import os
import json
import shutil
from importlib import resources
from typing import Literal, TypeVar, Any, Sequence
from typing_extensions import assert_never
from enum import IntEnum, Enum

from pydantic import BaseModel, ConfigDict

# TODO: from kotonebot import config (context) 会和 kotonebot.config 冲突
from kotonebot import logging
from kotonebot.backend.context import config

logger = logging.getLogger(__name__)

T = TypeVar('T')
class ConfigEnum(Enum):
    def display(self) -> str:
        return self.value[1]

class Priority(IntEnum):
    """
    任务优先级。数字越大，优先级越高，越先执行。
    """
    START_GAME = 1
    DEFAULT = 0
    CLAIM_MISSION_REWARD = -1
    END_GAME = -2

class APShopItems(IntEnum):
    PRODUCE_PT_UP = 0
    """获取支援强化 Pt 提升"""
    PRODUCE_NOTE_UP = 1
    """获取笔记数提升"""
    RECHALLENGE = 2
    """再挑战券"""
    REGENERATE_MEMORY = 3
    """回忆再生成券"""

class DailyMoneyShopItems(IntEnum):
    """日常商店物品"""
    Recommendations = -1
    """所有推荐商品"""
    LessonNote = 0
    """レッスンノート"""
    VeteranNote = 1
    """ベテランノート"""
    SupportEnhancementPt = 2
    """サポート強化Pt 支援强化Pt"""
    SenseNoteVocal = 3
    """センスノート（ボーカル）感性笔记（声乐）"""
    SenseNoteDance = 4
    """センスノート（ダンス）感性笔记（舞蹈）"""
    SenseNoteVisual = 5
    """センスノート（ビジュアル）感性笔记（形象）"""
    LogicNoteVocal = 6
    """ロジックノート（ボーカル）理性笔记（声乐）"""
    LogicNoteDance = 7
    """ロジックノート（ダンス）理性笔记（舞蹈）"""
    LogicNoteVisual = 8
    """ロジックノート（ビジュアル）理性笔记（形象）"""
    AnomalyNoteVocal = 9
    """アノマリーノート（ボーカル）非凡笔记（声乐）"""
    AnomalyNoteDance = 10
    """アノマリーノート（ダンス）非凡笔记（舞蹈）"""
    AnomalyNoteVisual = 11
    """アノマリーノート（ビジュアル）非凡笔记（形象）"""
    RechallengeTicket = 12
    """再挑戦チケット 重新挑战券"""
    RecordKey = 13
    """記録の鍵 解锁交流的物品"""

    # 碎片
    IdolPiece_倉本千奈_WonderScale = 14
    """倉本千奈 WonderScale 碎片"""
    IdolPiece_篠泽广_光景 = 15
    """篠泽广 光景 碎片"""
    IdolPiece_紫云清夏_TameLieOneStep = 16
    """紫云清夏 Tame-Lie-One-Step 碎片"""
    IdolPiece_葛城リーリヤ_白線 = 17
    """葛城リーリヤ 白線 碎片"""
    IdolPiece_姫崎薪波_cIclumsy_trick = 18
    """姫崎薪波 cIclumsy trick 碎片"""
    IdolPiece_花海咲季_FightingMyWay = 19
    """花海咲季 FightingMyWay 碎片"""
    IdolPiece_藤田ことね_世界一可愛い私 = 20
    """藤田ことね 世界一可愛い私 碎片"""
    IdolPiece_花海佑芽_TheRollingRiceball = 21
    """花海佑芽 The Rolling Riceball 碎片"""
    IdolPiece_月村手毬_LunaSayMaybe = 22
    """月村手毬 Luna say maybe 碎片"""

    @classmethod
    def to_ui_text(cls, item: "DailyMoneyShopItems") -> str:
        """获取枚举值对应的UI显示文本"""
        match item:
            case cls.Recommendations:
                return "所有推荐商品"
            case cls.LessonNote:
                return "课程笔记"
            case cls.VeteranNote:
                return "老手笔记"
            case cls.SupportEnhancementPt:
                return "支援强化点数"
            case cls.SenseNoteVocal:
                return "感性笔记（声乐）"
            case cls.SenseNoteDance:
                return "感性笔记（舞蹈）"
            case cls.SenseNoteVisual:
                return "感性笔记（形象）"
            case cls.LogicNoteVocal:
                return "理性笔记（声乐）"
            case cls.LogicNoteDance:
                return "理性笔记（舞蹈）"
            case cls.LogicNoteVisual:
                return "理性笔记（形象）"
            case cls.AnomalyNoteVocal:
                return "非凡笔记（声乐）"
            case cls.AnomalyNoteDance:
                return "非凡笔记（舞蹈）"
            case cls.AnomalyNoteVisual:
                return "非凡笔记（形象）"
            case cls.RechallengeTicket:
                return "重新挑战券"
            case cls.RecordKey:
                return "记录钥匙"
            case cls.IdolPiece_倉本千奈_WonderScale:
                return "倉本千奈 WonderScale 碎片"
            case cls.IdolPiece_篠泽广_光景:
                return "篠泽广 光景 碎片"
            case cls.IdolPiece_紫云清夏_TameLieOneStep:
                return "紫云清夏 Tame-Lie-One-Step 碎片"
            case cls.IdolPiece_葛城リーリヤ_白線:
                return "葛城リーリヤ 白線 碎片"
            case cls.IdolPiece_姫崎薪波_cIclumsy_trick:
                return "姫崎薪波 cIclumsy trick 碎片"
            case cls.IdolPiece_花海咲季_FightingMyWay:
                return "花海咲季 FightingMyWay 碎片"
            case cls.IdolPiece_藤田ことね_世界一可愛い私:
                return "藤田ことね 世界一可愛い私 碎片"
            case cls.IdolPiece_花海佑芽_TheRollingRiceball:
                return "花海佑芽 The Rolling Riceball 碎片"
            case cls.IdolPiece_月村手毬_LunaSayMaybe:
                return "月村手毬 Luna say maybe 碎片"
            case _:
                assert_never(item)

    @classmethod
    def all(cls) -> list[tuple[str, 'DailyMoneyShopItems']]:
        """获取所有枚举值及其对应的UI显示文本"""
        return [(cls.to_ui_text(item), item) for item in cls]

    @classmethod
    def _is_note(cls, item: 'DailyMoneyShopItems') -> bool:
        """判断是否为笔记"""
        return 'Note' in item.name and not item.name.startswith('Note') and not item.name.endswith('Note')

    @classmethod
    def note_items(cls) -> list[tuple[str, 'DailyMoneyShopItems']]:
        """获取所有枚举值及其对应的UI显示文本"""
        return [(cls.to_ui_text(item), item) for item in cls if cls._is_note(item)]

    def to_resource(self):
        from kotonebot.kaa.tasks import R
        match self:
            case DailyMoneyShopItems.Recommendations:
                return R.Daily.TextShopRecommended
            case DailyMoneyShopItems.LessonNote:
                return R.Shop.ItemLessonNote
            case DailyMoneyShopItems.VeteranNote:
                return R.Shop.ItemVeteranNote
            case DailyMoneyShopItems.SupportEnhancementPt:
                return R.Shop.ItemSupportEnhancementPt
            case DailyMoneyShopItems.SenseNoteVocal:
                return R.Shop.ItemSenseNoteVocal
            case DailyMoneyShopItems.SenseNoteDance:
                return R.Shop.ItemSenseNoteDance
            case DailyMoneyShopItems.SenseNoteVisual:
                return R.Shop.ItemSenseNoteVisual
            case DailyMoneyShopItems.LogicNoteVocal:
                return R.Shop.ItemLogicNoteVocal
            case DailyMoneyShopItems.LogicNoteDance:
                return R.Shop.ItemLogicNoteDance
            case DailyMoneyShopItems.LogicNoteVisual:
                return R.Shop.ItemLogicNoteVisual
            case DailyMoneyShopItems.AnomalyNoteVocal:
                return R.Shop.ItemAnomalyNoteVocal
            case DailyMoneyShopItems.AnomalyNoteDance:
                return R.Shop.ItemAnomalyNoteDance
            case DailyMoneyShopItems.AnomalyNoteVisual:
                return R.Shop.ItemAnomalyNoteVisual
            case DailyMoneyShopItems.RechallengeTicket:
                return R.Shop.ItemRechallengeTicket
            case DailyMoneyShopItems.RecordKey:
                return R.Shop.ItemRecordKey
            case DailyMoneyShopItems.IdolPiece_倉本千奈_WonderScale:
                return R.Shop.IdolPiece.倉本千奈_WonderScale
            case DailyMoneyShopItems.IdolPiece_篠泽广_光景:
                return R.Shop.IdolPiece.篠泽广_光景
            case DailyMoneyShopItems.IdolPiece_紫云清夏_TameLieOneStep:
                return R.Shop.IdolPiece.紫云清夏_TameLieOneStep
            case DailyMoneyShopItems.IdolPiece_葛城リーリヤ_白線:
                return R.Shop.IdolPiece.葛城リーリヤ_白線
            case DailyMoneyShopItems.IdolPiece_姫崎薪波_cIclumsy_trick:
                return R.Shop.IdolPiece.姫崎薪波_cIclumsy_trick
            case DailyMoneyShopItems.IdolPiece_花海咲季_FightingMyWay:
                return R.Shop.IdolPiece.花海咲季_FightingMyWay
            case DailyMoneyShopItems.IdolPiece_藤田ことね_世界一可愛い私:
                return R.Shop.IdolPiece.藤田ことね_世界一可愛い私
            case DailyMoneyShopItems.IdolPiece_花海佑芽_TheRollingRiceball:
                return R.Shop.IdolPiece.花海佑芽_TheRollingRiceball
            case DailyMoneyShopItems.IdolPiece_月村手毬_LunaSayMaybe:
                return R.Shop.IdolPiece.月村手毬_LunaSayMaybe
            case _:
                assert_never(self)

class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)

class PurchaseConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用商店购买"""
    money_enabled: bool = False
    """是否启用金币购买"""
    money_items: list[DailyMoneyShopItems] = []
    """金币商店要购买的物品"""
    money_refresh_on: Literal['never', 'not_found', 'always'] = 'never'
    """
    金币商店刷新逻辑。

    * never: 从不刷新。
    * not_found: 仅当要购买的物品不存在时刷新。
    * always: 总是刷新。
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

class ProduceAction(Enum):
    RECOMMENDED = 'recommended'
    VISUAL = 'visual'
    VOCAL = 'vocal'
    DANCE = 'dance'
    # VISUAL_SP = 'visual_sp'
    # VOCAL_SP = 'vocal_sp'
    # DANCE_SP = 'dance_sp'
    OUTING = 'outing'
    STUDY = 'study'
    ALLOWANCE = 'allowance'
    REST = 'rest'
    CONSULT = 'consult'
    # TODO: NIA 要和 HAJIME 分开
    PROMOTION = 'promotion'
    CARE_PACKAGE = 'care_package'
    SPECIAL_TRAINING = 'special_training'

    @property
    def display_name(self):
        MAP = {
            ProduceAction.RECOMMENDED: '推荐行动',
            ProduceAction.VISUAL: '形象课程',
            ProduceAction.VOCAL: '声乐课程',
            ProduceAction.DANCE: '舞蹈课程',
            ProduceAction.OUTING: '外出（おでかけ）',
            ProduceAction.STUDY: '文化课（授業）',
            ProduceAction.ALLOWANCE: '活动支给（活動支給）',
            ProduceAction.REST: '休息',
            ProduceAction.CONSULT: '咨询（相談）',
            ProduceAction.PROMOTION: '营业（営業）',
            ProduceAction.CARE_PACKAGE: '粉丝礼物（差し入れ）',
            ProduceAction.SPECIAL_TRAINING: '特别指导（特別指導）',
        }
        return MAP[self]

class RecommendCardDetectionMode(Enum):
    NORMAL = 'normal'
    STRICT = 'strict'

    @property
    def display_name(self):
        MAP = {
            RecommendCardDetectionMode.NORMAL: '正常模式',
            RecommendCardDetectionMode.STRICT: '严格模式',
        }
        return MAP[self]

class NiaPromotionType(Enum):
    HEAL = 'heal'
    POINT = 'point'
    DRINK = 'drink'
    SKILL_CARD = 'p_skill_card'

    @property
    def display_name(self):
        match self:
            case NiaPromotionType.HEAL:
                return '体力恢复'
            case NiaPromotionType.POINT:
                return 'P 点数'
            case NiaPromotionType.DRINK:
                return 'P 饮料'
            case NiaPromotionType.SKILL_CARD:
                return 'P 技能卡'
            case _:
                assert_never(self)

class NiaPromotionSkillCardOption(Enum):
    GOOD_CONDITION = "good_condition"
    """好调"""
    FOCUS = "focus"
    """集中"""
    GOOD_IMPRESSION = "good_impression"
    """好印象"""
    MOTIVATION = "motivation"
    """干劲"""
    CONFIDENCE_CONSERVATION = "confidence_conservation"
    """强气 温存"""
    FULL_POWER_CONSERVATION = "full_power_conservation"
    """全力 温存"""
    ACTIVE = "active"
    """主动技能卡"""
    MENTAL = "mental"
    """精神技能卡"""

    @property
    def search_text(self):
        match self:
            case NiaPromotionSkillCardOption.GOOD_CONDITION:
                return '好調'
            case NiaPromotionSkillCardOption.FOCUS:
                return '集中'
            case NiaPromotionSkillCardOption.GOOD_IMPRESSION:
                return '好印象'
            case NiaPromotionSkillCardOption.MOTIVATION:
                return 'やる気'
            case NiaPromotionSkillCardOption.CONFIDENCE_CONSERVATION:
                return '強気'
            case NiaPromotionSkillCardOption.FULL_POWER_CONSERVATION:
                return '全力'
            case NiaPromotionSkillCardOption.ACTIVE:
                return 'アクティブ'
            case NiaPromotionSkillCardOption.MENTAL:
                return 'メンタル'
            case _:
                assert_never(self)

    @property
    def display_name(self) -> str:
        match self:
            case NiaPromotionSkillCardOption.GOOD_CONDITION:
                return "好调"
            case NiaPromotionSkillCardOption.FOCUS:
                return "集中"
            case NiaPromotionSkillCardOption.GOOD_IMPRESSION:
                return "好印象"
            case NiaPromotionSkillCardOption.MOTIVATION:
                return "干劲"
            case NiaPromotionSkillCardOption.CONFIDENCE_CONSERVATION:
                return "强气 温存"
            case NiaPromotionSkillCardOption.FULL_POWER_CONSERVATION:
                return "全力 温存"
            case NiaPromotionSkillCardOption.ACTIVE:
                return "主动"
            case NiaPromotionSkillCardOption.MENTAL:
                return "精神"
            case _:
                assert_never(self)

class NiaFirstAuditionType(IntEnum):
    """NIA 第一次试镜 试镜类型"""
    LEVEL_2 = 2
    """MusicOrder"""
    LEVEL_1 = 1
    """HarmonyToNight"""
    LEVEL_0 = 0
    """MeroBang!"""
    
    @property
    def display_name(self):
        match self:
            case NiaFirstAuditionType.LEVEL_2:
                return 'MusicOrder（无条件）'
            case NiaFirstAuditionType.LEVEL_1:
                return 'HarmonyToNight（4,000 以上）'
            case NiaFirstAuditionType.LEVEL_0:
                return 'MeroBang!（9,000 以上）'
            case _:
                assert_never(self)
                
    @property
    def template(self):
        from kotonebot.kaa.tasks import R
        match self:
            case NiaFirstAuditionType.LEVEL_2:
                return R.InPurodyuusu.TextAuditionMusicOrder
            case NiaFirstAuditionType.LEVEL_1:
                return R.InPurodyuusu.TextAuditionHarmonyToNight
            case NiaFirstAuditionType.LEVEL_0:
                return R.InPurodyuusu.TextAuditionMeroBang
            case _:
                assert_never(self)

class NiaSecondAuditionType(IntEnum):
    """NIA 第二次试镜 试镜类型"""
    LEVEL_0 = 0
    """GALAXY ミュージック"""
    LEVEL_1 = 1
    """POPFair"""
    LEVEL_2 = 2
    """MelodyJourney"""
    
    @property
    def display_name(self):
        match self:
            case NiaSecondAuditionType.LEVEL_0:
                return 'GALAXY ミュージック（25,000 以上）'
            case NiaSecondAuditionType.LEVEL_1:
                return 'POPFair（14,000 以上）'
            case NiaSecondAuditionType.LEVEL_2:
                return 'MelodyJourney（无条件）'
            case _:
                assert_never(self)
                
    @property
    def template(self):
        from kotonebot.kaa.tasks import R
        match self:
            case NiaSecondAuditionType.LEVEL_0:
                return R.InPurodyuusu.TextAuditionGalaxyMusic
            case NiaSecondAuditionType.LEVEL_1:
                return R.InPurodyuusu.TextAuditionPopFair
            case NiaSecondAuditionType.LEVEL_2:
                return R.InPurodyuusu.TextAuditionMelodyJourney
            case _:
                assert_never(self)

class NiaFinalAuditionType(IntEnum):
    """NIA 最终试镜 试镜类型"""
    LEVEL_0 = 0
    """FINALE"""
    LEVEL_1 = 1
    """QUARTET"""
    LEVEL_2 = 2
    """IDOLBigup!"""
    LEVEL_3 = 3
    """SingleCut"""
    
    @property
    def display_name(self):
        match self:
            case NiaFinalAuditionType.LEVEL_0:
                return 'FINALE（57,000 以上）'
            case NiaFinalAuditionType.LEVEL_1:
                return 'QUARTET（40,000 以上）'
            case NiaFinalAuditionType.LEVEL_2:
                return 'IDOLBigup!（28,000 以上）'
            case NiaFinalAuditionType.LEVEL_3:
                return 'SingleCut（无条件）'
            case _:
                assert_never(self)
                
    @property
    def template(self):
        from kotonebot.kaa.tasks import R
        match self:
            case NiaFinalAuditionType.LEVEL_0:
                return R.InPurodyuusu.TextAuditionFinale
            case NiaFinalAuditionType.LEVEL_1:
                return R.InPurodyuusu.TextAuditionQuartet
            case NiaFinalAuditionType.LEVEL_2:
                return R.InPurodyuusu.TextAuditionIdolBigup
            case NiaFinalAuditionType.LEVEL_3:
                return R.InPurodyuusu.TextAuditionSingleCut
            case _:
                assert_never(self)

ProduceMode = Literal['regular', 'pro', 'master', 'nia-pro']
ProduceWeek = Literal[
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28,
]
class ProduceConfig(ConfigBaseModel):
    enabled: bool = False
    """是否启用培育"""
    mode: ProduceMode = 'regular'
    """
    培育模式。
    进行一次 REGULAR 培育需要 ~30min，进行一次 PRO 培育需要 ~1h（具体视设备性能而定）。
    """
    produce_count: int = 1
    """培育的次数。"""
    idols: list[str] = []
    """
    要培育偶像的 IdolCardSkin.id。将会按顺序循环选择培育。
    """
    memory_sets: list[int] = []
    """要使用的回忆编成编号，从 1 开始。将会按顺序循环选择使用。"""
    support_card_sets: list[int] = []
    """要使用的支援卡编成编号，从 1 开始。将会按顺序循环选择使用。"""
    auto_set_memory: bool = False
    """是否自动编成回忆。此选项优先级高于回忆编成编号。"""
    auto_set_support_card: bool = False
    """是否自动编成支援卡。此选项优先级高于支援卡编成编号。"""
    use_pt_boost: bool = False
    """是否使用支援强化 Pt 提升。"""
    use_note_boost: bool = False
    """是否使用笔记数提升。"""
    follow_producer: bool = False
    """是否关注租借了支援卡的制作人。"""
    self_study_lesson: Literal['dance', 'visual', 'vocal'] = 'dance'
    """自习课类型。"""
    prefer_lesson_ap: bool = False
    """
    优先 SP 课程。

    启用后，若出现 SP 课程，则会优先执行 SP 课程，而不是推荐课程。
    若出现多个 SP 课程，随机选择一个。
    """
    actions_order: list[ProduceAction] = [
        ProduceAction.RECOMMENDED,
        ProduceAction.VISUAL,
        ProduceAction.VOCAL,
        ProduceAction.DANCE,
        ProduceAction.PROMOTION,
        ProduceAction.CARE_PACKAGE,
        ProduceAction.SPECIAL_TRAINING,
        ProduceAction.ALLOWANCE,
        ProduceAction.OUTING,
        ProduceAction.STUDY,
        ProduceAction.CONSULT,
        ProduceAction.REST,
    ]
    """
    行动优先级

    每一周的行动将会按这里设置的优先级执行。
    """
    recommend_card_detection_mode: RecommendCardDetectionMode = RecommendCardDetectionMode.NORMAL
    """
    推荐卡检测模式

    严格模式下，识别速度会降低，但识别准确率会提高。
    """
    use_ap_drink: bool = False
    """
    AP 不足时自动使用 AP 饮料
    """
    skip_commu: bool = True
    """检测并跳过交流"""
    nia_promotion_type_order: list[NiaPromotionType] = [
        NiaPromotionType.SKILL_CARD,
        NiaPromotionType.POINT,
        NiaPromotionType.DRINK,
        NiaPromotionType.HEAL,
    ]
    """
    NIA 培育时的营业类型优先级顺序
    """
    nia_promotion_skill_card_option: NiaPromotionSkillCardOption = NiaPromotionSkillCardOption.GOOD_IMPRESSION
    """
    NIA 培育时的技能卡选项
    """
    nia_first_audition_type: NiaFirstAuditionType = NiaFirstAuditionType.LEVEL_2
    nia_second_audition_type: NiaSecondAuditionType = NiaSecondAuditionType.LEVEL_2
    nia_final_audition_type: NiaFinalAuditionType = NiaFinalAuditionType.LEVEL_3
    nia_rest_weeks: list[ProduceWeek] = []

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


def conf() -> BaseConfig:
    """获取当前配置数据"""
    c = config.to(BaseConfig).current
    return c.options

def sprite_path(path: str) -> str:
    standalone = os.path.join('kotonebot/kaa/sprites', path)
    if os.path.exists(standalone):
        return standalone
    return str(resources.files('kotonebot.kaa.sprites') / path)

def upgrade_config() -> str | None:
    """
    升级配置文件
    """
    if not os.path.exists('config.json'):
        return None
    with open('config.json', 'r', encoding='utf-8') as f:
        root = json.load(f)

    user_configs = root['user_configs']
    old_version = root['version']
    messages = []
    def upgrade_user_config(version: int, user_config: dict[str, Any]) -> int:
        nonlocal messages
        while True:
            match version:
                case 1:
                    logger.info('Upgrading config: v1 -> v2')
                    user_config, msg = upgrade_v1_to_v2(user_config['options'])
                    messages.append(msg)
                    version = 2
                case 2:
                    logger.info('Upgrading config: v2 -> v3')
                    user_config, msg = upgrade_v2_to_v3(user_config['options'])
                    messages.append(msg)
                    version = 3
                case 3:
                    logger.info('Upgrading config: v3 -> v4')
                    user_config, msg = upgrade_v3_to_v4(user_config['options'])
                    messages.append(msg)
                    version = 4
                case 4:
                    logger.info('Upgrading config: v4 -> v5')
                    user_config, msg = upgrade_v4_to_v5(user_config, user_config['options'])
                    messages.append(msg)
                    version = 5
                case _:
                    logger.info('No config upgrade needed.')
                    return version
    for user_config in user_configs:
        new_version = upgrade_user_config(old_version, user_config)
        root['version'] = new_version

    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(root, f, ensure_ascii=False, indent=4)
    return '\n'.join(messages)


倉本千奈_BASE = 0
十王星南_BASE = 100
姫崎莉波_BASE = 200
月村手毬_BASE = 300
有村麻央_BASE = 400
篠泽广_BASE = 500
紫云清夏_BASE = 600
花海佑芽_BASE = 700
花海咲季_BASE = 800
葛城リーリヤ_BASE = 900
藤田ことね_BASE = 1000

class PIdol(IntEnum):
    """
    P偶像。已废弃，仅为 upgrade_v1_to_v2()、upgrade_v2_to_v3() 而保留。
    """
    倉本千奈_Campusmode = 倉本千奈_BASE + 0
    倉本千奈_WonderScale = 倉本千奈_BASE + 1
    倉本千奈_ようこそ初星温泉 = 倉本千奈_BASE + 2
    倉本千奈_仮装狂騒曲 = 倉本千奈_BASE + 3
    倉本千奈_初心 = 倉本千奈_BASE + 4
    倉本千奈_学園生活 = 倉本千奈_BASE + 5
    倉本千奈_日々_発見的ステップ = 倉本千奈_BASE + 6
    倉本千奈_胸を張って一歩ずつ = 倉本千奈_BASE + 7

    十王星南_Campusmode = 十王星南_BASE + 0
    十王星南_一番星 = 十王星南_BASE + 1
    十王星南_学園生活 = 十王星南_BASE + 2
    十王星南_小さな野望 = 十王星南_BASE + 3

    姫崎莉波_clumsytrick = 姫崎莉波_BASE + 0
    姫崎莉波_私らしさのはじまり = 姫崎莉波_BASE + 1
    姫崎莉波_キミとセミブルー = 姫崎莉波_BASE + 2
    姫崎莉波_Campusmode = 姫崎莉波_BASE + 3
    姫崎莉波_LUV = 姫崎莉波_BASE + 4
    姫崎莉波_ようこそ初星温泉 = 姫崎莉波_BASE + 5
    姫崎莉波_ハッピーミルフィーユ = 姫崎莉波_BASE + 6
    姫崎莉波_初心 = 姫崎莉波_BASE + 7
    姫崎莉波_学園生活 = 姫崎莉波_BASE + 8

    月村手毬_Lunasaymaybe = 月村手毬_BASE + 0
    月村手毬_一匹狼 = 月村手毬_BASE + 1
    月村手毬_Campusmode = 月村手毬_BASE + 2
    月村手毬_アイヴイ = 月村手毬_BASE + 3
    月村手毬_初声 = 月村手毬_BASE + 4
    月村手毬_学園生活 = 月村手毬_BASE + 5
    月村手毬_仮装狂騒曲 = 月村手毬_BASE + 6

    有村麻央_Fluorite = 有村麻央_BASE + 0
    有村麻央_はじまりはカッコよく = 有村麻央_BASE + 1
    有村麻央_Campusmode = 有村麻央_BASE + 2
    有村麻央_FeelJewelDream = 有村麻央_BASE + 3
    有村麻央_キミとセミブルー = 有村麻央_BASE + 4
    有村麻央_初恋 = 有村麻央_BASE + 5
    有村麻央_学園生活 = 有村麻央_BASE + 6

    篠泽广_コントラスト = 篠泽广_BASE + 0
    篠泽广_一番向いていないこと = 篠泽广_BASE + 1
    篠泽广_光景 = 篠泽广_BASE + 2
    篠泽广_Campusmode = 篠泽广_BASE + 3
    篠泽广_仮装狂騒曲 = 篠泽广_BASE + 4
    篠泽广_ハッピーミルフィーユ = 篠泽广_BASE + 5
    篠泽广_初恋 = 篠泽广_BASE + 6
    篠泽广_学園生活 = 篠泽广_BASE + 7

    紫云清夏_TameLieOneStep = 紫云清夏_BASE + 0
    紫云清夏_カクシタワタシ = 紫云清夏_BASE + 1
    紫云清夏_夢へのリスタート = 紫云清夏_BASE + 2
    紫云清夏_Campusmode = 紫云清夏_BASE + 3
    紫云清夏_キミとセミブルー = 紫云清夏_BASE + 4
    紫云清夏_初恋 = 紫云清夏_BASE + 5
    紫云清夏_学園生活 = 紫云清夏_BASE + 6

    花海佑芽_WhiteNightWhiteWish = 花海佑芽_BASE + 0
    花海佑芽_学園生活 = 花海佑芽_BASE + 1
    花海佑芽_Campusmode = 花海佑芽_BASE + 2
    花海佑芽_TheRollingRiceball = 花海佑芽_BASE + 3
    花海佑芽_アイドル_はじめっ = 花海佑芽_BASE + 4

    花海咲季_BoomBoomPow = 花海咲季_BASE + 0
    花海咲季_Campusmode = 花海咲季_BASE + 1
    花海咲季_FightingMyWay = 花海咲季_BASE + 2
    花海咲季_わたしが一番 = 花海咲季_BASE + 3
    花海咲季_冠菊 = 花海咲季_BASE + 4
    花海咲季_初声 = 花海咲季_BASE + 5
    花海咲季_古今東西ちょちょいのちょい = 花海咲季_BASE + 6
    花海咲季_学園生活 = 花海咲季_BASE + 7

    葛城リーリヤ_一つ踏み出した先に = 葛城リーリヤ_BASE + 0
    葛城リーリヤ_白線 = 葛城リーリヤ_BASE + 1
    葛城リーリヤ_Campusmode = 葛城リーリヤ_BASE + 2
    葛城リーリヤ_WhiteNightWhiteWish = 葛城リーリヤ_BASE + 3
    葛城リーリヤ_冠菊 = 葛城リーリヤ_BASE + 4
    葛城リーリヤ_初心 = 葛城リーリヤ_BASE + 5
    葛城リーリヤ_学園生活 = 葛城リーリヤ_BASE + 6

    藤田ことね_カワイイ_はじめました = 藤田ことね_BASE + 0
    藤田ことね_世界一可愛い私 = 藤田ことね_BASE + 1
    藤田ことね_Campusmode = 藤田ことね_BASE + 2
    藤田ことね_YellowBigBang = 藤田ことね_BASE + 3
    藤田ことね_WhiteNightWhiteWish = 藤田ことね_BASE + 4
    藤田ことね_冠菊 = 藤田ことね_BASE + 5
    藤田ことね_初声 = 藤田ことね_BASE + 6
    藤田ことね_学園生活 = 藤田ことね_BASE + 7


def upgrade_v1_to_v2(options: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """
    v1 -> v2 变更：

    1. 将 PIdol 的枚举值改为整数
    """
    msg = ''
    # 转换 PIdol 的枚举值
    def map_idol(idol: list[str]) -> PIdol | None:
        logger.debug("Converting %s", idol)
        match idol:
            case ["倉本千奈", "Campus mode!!"]:
                return PIdol.倉本千奈_Campusmode
            case ["倉本千奈", "Wonder Scale"]:
                return PIdol.倉本千奈_WonderScale
            case ["倉本千奈", "ようこそ初星温泉"]:
                return PIdol.倉本千奈_ようこそ初星温泉
            case ["倉本千奈", "仮装狂騒曲"]:
                return PIdol.倉本千奈_仮装狂騒曲
            case ["倉本千奈", "初心"]:
                return PIdol.倉本千奈_初心
            case ["倉本千奈", "学園生活"]:
                return PIdol.倉本千奈_学園生活
            case ["倉本千奈", "日々、発見的ステップ！"]:
                return PIdol.倉本千奈_日々_発見的ステップ
            case ["倉本千奈", "胸を張って一歩ずつ"]:
                return PIdol.倉本千奈_胸を張って一歩ずつ
            case ["十王星南", "Campus mode!!"]:
                return PIdol.十王星南_Campusmode
            case ["十王星南", "一番星"]:
                return PIdol.十王星南_一番星
            case ["十王星南", "学園生活"]:
                return PIdol.十王星南_学園生活
            case ["十王星南", "小さな野望"]:
                return PIdol.十王星南_小さな野望
            case ["姫崎莉波", "clumsy trick"]:
                return PIdol.姫崎莉波_clumsytrick
            case ["姫崎莉波", "『私らしさ』のはじまり"]:
                return PIdol.姫崎莉波_私らしさのはじまり
            case ["姫崎莉波", "キミとセミブルー"]:
                return PIdol.姫崎莉波_キミとセミブルー
            case ["姫崎莉波", "Campus mode!!"]:
                return PIdol.姫崎莉波_Campusmode
            case ["姫崎莉波", "L.U.V"]:
                return PIdol.姫崎莉波_LUV
            case ["姫崎莉波", "ようこそ初星温泉"]:
                return PIdol.姫崎莉波_ようこそ初星温泉
            case ["姫崎莉波", "ハッピーミルフィーユ"]:
                return PIdol.姫崎莉波_ハッピーミルフィーユ
            case ["姫崎莉波", "初心"]:
                return PIdol.姫崎莉波_初心
            case ["姫崎莉波", "学園生活"]:
                return PIdol.姫崎莉波_学園生活
            case ["月村手毬", "Luna say maybe"]:
                return PIdol.月村手毬_Lunasaymaybe
            case ["月村手毬", "一匹狼"]:
                return PIdol.月村手毬_一匹狼
            case ["月村手毬", "Campus mode!!"]:
                return PIdol.月村手毬_Campusmode
            case ["月村手毬", "アイヴイ"]:
                return PIdol.月村手毬_アイヴイ
            case ["月村手毬", "初声"]:
                return PIdol.月村手毬_初声
            case ["月村手毬", "学園生活"]:
                return PIdol.月村手毬_学園生活
            case ["月村手毬", "仮装狂騒曲"]:
                return PIdol.月村手毬_仮装狂騒曲
            case ["有村麻央", "Fluorite"]:
                return PIdol.有村麻央_Fluorite
            case ["有村麻央", "はじまりはカッコよく"]:
                return PIdol.有村麻央_はじまりはカッコよく
            case ["有村麻央", "Campus mode!!"]:
                return PIdol.有村麻央_Campusmode
            case ["有村麻央", "Feel Jewel Dream"]:
                return PIdol.有村麻央_FeelJewelDream
            case ["有村麻央", "キミとセミブルー"]:
                return PIdol.有村麻央_キミとセミブルー
            case ["有村麻央", "初恋"]:
                return PIdol.有村麻央_初恋
            case ["有村麻央", "学園生活"]:
                return PIdol.有村麻央_学園生活
            case ["篠泽广", "コントラスト"]:
                return PIdol.篠泽广_コントラスト
            case ["篠泽广", "一番向いていないこと"]:
                return PIdol.篠泽广_一番向いていないこと
            case ["篠泽广", "光景"]:
                return PIdol.篠泽广_光景
            case ["篠泽广", "Campus mode!!"]:
                return PIdol.篠泽广_Campusmode
            case ["篠泽广", "仮装狂騒曲"]:
                return PIdol.篠泽广_仮装狂騒曲
            case ["篠泽广", "ハッピーミルフィーユ"]:
                return PIdol.篠泽广_ハッピーミルフィーユ
            case ["篠泽广", "初恋"]:
                return PIdol.篠泽广_初恋
            case ["篠泽广", "学園生活"]:
                return PIdol.篠泽广_学園生活
            case ["紫云清夏", "Tame-Lie-One-Step"]:
                return PIdol.紫云清夏_TameLieOneStep
            case ["紫云清夏", "カクシタワタシ"]:
                return PIdol.紫云清夏_カクシタワタシ
            case ["紫云清夏", "夢へのリスタート"]:
                return PIdol.紫云清夏_夢へのリスタート
            case ["紫云清夏", "Campus mode!!"]:
                return PIdol.紫云清夏_Campusmode
            case ["紫云清夏", "キミとセミブルー"]:
                return PIdol.紫云清夏_キミとセミブルー
            case ["紫云清夏", "初恋"]:
                return PIdol.紫云清夏_初恋
            case ["紫云清夏", "学園生活"]:
                return PIdol.紫云清夏_学園生活
            case ["花海佑芽", "White Night! White Wish!"]:
                return PIdol.花海佑芽_WhiteNightWhiteWish
            case ["花海佑芽", "学園生活"]:
                return PIdol.花海佑芽_学園生活
            case ["花海佑芽", "Campus mode!!"]:
                return PIdol.花海佑芽_Campusmode
            case ["花海佑芽", "The Rolling Riceball"]:
                return PIdol.花海佑芽_TheRollingRiceball
            case ["花海佑芽", "アイドル、はじめっ！"]:
                return PIdol.花海佑芽_アイドル_はじめっ
            case ["花海咲季", "Boom Boom Pow"]:
                return PIdol.花海咲季_BoomBoomPow
            case ["花海咲季", "Campus mode!!"]:
                return PIdol.花海咲季_Campusmode
            case ["花海咲季", "Fighting My Way"]:
                return PIdol.花海咲季_FightingMyWay
            case ["花海咲季", "わたしが一番！"]:
                return PIdol.花海咲季_わたしが一番
            case ["花海咲季", "冠菊"]:
                return PIdol.花海咲季_冠菊
            case ["花海咲季", "初声"]:
                return PIdol.花海咲季_初声
            case ["花海咲季", "古今東西ちょちょいのちょい"]:
                return PIdol.花海咲季_古今東西ちょちょいのちょい
            case ["花海咲季", "学園生活"]:
                return PIdol.花海咲季_学園生活
            case ["葛城リーリヤ", "一つ踏み出した先に"]:
                return PIdol.葛城リーリヤ_一つ踏み出した先に
            case ["葛城リーリヤ", "白線"]:
                return PIdol.葛城リーリヤ_白線
            case ["葛城リーリヤ", "Campus mode!!"]:
                return PIdol.葛城リーリヤ_Campusmode
            case ["葛城リーリヤ", "White Night! White Wish!"]:
                return PIdol.葛城リーリヤ_WhiteNightWhiteWish
            case ["葛城リーリヤ", "冠菊"]:
                return PIdol.葛城リーリヤ_冠菊
            case ["葛城リーリヤ", "初心"]:
                return PIdol.葛城リーリヤ_初心
            case ["葛城リーリヤ", "学園生活"]:
                return PIdol.葛城リーリヤ_学園生活
            case ["藤田ことね", "カワイイ", "はじめました"]:
                return PIdol.藤田ことね_カワイイ_はじめました
            case ["藤田ことね", "世界一可愛い私"]:
                return PIdol.藤田ことね_世界一可愛い私
            case ["藤田ことね", "Campus mode!!"]:
                return PIdol.藤田ことね_Campusmode
            case ["藤田ことね", "Yellow Big Bang！"]:
                return PIdol.藤田ことね_YellowBigBang
            case ["藤田ことね", "White Night! White Wish!"]:
                return PIdol.藤田ことね_WhiteNightWhiteWish
            case ["藤田ことね", "冠菊"]:
                return PIdol.藤田ことね_冠菊
            case ["藤田ことね", "初声"]:
                return PIdol.藤田ことね_初声
            case ["藤田ことね", "学園生活"]:
                return PIdol.藤田ことね_学園生活
            case _:
                nonlocal msg
                if msg == '':
                    msg = '培育设置中的以下偶像升级失败。请尝试手动添加。\n'
                msg += f'{idol} 未找到\n'
                return None
    old_idols = options['produce']['idols']
    new_idols = list(filter(lambda x: x is not None, map(map_idol, old_idols)))
    options['produce']['idols'] = new_idols
    shutil.copy('config.json', 'config.v1.json')
    return options, msg

def upgrade_v2_to_v3(options: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """
    v2 -> v3 变更：\n
    引入了游戏解包数据，因此 PIdol 枚举废弃，直接改用游戏内 ID。
    """
    msg = ''
    def map_idol(idol: PIdol) -> str | None:
        match idol:
            case PIdol.倉本千奈_Campusmode: return "i_card-skin-kcna-3-007"
            case PIdol.倉本千奈_WonderScale: return "i_card-skin-kcna-3-000"
            case PIdol.倉本千奈_ようこそ初星温泉: return "i_card-skin-kcna-3-005"
            case PIdol.倉本千奈_仮装狂騒曲: return "i_card-skin-kcna-3-002"
            case PIdol.倉本千奈_初心: return "i_card-skin-kcna-1-001"
            case PIdol.倉本千奈_学園生活: return "i_card-skin-kcna-1-000"
            case PIdol.倉本千奈_日々_発見的ステップ: return "i_card-skin-kcna-3-001"
            case PIdol.倉本千奈_胸を張って一歩ずつ: return "i_card-skin-kcna-2-000"
            case PIdol.十王星南_Campusmode: return "i_card-skin-jsna-3-002"
            case PIdol.十王星南_一番星: return "i_card-skin-jsna-2-000"
            case PIdol.十王星南_学園生活: return "i_card-skin-jsna-1-000"
            case PIdol.十王星南_小さな野望: return "i_card-skin-jsna-3-000"
            case PIdol.姫崎莉波_clumsytrick: return "i_card-skin-hrnm-3-000"
            case PIdol.姫崎莉波_私らしさのはじまり: return "i_card-skin-hrnm-2-000"
            case PIdol.姫崎莉波_キミとセミブルー: return "i_card-skin-hrnm-3-001"
            case PIdol.姫崎莉波_Campusmode: return "i_card-skin-hrnm-3-007"
            case PIdol.姫崎莉波_LUV: return "i_card-skin-hrnm-3-002"
            case PIdol.姫崎莉波_ようこそ初星温泉: return "i_card-skin-hrnm-3-004"
            case PIdol.姫崎莉波_ハッピーミルフィーユ: return "i_card-skin-hrnm-3-008"
            case PIdol.姫崎莉波_初心: return "i_card-skin-hrnm-1-001"
            case PIdol.姫崎莉波_学園生活: return "i_card-skin-hrnm-1-000"
            case PIdol.月村手毬_Lunasaymaybe: return "i_card-skin-ttmr-3-000"
            case PIdol.月村手毬_一匹狼: return "i_card-skin-ttmr-2-000"
            case PIdol.月村手毬_Campusmode: return "i_card-skin-ttmr-3-007"
            case PIdol.月村手毬_アイヴイ: return "i_card-skin-ttmr-3-001"
            case PIdol.月村手毬_初声: return "i_card-skin-ttmr-1-001"
            case PIdol.月村手毬_学園生活: return "i_card-skin-ttmr-1-000"
            case PIdol.月村手毬_仮装狂騒曲: return "i_card-skin-ttmr-3-002"
            case PIdol.有村麻央_Fluorite: return "i_card-skin-amao-3-000"
            case PIdol.有村麻央_はじまりはカッコよく: return "i_card-skin-amao-2-000"
            case PIdol.有村麻央_Campusmode: return "i_card-skin-amao-3-007"
            case PIdol.有村麻央_FeelJewelDream: return "i_card-skin-amao-3-002"
            case PIdol.有村麻央_キミとセミブルー: return "i_card-skin-amao-3-001"
            case PIdol.有村麻央_初恋: return "i_card-skin-amao-1-001"
            case PIdol.有村麻央_学園生活: return "i_card-skin-amao-1-000"
            case PIdol.篠泽广_コントラスト: return "i_card-skin-shro-3-001"
            case PIdol.篠泽广_一番向いていないこと: return "i_card-skin-shro-2-000"
            case PIdol.篠泽广_光景: return "i_card-skin-shro-3-000"
            case PIdol.篠泽广_Campusmode: return "i_card-skin-shro-3-007"
            case PIdol.篠泽广_仮装狂騒曲: return "i_card-skin-shro-3-002"
            case PIdol.篠泽广_ハッピーミルフィーユ: return "i_card-skin-shro-3-008"
            case PIdol.篠泽广_初恋: return "i_card-skin-shro-1-001"
            case PIdol.篠泽广_学園生活: return "i_card-skin-shro-1-000"
            case PIdol.紫云清夏_TameLieOneStep: return "i_card-skin-ssmk-3-000"
            case PIdol.紫云清夏_カクシタワタシ: return "i_card-skin-ssmk-3-002"
            case PIdol.紫云清夏_夢へのリスタート: return "i_card-skin-ssmk-2-000"
            case PIdol.紫云清夏_Campusmode: return "i_card-skin-ssmk-3-007"
            case PIdol.紫云清夏_キミとセミブルー: return "i_card-skin-ssmk-3-001"
            case PIdol.紫云清夏_初恋: return "i_card-skin-ssmk-1-001"
            case PIdol.紫云清夏_学園生活: return "i_card-skin-ssmk-1-000"
            case PIdol.花海佑芽_WhiteNightWhiteWish: return "i_card-skin-hume-3-005"
            case PIdol.花海佑芽_学園生活: return "i_card-skin-hume-1-000"
            case PIdol.花海佑芽_Campusmode: return "i_card-skin-hume-3-006"
            case PIdol.花海佑芽_TheRollingRiceball: return "i_card-skin-hume-3-000"
            case PIdol.花海佑芽_アイドル_はじめっ: return "i_card-skin-hume-2-000"
            case PIdol.花海咲季_BoomBoomPow: return "i_card-skin-hski-3-001"
            case PIdol.花海咲季_Campusmode: return "i_card-skin-hski-3-008"
            case PIdol.花海咲季_FightingMyWay: return "i_card-skin-hski-3-000"
            case PIdol.花海咲季_わたしが一番: return "i_card-skin-hski-2-000"
            case PIdol.花海咲季_冠菊: return "i_card-skin-hski-3-002"
            case PIdol.花海咲季_初声: return "i_card-skin-hski-1-001"
            case PIdol.花海咲季_古今東西ちょちょいのちょい: return "i_card-skin-hski-3-006"
            case PIdol.花海咲季_学園生活: return "i_card-skin-hski-1-000"
            case PIdol.葛城リーリヤ_一つ踏み出した先に: return "i_card-skin-kllj-2-000"
            case PIdol.葛城リーリヤ_白線: return "i_card-skin-kllj-3-000"
            case PIdol.葛城リーリヤ_Campusmode: return "i_card-skin-kllj-3-006"
            case PIdol.葛城リーリヤ_WhiteNightWhiteWish: return "i_card-skin-kllj-3-005"
            case PIdol.葛城リーリヤ_冠菊: return "i_card-skin-kllj-3-001"
            case PIdol.葛城リーリヤ_初心: return "i_card-skin-kllj-1-001"
            case PIdol.葛城リーリヤ_学園生活: return "i_card-skin-kllj-1-000"
            case PIdol.藤田ことね_カワイイ_はじめました: return "i_card-skin-fktn-2-000"
            case PIdol.藤田ことね_世界一可愛い私: return "i_card-skin-fktn-3-000"
            case PIdol.藤田ことね_Campusmode: return "i_card-skin-fktn-3-007"
            case PIdol.藤田ことね_YellowBigBang: return "i_card-skin-fktn-3-001"
            case PIdol.藤田ことね_WhiteNightWhiteWish: return "i_card-skin-fktn-3-006"
            case PIdol.藤田ことね_冠菊: return "i_card-skin-fktn-3-002"
            case PIdol.藤田ことね_初声: return "i_card-skin-fktn-1-001"
            case PIdol.藤田ことね_学園生活: return "i_card-skin-fktn-1-000"
            case _:
                nonlocal msg
                if msg == '':
                    msg = '培育设置中的以下偶像升级失败。请尝试手动添加。\n'
                msg += f'{idol} 未找到\n'
                return None
    old_idols = options['produce']['idols']
    new_idols = list(filter(lambda x: x is not None, map(map_idol, old_idols)))
    options['produce']['idols'] = new_idols
    shutil.copy('config.json', 'config.v2.json')
    return options, msg

def upgrade_v3_to_v4(options: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """
    v3 -> v4 变更：
    自动纠正错误游戏包名
    """
    shutil.copy('config.json', 'config.v3.json')
    if options['start_game']['game_package_name'] == 'com.bandinamcoent.idolmaster_gakuen':
        options['start_game']['game_package_name'] = 'com.bandainamcoent.idolmaster_gakuen'
        logger.info('Corrected game package name to com.bandainamcoent.idolmaster_gakuen')
    return options, ''

def upgrade_v4_to_v5(user_config: dict[str, Any], options: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """
    v4 -> v5 变更：
    为 windows 和 windows_remote 截图方式的 type 设置为 dmm
    """
    shutil.copy('config.json', 'config.v4.json')
    if user_config['backend']['screenshot_impl'] in ['windows', 'remote_windows']:
        logger.info('Set backend type to dmm.')
        user_config['backend']['type'] = 'dmm'
    return options, ''

if __name__ == '__main__':
    print(PurchaseConfig.model_fields['money_refresh_on'].description)