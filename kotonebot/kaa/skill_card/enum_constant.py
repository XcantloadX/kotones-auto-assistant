from enum import Enum, IntEnum


# 卡牌作用类型
class CardType(Enum):
    mental = "MentalSkillCard"  # M卡
    active = "ActiveSkillCard"  # A卡
    trouble = "TroubleSkillCard"  # T卡
    unidentified = "Unidentified"  # 未识别


# 卡牌职业分类
class PlanType(Enum):
    common = "Common"  # 通用
    sense = "Sense"  # 感性
    logic = "Logic"  # 理性
    anomaly = "Anomaly"  # 非凡


# 偶像流派
class Archetype(Enum):
    # 未识别
    unidentified = "unidentified"
    # 好调
    good_condition = "好調"
    # 集中
    focus = "集中"
    # 好印象
    good_impression = "好印象"
    # 干劲
    motivation = "やる気"
    # 强气
    confidence = "強気"
    # 温存
    conservation = "温存"
    # 全力
    full_power = "全力"


# 卡牌抉择优先度，越大优先度越低
class CardPriority(IntEnum):
    core = 0
    high = 1
    medium = 2
    low = 3
    other = 99


# 卡牌名称（标识）
class CardName(Enum):
    unidentified = "Unidentified"

    # common：N 卡
    c_n_0 = "眠気"
    c_n_1 = "アピールの基本"
    c_n_2 = "ポーズの基本"

    c_n_3 = "表現の基本"

    # common：R 卡
    c_r_1 = "気合十分!"
    c_r_2 = "ファーストステップ"

    # common：SR 卡
    c_sr_1 = "前途洋々"

    c_sr_2 = "アイドル宣言"
    c_sr_3 = "ハイテンション"

    # common：SSR 卡
    c_ssr_1 = "テレビ出演"
    c_ssr_2 = "叶えたい夢"
    c_ssr_3 = "アイドル魂"
    c_ssr_4 = "仕切り直し"

    # sense：N 卡
    s_n_1 = "挑戦"
    s_n_2 = "試行錯誤"

    s_n_3 = "振る舞いの基本"
    s_n_4 = "表情の基本"

    # sense：R 卡
    s_r_1 = "軽い足取り"
    s_r_2 = "愛嬌"
    s_r_3 = "準備運動"
    s_r_4 = "ファンサ"
    s_r_5 = "勢い任せ"
    s_r_6 = "ハイタッチ"
    s_r_7 = "トークタイム"
    s_r_8 = "エキサイト"

    s_r_9 = "バランス感覚"
    s_r_10 = "楽観的"
    s_r_11 = "深呼吸"
    s_r_12 = "ひと呼吸"

    # sense：SR 卡
    s_sr_1 = "決めポーズ"
    s_sr_2 = "アドリブ"
    s_sr_3 = "情熱ターン"
    s_sr_4 = "飛躍"
    s_sr_5 = "祝福"
    s_sr_6 = "スタートダッシュ"
    s_sr_7 = "スタンドプレー"
    s_sr_8 = "シュプレヒコール"
    s_sr_9 = "立ち位置チェック"

    s_sr_10 = "眼力"
    s_sr_11 = "大声援"
    s_sr_12 = "演出計画"
    s_sr_13 = "願いの力"
    s_sr_14 = "静かな意志"
    s_sr_15 = "始まりの合図"
    s_sr_16 = "意地"
    s_sr_17 = "存在感"
    s_sr_18 = "成功への道筋"
    s_sr_19 = "スポットライト"

    # sense：SSR 卡
    s_ssr_1 = "コール&レスポンス"
    s_ssr_2 = "バズワード"
    s_ssr_3 = "成就"
    s_ssr_4 = "魅惑のパフォーマンス"
    s_ssr_5 = "至高のエンタメ"
    s_ssr_6 = "覚醒"

    s_ssr_7 = "国民的アイドル"
    s_ssr_8 = "魅惑の視線"
    s_ssr_9 = "鳴り止まない拍手"
    s_ssr_10 = "天真爛漫"

    # logic：N 卡
    l_n_1 = "可愛い仕草"
    l_n_2 = "気分転換"

    l_n_3 = "目線の基本"
    l_n_4 = "意識の基本"

    # logic：R 卡
    l_r_1 = "今日もおはよう"
    l_r_2 = "ゆるふわおしゃべり"
    l_r_3 = "もう少しだけ"
    l_r_4 = "手拍子"
    l_r_5 = "元気な挨拶"
    l_r_6 = "デイドリーミング"

    l_r_7 = "リスタート"
    l_r_8 = "えいえいおー"
    l_r_9 = "リズミカル"
    l_r_10 = "思い出し笑い"
    l_r_11 = "パステル気分"
    l_r_12 = "励まし"
    l_r_13 = "幸せのおまじない"

    # logic：SR 卡
    l_sr_1 = "ラブリーウインク"
    l_sr_2 = "ありがとうの言葉"
    l_sr_3 = "ハートの合図"
    l_sr_4 = "キラメキ"
    l_sr_5 = "みんな大好き"
    l_sr_6 = "きらきら紙吹雪"

    l_sr_7 = "あふれる思い出"
    l_sr_8 = "ふれあい"
    l_sr_9 = "幸せな時間"
    l_sr_10 = "ファンシーチャーム"
    l_sr_11 = "ワクワクが止まらない"
    l_sr_12 = "本番前夜"
    l_sr_13 = "ひなたぼっこ"
    l_sr_14 = "イメトレ"
    l_sr_15 = "やる気は満点"
    l_sr_16 = "ゆめみごこち"
    l_sr_17 = "止められない想い"
    l_sr_18 = "オトメゴコロ"

    # logic：SSR 卡
    l_ssr_1 = "200%スマイル"
    l_ssr_2 = "開花"
    l_ssr_3 = "届いて!"
    l_ssr_4 = "輝くキミへ"
    l_ssr_5 = "あのときの約束"
    l_ssr_6 = "キセキの魔法"

    l_ssr_7 = "私がスター"
    l_ssr_8 = "星屑センセーション"
    l_ssr_9 = "ノートの端の決意"
    l_ssr_10 = "手書きのメッセージ"
    l_ssr_11 = "トキメキ"
    l_ssr_12 = "虹色ドリーマー"
    l_ssr_13 = "夢色リップ"

    # anomaly：N 卡
    a_n_1 = "挨拶の基本"
    a_n_2 = "はげしく"
    a_n_3 = "スパート"
    a_n_4 = "メントレの基本"
    a_n_5 = "イメージの基本"
    # anomaly：R 卡
    a_r_1 = "ジャストアピール"
    a_r_2 = "スターライト"
    a_r_3 = "一歩"
    a_r_4 = "ラッキー♪"
    a_r_5 = "積み重ね"
    a_r_6 = "精一杯"

    a_r_7 = "ハッピー♪"
    a_r_8 = "嬉しい誤算"
    a_r_9 = "涙の思い出"
    a_r_10 = "セッティング"

    # anomaly：SR 卡
    a_sr_1 = "せーのっ!"
    a_sr_2 = "アッチェレランド"
    a_sr_3 = "はじけるパッション"
    a_sr_4 = "汗と成長"
    a_sr_5 = "第一印象"
    a_sr_6 = "オープニングアクト"
    a_sr_7 = "始まりの笑顔"
    a_sr_8 = "トレンドリーダー"
    a_sr_9 = "理想のテンポ"
    a_sr_10 = "トレーニングの成果"

    a_sr_11 = "潜在能力"
    a_sr_12 = "カウントダウン"
    a_sr_13 = "モチベ"
    a_sr_14 = "プライド"
    a_sr_15 = "盛り上げ上手"
    a_sr_16 = "インフルエンサー"
    a_sr_17 = "忍耐力"
    a_sr_18 = "切磋琢磨"
    a_sr_19 = "タフネス"
    # anomaly：SSR 卡
    a_ssr_1 = "翔び立て!"
    a_ssr_2 = "総合芸術"
    a_ssr_3 = "心・技・体"
    a_ssr_4 = "輝け!"
    a_ssr_5 = "クライマックス"
    a_ssr_6 = "全身全霊"

    a_ssr_7 = "アイドルになります"
    a_ssr_8 = "一心不乱"
    a_ssr_9 = "頂点へ"
    a_ssr_10 = "覚悟"


archetype_dict = {x.value: x for x in Archetype}
card_name_dict = {x.value: x for x in CardName}

# 一些因为ocr读取有问题而暂时添加的匹配
card_name_dict.update(
    {
        # 卡名读取有误
        "天真燗漫": CardName.s_ssr_10,
        "元気な挨": CardName.l_r_5,
        "えいえいお一": CardName.l_r_8,
        "フクワクが止まらない": CardName.l_sr_11,
        "ラッキーの": CardName.a_r_4,  # 名字后面的音符符号
        "ハッピー・": CardName.a_r_7,  # 名字后面的音符符号
        "切礎琢磨": CardName.a_sr_18,

        # 强化卡名读取有误
        "デイドリーミングャ": CardName.l_r_6,
        "ラッキー・": CardName.a_r_4,  # 名字后面的音符符号
        "切瑳琢磨": CardName.a_sr_18,
        "バズワードャ": CardName.s_ssr_2,  # 名字后面的音符符号
        "輝くキミヘ": CardName.l_ssr_4,  # 片假名
        "天真欄漫": CardName.s_ssr_10,
        "頂点ヘ": CardName.a_ssr_9,  # 片假名
    }
)


def get_archetype(s: str):
    return archetype_dict.get(s, Archetype.unidentified)


def get_card_name(s: str):
    return card_name_dict.get(s, CardName.unidentified)
