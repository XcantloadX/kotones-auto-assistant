"""
默认卡组配置。

卡牌优先级数据源自社区通用认知，对应每个考试流派的卡牌选择偏好。
如果有误或游戏版本更新导致变化，欢迎 PR 修正。

数据来源：https://github.com/XcantloadX/kotones-auto-assistant/pull/48
"""
from kaa.config.deck import CardDeck
from kaa.db.constants import ProduceExamEffectType

DEFAULT_DECKS: dict[ProduceExamEffectType, CardDeck] = {
    ProduceExamEffectType.ExamParameterBuff: CardDeck(
        id='__default_ExamParameterBuff',
        name='默认卡组 - 好调',
        archetype='ProduceExamEffectType_ExamParameterBuff',
        cards=[
            [
                'p_card-01-act-3_049',  # 至高のエンタメ
                'p_card-01-men-3_006',  # 国民的アイドル
                'p_card-01-men-3_036',  # 魅惑の視線
            ],
            [
                'p_card-00-men-2_012',  # アイドル宣言
                'p_card-00-men-3_003',  # アイドル魂
                'p_card-00-men-3_005',  # 仕切り直し
                'p_card-01-men-1_034',  # ひと呼吸
                'p_card-01-men-2_038',  # 願いの力
                'p_card-01-men-2_035',  # 静かな意志
                'p_card-01-men-2_036',  # 始まりの合図
                'p_card-01-men-2_037',  # 存在感
                'p_card-01-act-2_001',  # シュプレヒコール
                'p_card-01-act-3_030',  # コール＆レスポンス
                'p_card-01-act-3_029',  # 成就
                'p_card-01-men-3_033',  # 鳴り止まない拍手
                'p_card-01-men-3_035',  # 天真爛漫
                'p_card-01-act-3_010',  # 魅惑のパフォーマンス
            ],
            [
                'p_card-01-men-2_039',  # 眼力
                'p_card-01-men-2_043',  # 大声援
                'p_card-01-men-2_034',  # 演出計画
                'p_card-01-men-2_040',  # 意地
                'p_card-01-act-1_020',  # ハイタッチ
                'p_card-01-act-1_021',  # トークタイム
                'p_card-01-act-1_036',  # エキサイト
                'p_card-01-act-2_042',  # 祝福
            ],
            [
                'p_card-01-act-2_003',  # 決めポーズ
                'p_card-01-act-2_033',  # 飛躍
                'p_card-01-act-2_059',  # 立ち位置チェック
                'p_card-01-men-2_041',  # 成功への道筋
                'p_card-00-men-1_007',  # ファーストステップ
                'p_card-00-men-3_012',  # テレビ出演
                'p_card-00-men-3_011',  # 叶えたい夢
            ],
        ],
    ),
    ProduceExamEffectType.ExamLessonBuff: CardDeck(
        id='__default_ExamLessonBuff',
        name='默认卡组 - 集中',
        archetype='ProduceExamEffectType_ExamLessonBuff',
        cards=[
            [
                'p_card-01-act-3_049',  # 至高のエンタメ
                'p_card-01-men-3_006',  # 国民的アイドル
                'p_card-01-men-3_036',  # 魅惑の視線
            ],
            [
                'p_card-00-men-2_012',  # アイドル宣言
                'p_card-00-men-3_003',  # アイドル魂
                'p_card-00-men-3_005',  # 仕切り直し
                'p_card-01-men-1_034',  # ひと呼吸
                'p_card-01-men-2_038',  # 願いの力
                'p_card-01-men-2_035',  # 静かな意志
                'p_card-01-men-2_036',  # 始まりの合図
                'p_card-01-men-2_037',  # 存在感
                'p_card-01-act-2_001',  # シュプレヒコール
                'p_card-01-act-3_030',  # コール＆レスポンス
                'p_card-01-act-3_029',  # 成就
                'p_card-01-men-3_033',  # 鳴り止まない拍手
                'p_card-01-men-3_035',  # 天真爛漫
                'p_card-01-act-3_010',  # 魅惑のパフォーマンス
            ],
            [
                'p_card-01-men-2_039',  # 眼力
                'p_card-01-men-2_043',  # 大声援
                'p_card-01-men-2_034',  # 演出計画
                'p_card-01-men-2_040',  # 意地
                'p_card-01-act-1_020',  # ハイタッチ
                'p_card-01-act-1_021',  # トークタイム
                'p_card-01-act-1_036',  # エキサイト
                'p_card-01-act-2_042',  # 祝福
            ],
            [
                'p_card-01-act-2_003',  # 決めポーズ
                'p_card-01-act-2_033',  # 飛躍
                'p_card-01-act-2_059',  # 立ち位置チェック
                'p_card-01-men-2_041',  # 成功への道筋
                'p_card-00-men-1_007',  # ファーストステップ
                'p_card-00-men-3_012',  # テレビ出演
                'p_card-00-men-3_011',  # 叶えたい夢
            ],
        ],
    ),
    ProduceExamEffectType.ExamReview: CardDeck(
        id='__default_ExamReview',
        name='默认卡组 - 好印象',
        archetype='ProduceExamEffectType_ExamReview',
        cards=[
            [
                'p_card-02-act-3_050',  # 輝くキミへ
                'p_card-02-men-3_002',  # 私がスター
                'p_card-02-men-3_004',  # 星屑センセーション
                'p_card-02-men-3_040',  # 夢色リップ
            ],
            [
                'p_card-00-men-2_012',  # アイドル宣言
                'p_card-00-men-3_003',  # アイドル魂
                'p_card-00-men-3_005',  # 仕切り直し
                'p_card-02-men-2_056',  # 止められない想い
                'p_card-02-act-2_048',  # キラメキ
                'p_card-02-men-2_058',  # ファンシーチャーム
                'p_card-02-men-2_004',  # ワクワクが止まらない
                'p_card-02-men-3_041',  # ノートの端の決意
                'p_card-02-men-3_043',  # トキメキ
                'p_card-02-men-3_042',  # 虹色ドリーマー
                'p_card-02-act-2_049',  # みんな大好き
                'p_card-02-men-2_057',  # ゆめみごこち
                'p_card-02-men-2_060',  # オトメゴコロ
            ],
            [
                'p_card-02-act-1_003',  # 手拍子
                'p_card-02-men-1_035',  # 幸せのおまじない
                'p_card-02-men-2_051',  # やる気は満点
                'p_card-02-men-2_054',  # 本番前夜
                'p_card-02-act-3_001',  # 200%スマイル
                'p_card-02-act-3_052',  # キセキの魔法
            ],
            [
                'p_card-02-act-2_046',  # ラブリーウインク
                'p_card-02-men-2_050',  # 幸せな時間
                'p_card-02-men-2_052',  # ひなたぼっこ
                'p_card-02-men-2_008',  # イメトレ
                'p_card-00-men-1_007',  # ファーストステップ
                'p_card-00-men-3_012',  # テレビ出演
                'p_card-00-men-3_011',  # 叶えたい夢
            ],
        ],
    ),
    ProduceExamEffectType.ExamCardPlayAggressive: CardDeck(
        id='__default_ExamCardPlayAggressive',
        name='默认卡组 - 干劲',
        archetype='ProduceExamEffectType_ExamCardPlayAggressive',
        cards=[
            [
                'p_card-02-men-3_002',  # 私がスター
                'p_card-02-men-3_040',  # 夢色リップ
                'p_card-02-act-1_037',  # デイドリーミング
                'p_card-02-act-2_062',  # きらきら紙吹雪
            ],
            [
                'p_card-00-men-2_012',  # アイドル宣言
                'p_card-00-men-3_003',  # アイドル魂
                'p_card-00-men-3_005',  # 仕切り直し
                'p_card-02-men-2_056',  # 止められない想い
                'p_card-02-men-2_004',  # ワクワクが止まらない
                'p_card-02-men-2_052',  # ひなたぼっこ
                'p_card-02-men-2_008',  # イメトレ
                'p_card-02-act-3_039',  # 届いて！
                'p_card-02-men-3_041',  # ノートの端の決意
                'p_card-02-men-3_043',  # トキメキ
            ],
            [
                'p_card-02-act-3_038',  # 開花
                'p_card-02-men-3_044',  # 手書きのメッセージ
                'p_card-02-act-3_045',  # あのときの約束
                'p_card-02-act-2_047',  # ありがとうの言葉
                'p_card-02-men-2_054',  # 本番前夜
            ],
            [
                'p_card-02-act-1_004',  # 元気な挨拶
                'p_card-02-men-1_006',  # リズミカル
                'p_card-02-men-2_051',  # やる気は満点
                'p_card-00-men-1_007',  # ファーストステップ
                'p_card-00-men-3_012',  # テレビ出演
                'p_card-00-men-3_011',  # 叶えたい夢
            ],
        ],
    ),
    ProduceExamEffectType.ExamConcentration: CardDeck(
        id='__default_ExamConcentration',
        name='默认卡组 - 强气',
        archetype='ProduceExamEffectType_ExamConcentration',
        cards=[
            [
                'p_card-03-men-3_058',  # アイドルになります
                'p_card-03-men-3_061',  # 一心不乱
            ],
            [
                'p_card-00-men-2_012',  # アイドル宣言
                'p_card-00-men-3_003',  # アイドル魂
                'p_card-00-men-3_005',  # 仕切り直し
                'p_card-03-act-2_081',  # 第一印象
                'p_card-03-men-2_066',  # プライド
                'p_card-03-men-2_076',  # 盛り上げ上手
                'p_card-03-men-2_080',  # インフルエンサー
                'p_card-03-men-2_074',  # タフネス
                'p_card-03-act-3_054',  # 総合芸術
                'p_card-03-act-3_056',  # 心・技・体
                'p_card-03-act-3_055',  # クライマックス
                'p_card-03-act-3_065',  # 全身全霊
                'p_card-03-men-3_062',  # 頂点へ
            ],
            [
                'p_card-03-act-1_044',  # 精一杯
                'p_card-03-men-1_039',  # ハッピー♪
                'p_card-03-men-1_049',  # 嬉しい誤算
                'p_card-03-act-2_063',  # オープニングアクト
                'p_card-03-act-2_073',  # カウントダウン
                'p_card-03-men-2_077',  # 忍耐力
            ],
            [
                'p_card-03-men-1_048',  # 涙の思い出
                'p_card-03-act-2_068',  # はじけるパッション
                'p_card-03-act-2_067',  # 理想のテンポ
                'p_card-00-men-1_007',  # ファーストステップ
                'p_card-00-men-3_012',  # テレビ出演
                'p_card-00-men-3_011',  # 叶えたい夢
            ],
        ],
    ),
    ProduceExamEffectType.ExamFullPower: CardDeck(
        id='__default_ExamFullPower',
        name='默认卡组 - 全力',
        archetype='ProduceExamEffectType_ExamFullPower',
        cards=[
            [
                'p_card-03-men-2_075',  # モチベ
                'p_card-03-men-3_058',  # アイドルになります
            ],
            [
                'p_card-00-men-2_012',  # アイドル宣言
                'p_card-00-men-3_003',  # アイドル魂
                'p_card-00-men-3_005',  # 仕切り直し
                'p_card-03-men-2_066',  # プライド
                'p_card-03-men-2_076',  # 盛り上げ上手
                'p_card-03-men-2_080',  # インフルエンサー
                'p_card-03-men-2_074',  # タフネス
                'p_card-03-act-3_057',  # 翔び立て！
                'p_card-03-act-3_056',  # 心・技・体
                'p_card-03-act-3_053',  # 輝け！
                'p_card-03-act-3_065',  # 全身全霊
                'p_card-03-men-3_062',  # 頂点へ
                'p_card-03-men-3_063',  # 覚悟
            ],
            [
                'p_card-03-men-1_049',  # 嬉しい誤算
                'p_card-03-men-1_048',  # 涙の思い出
                'p_card-03-men-1_051',  # セッティング
                'p_card-03-act-2_063',  # オープニングアクト
                'p_card-03-act-2_071',  # トレーニングの成果
                'p_card-03-men-2_064',  # 潜在能力
                'p_card-03-men-2_077',  # 忍耐力
                'p_card-03-act-3_055',  # クライマックス
            ],
            [
                'p_card-03-act-1_038',  # ジャストアピール
                'p_card-03-act-1_042',  # 積み重ね
                'p_card-03-act-2_072',  # アッチェレランド
                'p_card-03-act-2_068',  # はじけるパッション
                'p_card-03-act-2_082',  # トレンドリーダー
                'p_card-00-men-1_007',  # ファーストステップ
                'p_card-00-men-3_012',  # テレビ出演
                'p_card-00-men-3_011',  # 叶えたい夢
            ],
        ],
    ),
}


def get_default_deck(archetype: ProduceExamEffectType) -> CardDeck | None:
    """获取指定流派的默认卡组。"""
    return DEFAULT_DECKS.get(archetype)
