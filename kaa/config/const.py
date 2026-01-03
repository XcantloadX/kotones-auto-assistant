from enum import IntEnum, Enum
from typing_extensions import assert_never


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
    IdolPiece_姬崎莉波_clumsy_trick = 18
    """姫崎薪波 cIclumsy trick 碎片"""
    IdolPiece_花海咲季_FightingMyWay = 19
    """花海咲季 FightingMyWay 碎片"""
    IdolPiece_藤田ことね_世界一可愛い私 = 20
    """藤田ことね 世界一可愛い私 碎片"""
    IdolPiece_花海佑芽_TheRollingRiceball = 21
    """花海佑芽 The Rolling Riceball 碎片"""
    IdolPiece_月村手毬_LunaSayMaybe = 22
    """月村手毬 Luna say maybe 碎片"""
    IdolPiece_有村麻央_Fluorite = 23
    """有村麻央 Fluorite 碎片"""

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
                return "倉本千奈　WonderScale 碎片"
            case cls.IdolPiece_篠泽广_光景:
                return "篠泽广　光景 碎片"
            case cls.IdolPiece_紫云清夏_TameLieOneStep:
                return "紫云清夏　Tame-Lie-One-Step 碎片"
            case cls.IdolPiece_葛城リーリヤ_白線:
                return "葛城リーリヤ　白線 碎片"
            case cls.IdolPiece_姬崎莉波_clumsy_trick:
                return "姫崎薪波　clumsy trick 碎片"
            case cls.IdolPiece_花海咲季_FightingMyWay:
                return "花海咲季　FightingMyWay 碎片"
            case cls.IdolPiece_藤田ことね_世界一可愛い私:
                return "藤田ことね　世界一可愛い私 碎片"
            case cls.IdolPiece_花海佑芽_TheRollingRiceball:
                return "花海佑芽　The Rolling Riceball 碎片"
            case cls.IdolPiece_月村手毬_LunaSayMaybe:
                return "月村手毬　Luna say maybe 碎片"
            case cls.IdolPiece_有村麻央_Fluorite:
                return "有村麻央　Fluorite 碎片"
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
        from kaa.tasks import R
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
            case DailyMoneyShopItems.IdolPiece_姬崎莉波_clumsy_trick:
                return R.Shop.IdolPiece.姬崎莉波_clumsy_trick
            case DailyMoneyShopItems.IdolPiece_花海咲季_FightingMyWay:
                return R.Shop.IdolPiece.花海咲季_FightingMyWay
            case DailyMoneyShopItems.IdolPiece_藤田ことね_世界一可愛い私:
                return R.Shop.IdolPiece.藤田ことね_世界一可愛い私
            case DailyMoneyShopItems.IdolPiece_花海佑芽_TheRollingRiceball:
                return R.Shop.IdolPiece.花海佑芽_TheRollingRiceball
            case DailyMoneyShopItems.IdolPiece_月村手毬_LunaSayMaybe:
                return R.Shop.IdolPiece.月村手毬_LunaSayMaybe
            case DailyMoneyShopItems.IdolPiece_有村麻央_Fluorite:
                return R.Shop.IdolPiece.有村麻央_Fluorite
            case _:
                assert_never(self)


class ProduceAction(Enum):
    RECOMMENDED = 'recommended'
    VISUAL = 'visual'
    VOCAL = 'vocal'
    DANCE = 'dance'
    VISUAL_SP = 'visual_sp'
    VOCAL_SP = 'vocal_sp'
    DANCE_SP = 'dance_sp'
    OUTING = 'outing'
    STUDY = 'study'
    ALLOWANCE = 'allowance'
    REST = 'rest'
    CONSULT = 'consult'

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