from enum import Enum

class CharacterId(Enum):
    hski = "hski" # Hanami Saki, 花海咲季
    ttmr = "ttmr" # Tsukimura Temari, 月村手毬
    fktn = "fktn" # Fujita Kotone, 藤田ことね
    amao = "amao" # Arimura Mao, 有村麻央
    kllj = "kllj" # Katsuragi Lilja, 葛城リーリヤ
    kcna = "kcna" # Kuramoto China, 倉本千奈
    ssmk = "ssmk" # Shiun Sumika, 紫云清夏
    shro = "shro" # Shinosawa Hiro, 篠澤広
    hrnm = "hrnm" # Himesaki Rinami, 姫崎莉波
    hume = "hume" # Hanami Ume, 花海佑芽
    jsna = "jsna" # Juo Sena, 十王星南
    atmb = "atmb" # Amaya Tsubame, 雨夜燕


class ProduceExamEffectType(Enum):
    ExamAddGrowEffect = 'ProduceExamEffectType_ExamAddGrowEffect'
    """成長（成长）\n
    例：究極スマイル（p_card-02-men-100_008）、屋上からの景色+++（p_card-03-ido-3_077）"""

    ExamAggressiveAdditive = 'ProduceExamEffectType_ExamAggressiveAdditive'
    """やる気増加量増加（干劲增加量增加）\n
    无引用此效果的卡牌"""

    ExamAggressiveReduce = 'ProduceExamEffectType_ExamAggressiveReduce'
    """やる気減少（干劲减少）\n
    无引用此效果的卡牌"""

    ExamAggressiveValueMultiple = 'ProduceExamEffectType_ExamAggressiveValueMultiple'
    """やる気（干劲效果倍率提升）\n
    例：わたしらしい色+++（p_card-02-ido-3_127）"""

    ExamAntiDebuff = 'ProduceExamEffectType_ExamAntiDebuff'
    """低下状態無効（低下状态无效）\n
    例：アイドル魂+++（p_card-00-men-3_003）、紅葉ランニング+++（p_card-00-sup-3_093）"""

    ExamBlockAddDown = 'ProduceExamEffectType_ExamBlockAddDown'
    """不安（不安）\n
    无引用此效果的卡牌"""

    ExamBlockAddMultipleAggressive = 'ProduceExamEffectType_ExamBlockAddMultipleAggressive'
    """元気（元气增加量随干劲提升）\n
    例：初めてのお相手+++（p_card-02-ido-1_064）、愛を込めて+++（p_card-02-ido-3_086）"""

    ExamBlockDependExamReview = 'ProduceExamEffectType_ExamBlockDependExamReview'
    """好印象（元气依赖好印象）\n
    无引用此效果的卡牌"""

    ExamBlockDown = 'ProduceExamEffectType_ExamBlockDown'
    """元気（元气下降）\n
    无引用此效果的卡牌"""

    ExamBlockFix = 'ProduceExamEffectType_ExamBlockFix'
    """固定元気（固定元气）\n
    例：執念キャッチャー+++（p_card-00-sup-3_161）"""

    ExamBlockPerUseCardCount = 'ProduceExamEffectType_ExamBlockPerUseCardCount'
    """元気（按出牌次数获得元气）\n
    例：未完の大器+++（p_card-02-ido-1_053）、おっきなおにぎり+++（p_card-02-ido-3_067）"""

    ExamBlockRestriction = 'ProduceExamEffectType_ExamBlockRestriction'
    """元気増加無効（元气增加无效）\n
    例：ハイテンション+++（p_card-00-men-2_014）、立ち位置チェック+++（p_card-01-act-2_059）"""

    ExamBlockValueMultiple = 'ProduceExamEffectType_ExamBlockValueMultiple'
    """元気（元气效果倍率提升）\n
    无引用此效果的卡牌"""

    ExamBlock = 'ProduceExamEffectType_ExamBlock'
    """元気（元气）\n
    例：ポーズの基本+++（p_card-00-act-0_002）、前途洋々+++（p_card-00-act-2_009）"""

    ExamCardCreateId = 'ProduceExamEffectType_ExamCardCreateId'
    """生成（生成）\n
    例：スリリング+++（p_card-01-men-2_098）、一発勝負+++（p_card-01-men-2_099）"""

    ExamCardCreateSearch = 'ProduceExamEffectType_ExamCardCreateSearch'
    """生成（检索生成）\n
    例：花萌ゆ季節+++（p_card-00-sup-3_024）"""

    ExamCardDraw = 'ProduceExamEffectType_ExamCardDraw'
    """スキルカードを引く（抽取技能卡）\n
    例：アイドル宣言+++（p_card-00-men-2_012）、仕切り直し+++（p_card-00-men-3_005）"""

    ExamCardDuplicate = 'ProduceExamEffectType_ExamCardDuplicate'
    """複製（复制）\n
    无引用此效果的卡牌"""

    ExamCardMove = 'ProduceExamEffectType_ExamCardMove'
    """温存（卡牌移动）\n
    例：夏夜に咲く思い出+++（p_card-00-sup-3_152）、天賦の才+++（p_card-01-men-3_034）"""

    ExamCardPlayAggressive = 'ProduceExamEffectType_ExamCardPlayAggressive'
    """やる気（干劲）\n
    例：ゆるふわおしゃべり+++（p_card-02-act-1_028）、もう少しだけ+++（p_card-02-act-1_029）"""

    ExamCardSearchEffectPlayCountBuff = 'ProduceExamEffectType_ExamCardSearchEffectPlayCountBuff'
    """スキルカード追加発動（技能卡追加发动）\n
    例：入道雲と、きみ+++（p_card-01-ido-3_070）、国民的アイドル+++（p_card-01-men-3_006）"""

    ExamCardUpgrade = 'ProduceExamEffectType_ExamCardUpgrade'
    """レッスン中強化（练习中强化）\n
    例：ティーパーティ+++（p_card-00-sup-3_027）"""

    ExamConcentration = 'ProduceExamEffectType_ExamConcentration'
    """強気（强势）\n
    例：挨拶の基本+++（p_card-03-act-0_014）、はげしく+++（p_card-03-act-0_020）"""

    ExamDebuffRecover = 'ProduceExamEffectType_ExamDebuffRecover'
    """低下状態回復（低下状态恢复）\n
    例：わたしらしい色+++（p_card-02-ido-3_127）"""

    ExamEffectTimer = 'ProduceExamEffectType_ExamEffectTimer'
    """発動予約（触发预约）\n
    例：アイドル魂+++（p_card-00-men-3_003）、お姉ちゃんだもの！+++（p_card-00-sup-2_025）"""

    ExamEnthusiasticAdditive = 'ProduceExamEffectType_ExamEnthusiasticAdditive'
    """熱意追加（热意追加）\n
    例：あたらしい光+++（p_card-03-ido-3_129）、日が差す方へ+++（p_card-03-ido-3_135）"""

    ExamEnthusiasticMultiple = 'ProduceExamEffectType_ExamEnthusiasticMultiple'
    """熱意増加（热意增加）\n
    例：フルスロットル+++（p_card-03-men-2_112）、いたずらサンタさん+++（p_card-03-sup-3_162）"""

    ExamExtraTurn = 'ProduceExamEffectType_ExamExtraTurn'
    """ターン追加（回合追加）\n
    例：私がスター+++（p_card-02-men-3_002）、レジェンドスター（p_card-03-men-100_016）"""

    ExamForcePlayCardSearch = 'ProduceExamEffectType_ExamForcePlayCardSearch'
    """生成（强制打出检索卡）\n
    例：エキスパート（p_card-03-men-100_015）"""

    ExamFullPower = 'ProduceExamEffectType_ExamFullPower'
    """全力（全力）\n
    无引用此效果的卡牌"""

    ExamFullPowerPointAdditive = 'ProduceExamEffectType_ExamFullPowerPointAdditive'
    """全力値増加量増加（全力值增加量增加）\n
    例：リスキーチャンス+++（p_card-03-men-2_103）"""

    ExamFullPowerPointReduce = 'ProduceExamEffectType_ExamFullPowerPointReduce'
    """全力値減少（全力值减少）\n
    无引用此效果的卡牌"""

    ExamFullPowerPoint = 'ProduceExamEffectType_ExamFullPowerPoint'
    """全力値（全力值）\n
    例：スパート+++（p_card-03-act-0_021）、アドリブの基本+++（p_card-03-act-0_047）"""

    ExamGimmickLessonDebuff = 'ProduceExamEffectType_ExamGimmickLessonDebuff'
    """緊張（紧张）\n
    无引用此效果的卡牌"""

    ExamGimmickParameterDebuff = 'ProduceExamEffectType_ExamGimmickParameterDebuff'
    """不調（不调）\n
    无引用此效果的卡牌"""

    ExamGimmickPlayCardLimit = 'ProduceExamEffectType_ExamGimmickPlayCardLimit'
    """スキルカード使用不可（技能卡不可使用）\n
    无引用此效果的卡牌"""

    ExamGimmickSleepy = 'ProduceExamEffectType_ExamGimmickSleepy'
    """弱気（弱气）\n
    无引用此效果的卡牌"""

    ExamGimmickSlump = 'ProduceExamEffectType_ExamGimmickSlump'
    """スランプ（低潮）\n
    无引用此效果的卡牌"""

    ExamGimmickStartTurnCardDrawDown = 'ProduceExamEffectType_ExamGimmickStartTurnCardDrawDown'
    """手札減少（手牌减少）\n
    无引用此效果的卡牌"""

    ExamHandGraveCountCardDraw = 'ProduceExamEffectType_ExamHandGraveCountCardDraw'
    """手札を入れ替える（更换手牌）\n
    例：仕切り直し+++（p_card-00-men-3_005）、練習再開！+++（p_card-01-sup-3_109）"""

    ExamItemFireLimitAdd = 'ProduceExamEffectType_ExamItemFireLimitAdd'
    """アイテム発動回数上限+（道具触发次数上限增加）\n
    无引用此效果的卡牌"""

    ExamLessonAddMultipleLessonBuff = 'ProduceExamEffectType_ExamLessonAddMultipleLessonBuff'
    """集中（集中倍率）\n
    例：いつか見た景色+++（p_card-01-ido-3_102）
    
    【参数】\n
    `value1`：提升倍率数值。例如 300 代表提升 0.3 倍，即集中 1.3 倍。
    """

    ExamLessonAddMultipleParameterBuff = 'ProduceExamEffectType_ExamLessonAddMultipleParameterBuff'
    """パラメータ（参数提升量随好调增加）\n
    例：ステージングの基本+++（p_card-01-act-0_022）、立ち位置チェック+++（p_card-01-act-2_059）"""

    ExamLessonBuffAdditive = 'ProduceExamEffectType_ExamLessonBuffAdditive'
    """集中増加量増加（集中增加量增加）\n
    例：完全無欠（p_card-01-men-100_001）、ほぐれるひととき+++（p_card-01-sup-3_157）"""

    ExamLessonBuffDependParameterBuff = 'ProduceExamEffectType_ExamLessonBuffDependParameterBuff'
    """好調（集中依赖好调）\n
    例：見つけた世界で+++（p_card-01-ido-3_151）"""

    ExamLessonBuffMultiple = 'ProduceExamEffectType_ExamLessonBuffMultiple'
    """集中効果一時増加（集中效果临时增加）\n
    无引用此效果的卡牌"""

    ExamLessonBuffReduce = 'ProduceExamEffectType_ExamLessonBuffReduce'
    """集中減少（集中减少）\n
    无引用此效果的卡牌"""

    ExamLessonBuff = 'ProduceExamEffectType_ExamLessonBuff'
    """集中（集中）\n
    例：パフォーマンスの基本+++（p_card-01-act-0_027）、準備運動+++（p_card-01-act-1_022）"""

    ExamLessonDependBlock = 'ProduceExamEffectType_ExamLessonDependBlock'
    """元気（参数依赖元气）\n
    例：気分転換+++（p_card-02-act-0_010）、アイコンタクトの基本+++（p_card-02-act-0_037）"""

    ExamLessonDependExamCardPlayAggressive = 'ProduceExamEffectType_ExamLessonDependExamCardPlayAggressive'
    """やる気（参数依赖干劲出牌）\n
    例：仕草の基本+++（p_card-02-act-0_038）、開花+++（p_card-02-act-3_038）"""

    ExamLessonDependExamReview = 'ProduceExamEffectType_ExamLessonDependExamReview'
    """好印象（参数依赖好印象）\n
    例：可愛い仕草+++（p_card-02-act-0_009）、ファンサの基本+++（p_card-02-act-0_032）"""

    ExamLessonDependParameterBuff = 'ProduceExamEffectType_ExamLessonDependParameterBuff'
    """好調（参数依赖好调）\n
    例：初めての地平+++（p_card-01-ido-1_060）、はじめてのラムネ+++（p_card-01-ido-3_074）"""

    ExamLessonDependPlayCardCountSum = 'ProduceExamEffectType_ExamLessonDependPlayCardCountSum'
    """パラメータ（参数依赖出牌次数）\n
    无引用此效果的卡牌"""

    ExamLessonDependStaminaConsumptionSum = 'ProduceExamEffectType_ExamLessonDependStaminaConsumptionSum'
    """パラメータ（参数依赖体力消耗总量）\n
    无引用此效果的卡牌"""

    ExamLessonFix = 'ProduceExamEffectType_ExamLessonFix'
    """固定パラメータ（固定参数）\n
    无引用此效果的卡牌"""

    ExamLessonFullPowerPoint = 'ProduceExamEffectType_ExamLessonFullPowerPoint'
    """パラメータ（参数依赖全力值）\n
    例：トレンドリーダー+++（p_card-03-act-2_082）、翔び立て！+++（p_card-03-act-3_057）"""

    ExamLessonPerSearchCount = 'ProduceExamEffectType_ExamLessonPerSearchCount'
    """パラメータ（参数依赖检索次数）\n
    无引用此效果的卡牌"""

    ExamLessonValueMultipleDependReviewOrAggressive = 'ProduceExamEffectType_ExamLessonValueMultipleDependReviewOrAggressive'
    """プライド（自尊）\n
    例：私は、決して+++（p_card-02-ido-3_140）"""

    ExamLessonValueMultipleDown = 'ProduceExamEffectType_ExamLessonValueMultipleDown'
    """パラメータ上昇量減少（参数提升量减少）\n
    无引用此效果的卡牌"""

    ExamLessonValueMultiple = 'ProduceExamEffectType_ExamLessonValueMultiple'
    """パラメータ上昇量増加（参数提升量增加）\n
    例：ダークヒーローの誕生+++（p_card-01-ido-3_164）、夢色リップ+++（p_card-02-men-3_040）"""

    ExamLesson = 'ProduceExamEffectType_ExamLesson'
    """パラメータ（参数）\n
    例：アピールの基本+++（p_card-00-act-0_001）、ポーズの基本+++（p_card-00-act-0_002）"""

    ExamMultipleLessonBuffLesson = 'ProduceExamEffectType_ExamMultipleLessonBuffLesson'
    """パラメータ（集中强化的参数提升）\n
    例：ハイタッチ+++（p_card-01-act-1_020）、最高傑作（p_card-01-act-100_004）"""

    ExamOverPreservation = 'ProduceExamEffectType_ExamOverPreservation'
    """のんびり（悠闲）\n
    无引用此效果的卡牌"""

    ExamPanic = 'ProduceExamEffectType_ExamPanic'
    """気まぐれ（心血来潮）\n
    无引用此效果的卡牌"""

    ExamParameterBuffAdditive = 'ProduceExamEffectType_ExamParameterBuffAdditive'
    """好調増加量増加（好调增加量增加）\n
    例：完全無欠（p_card-01-men-100_001）"""

    ExamParameterBuffDependLessonBuff = 'ProduceExamEffectType_ExamParameterBuffDependLessonBuff'
    """集中（好调依赖集中）\n
    无引用此效果的卡牌"""

    ExamParameterBuffMultiplePerTurn = 'ProduceExamEffectType_ExamParameterBuffMultiplePerTurn'
    """絶好調（绝好调）\n
    例：エキサイト+++（p_card-01-act-1_036）、魅惑のパフォーマンス+++（p_card-01-act-3_010）
    
    【参数】\n
    `effect_turn`：持续回合数。
    """

    ExamParameterBuffReduce = 'ProduceExamEffectType_ExamParameterBuffReduce'
    """好調減少（好调减少）\n
    无引用此效果的卡牌"""

    ExamParameterBuff = 'ProduceExamEffectType_ExamParameterBuff'
    """好調（好调）\n
    例：ステップの基本+++（p_card-01-act-0_023）、軽い足取り+++（p_card-01-act-1_002）
    
    【参数】\n
    `effect_turn`：持续回合数。
    """

    ExamPlayableValueAdd = 'ProduceExamEffectType_ExamPlayableValueAdd'
    """スキルカード使用数追加（技能卡使用次数追加）\n
    例：アイドル宣言+++（p_card-00-men-2_012）、アイドル魂+++（p_card-00-men-3_003）
    
    【参数】\n
    `effect_count`：允许的额外出牌次数。
    """

    ExamPreservation = 'ProduceExamEffectType_ExamPreservation'
    """温存（温存）\n
    例：カウントダウン+++（p_card-03-act-2_073）、休み休み、前へ+++（p_card-03-ido-2_084）
    
    【参数】\n
    `effect_value1`：阶段。1=温存，2=二阶温存。
    """

    ExamReviewAdditive = 'ProduceExamEffectType_ExamReviewAdditive'
    """好印象増加量増加（好印象增加量增加）\n
    例：湧き上がる気持ち+++（p_card-02-ido-3_119）、星屑センセーション+++（p_card-02-men-3_004）
    
    【参数】\n
    `effect_value1`：增加倍率。例如 500 代表好印象增加量增加 50%。
    `effect_turn`：持续回合数。
    """

    ExamReviewDependExamBlock = 'ProduceExamEffectType_ExamReviewDependExamBlock'
    """元気（好印象依赖元气）\n
    无引用此效果的卡牌"""

    ExamReviewDependExamCardPlayAggressive = 'ProduceExamEffectType_ExamReviewDependExamCardPlayAggressive'
    """やる気（好印象依赖干劲出牌）\n
    无引用此效果的卡牌"""

    ExamReviewMultiple = 'ProduceExamEffectType_ExamReviewMultiple'
    """好印象強化（好印象得分倍率）\n
    例：空まで一直線+++（p_card-02-ido-3_148）、究極スマイル（p_card-02-men-100_008）
    
    【参数】\n
    `effect_value1`：提升倍率数值。例如 250 代表好印象的分数收益为 1.3 倍。
    `effect_turn`：持续回合数。-1 代表永久。
    """

    ExamReviewPerSearchCount = 'ProduceExamEffectType_ExamReviewPerSearchCount'
    """好印象（根据牌堆中相同技能卡数量增加好印象）\n
    例：微熱ノスタルジー+++（p_card-02-ido-3_146）
    
    【参数】\n
    `effect_value1`：增加的好印象值。例如 2000 表示：牌库或弃牌堆中每有 1 张本技能卡，好印象 +2。
    """

    ExamReviewReduce = 'ProduceExamEffectType_ExamReviewReduce'
    """好印象減少（好印象减少）\n
    无引用此效果的卡牌"""

    ExamReviewValueMultiple = 'ProduceExamEffectType_ExamReviewValueMultiple'
    """好印象（好印象倍率）\n
    例：戦う理由+++（p_card-02-ido-3_132）
    
    【参数】\n
    `effect_value1`：提升倍率数值。例如 100 代表好印象 1.1 倍。
    """

    ExamReview = 'ProduceExamEffectType_ExamReview'
    """好印象（好印象增加）\n
    例：可愛い仕草+++（p_card-02-act-0_009）、今日もおはよう+++（p_card-02-act-1_027）
    
    【参数】\n
    `effect_value1`：增加的好印象值。例如 2 代表好印象 +2。
    """

    ExamSearchPlayCardStaminaConsumptionChange = 'ProduceExamEffectType_ExamSearchPlayCardStaminaConsumptionChange'
    """消費体力変化（体力消耗变化）\n
    例：勝利をつかめ！+++（p_card-00-sup-3_158）、全身全霊+++（p_card-03-act-3_065）
    
    【参数】\n
    `effect_turn`：持续回合数，似乎总是 -1。
    `effect_count`：下 N 张打出的技能卡的体力消耗变为 0。
    """

    ExamStaminaConsumptionAddFix = 'ProduceExamEffectType_ExamStaminaConsumptionAddFix'
    """消費体力追加（体力消耗追加）\n
    无引用此效果的卡牌"""

    ExamStaminaConsumptionAdd = 'ProduceExamEffectType_ExamStaminaConsumptionAdd'
    """消費体力増加（体力消耗上升 50%）\n
    例：スタートダッシュ+++（p_card-01-act-2_002）、スタンドプレー+++（p_card-01-act-2_032）
    
    【参数】\n
    `effect_turn`：持续回合数。
    """

    ExamStaminaConsumptionDownFix = 'ProduceExamEffectType_ExamStaminaConsumptionDownFix'
    """消費体力削減（体力消耗减少）\n
    例：ファーストステップ+++（p_card-00-men-1_007）、叶えたい夢+++（p_card-00-men-3_011）
    
    【参数】\n
    `effect_value1`：减少的体力值。例如 2 代表体力消耗 -2。
    `effect_turn`：持续回合数，-1 表示永久。
    """

    ExamStaminaConsumptionDown = 'ProduceExamEffectType_ExamStaminaConsumptionDown'
    """消費体力減少（体力消耗降低 50%）\n
    例：気合十分！+++（p_card-00-men-1_005）、アイドル宣言+++（p_card-00-men-2_012）
    
    【参数】\n
    `effect_turn`：持续回合数，-1 表示永久。
    """

    ExamStaminaDamage = 'ProduceExamEffectType_ExamStaminaDamage'
    """体力減少（体力减少）\n
    无引用此效果的卡牌"""

    ExamStaminaRecoverFix = 'ProduceExamEffectType_ExamStaminaRecoverFix'
    """体力回復（体力恢复）\n
    例：陽だまりの生徒会室+++（p_card-00-sup-3_025）、包容力+++（p_card-01-ido-1_014）
    
    【参数】\n
    `effect_value1`：恢复的体力值。例如 5 代表体力 +5。
    """

    ExamStaminaRecoverMultiple = 'ProduceExamEffectType_ExamStaminaRecoverMultiple'
    """体力回復（体力恢复倍率提升）\n
    例：また、明日+++（p_card-02-ido-3_081）"""

    ExamStaminaRecoverRestriction = 'ProduceExamEffectType_ExamStaminaRecoverRestriction'
    """体力回復無効（体力恢复无效）\n
    无引用此效果的卡牌"""

    ExamStaminaReduceFix = 'ProduceExamEffectType_ExamStaminaReduceFix'
    """体力消費（体力消耗）\n
    无引用此效果的卡牌"""

    ExamStaminaReduce = 'ProduceExamEffectType_ExamStaminaReduce'
    """体力消費（体力消耗减轻）\n
    无引用此效果的卡牌"""

    ExamStanceReset = 'ProduceExamEffectType_ExamStanceReset'
    """指針解除（指针解除）\n
    无引用此效果的卡牌"""

    ExamStatusEnchant = 'ProduceExamEffectType_ExamStatusEnchant'
    """持続効果（持续效果）\n
    例：夏夜に咲く思い出+++（p_card-00-sup-3_152）、最高傑作（p_card-01-act-100_004）
    
    【参数】\n
    `effect_turn`：持续回合数限制。
    `effect_count`：触发次数限制，0 表示永久。

    【例】
    1. effect_turn=3, effect_count=0 表示持续 3 回合，不限制触发次数。
    2. effect_turn=-1, effect_count=2 表示持续到触发 2 次为止。
    3. effect_turn=-1, effect_count=0 表示永久持续，且不限制触发次数。
    4. effect_turn=3, effect_count=2 表示持续 3 回合，且最多触发 2 次。
    """

    StanceLock = 'ProduceExamEffectType_StanceLock'
    """指針固定（指针固定）\n
    例：切磋琢磨+++（p_card-03-men-2_079）
    
    【参数】\n
    `effect_turn`：持续回合数。
    """

"""
附 查询 SQL

```sql
SELECT
    pc.id AS card_id,
    pc.name AS card_name,
    pee.id AS effect_id,
    pee.effectType,
    pee.effectValue1,
    pee.effectValue2,
    pee.effectTurn,
    pee.effectCount,
    -- 子查询：遍历 customizeProduceDescriptions 数组，提取 'text' 字段并拼接成字符串
    (
        SELECT group_concat(json_extract(desc_item.value, '$.text'), '')
        FROM json_each(pee.customizeProduceDescriptions) AS desc_item
    ) AS description
FROM
    ProduceCard pc
-- 1. 展开 ProduceCard 中的 playEffects JSON 数组
        CROSS JOIN json_each(pc.playEffects) AS pe_node
-- 2. 通过提取出的 produceExamEffectId 关联 ProduceExamEffect 表
        JOIN ProduceExamEffect pee
             ON pee.id = json_extract(pe_node.value, '$.produceExamEffectId')
WHERE
  -- 过滤掉空的效果 ID
    pee.id IS NOT NULL AND pee.id != '';
```
"""