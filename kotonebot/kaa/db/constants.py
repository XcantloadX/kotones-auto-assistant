from enum import Enum


class CharacterId(Enum):
    """偶像 ID。"""
    hski = "hski"  # Hanami Saki, 花海咲季
    ttmr = "ttmr"  # Tsukimura Temari, 月村手毬
    fktn = "fktn"  # Fujita Kotone, 藤田ことね
    amao = "amao"  # Arimura Mao, 有村麻央
    kllj = "kllj"  # Katsuragi Lilja, 葛城リーリヤ
    kcna = "kcna"  # Kuramoto China, 倉本千奈
    ssmk = "ssmk"  # Shiun Sumika, 紫云清夏
    shro = "shro"  # Shinosawa Hiro, 篠澤広
    hrnm = "hrnm"  # Himesaki Rinami, 姫崎莉波
    hume = "hume"  # Hanami Ume, 花海佑芽
    jsna = "jsna"  # Juo Sena, 十王星南
    hmsz = "hmsz"  # Hataya Misuzu, 秦谷美鈴    


class ExamEffectType(Enum):
    """
    考试流派。
    温存根据 ShowExamEffectType 决定
    """
    good_condition = "ProduceExamEffectType_ExamParameterBuff"
    """好调"""
    focus = "ProduceExamEffectType_ExamLessonBuff"
    """集中"""
    good_impression = "ProduceExamEffectType_ExamReview"
    """好印象"""
    motivation = "ProduceExamEffectType_ExamCardPlayAggressive"
    """干劲"""
    confidence = "ProduceExamEffectType_ExamConcentration"
    """强气"""
    full_power = "ProduceExamEffectType_ExamFullPower"
    """全力"""


class ShowExamEffectType(Enum):
    """
    若为 ProduceExamEffectType_ExamPreservation ，则偶像卡推荐流派显示为 温存
    目前分 全力-温存 和 强气-温存 两种，选择卡牌还是根据 全力/强气 来选择
    """
    unknown = "ProduceExamEffectType_Unknown"
    """推荐流派与ExamEffectType对应"""
    conservation = "ProduceExamEffectType_ExamPreservation"
    """推荐流派显示为温存"""
