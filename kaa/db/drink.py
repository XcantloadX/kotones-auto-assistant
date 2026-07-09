from dataclasses import dataclass
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field

from kaa.db._util import register_cache_clear, row_dict
from kaa.db.sqlite import select, select_many

_PRODUCE_DRINK_SELECT = """
SELECT
    id,
    assetId,
    name
FROM ProduceDrink
""".strip()


class ProduceDrinkRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    asset_id: str = Field(alias='assetId')
    name: str


@dataclass
class Drink:
    """饮品"""
    id: str
    asset_id: str
    name: str

    @classmethod
    def from_asset_id(cls, asset_id: str) -> 'Drink | None':
        """根据 asset_id 查询 Drink。"""
        row = select(f'{_PRODUCE_DRINK_SELECT} WHERE assetId = ?;', asset_id)
        if row is None:
            return None
        parsed = ProduceDrinkRow.model_validate(row_dict(row))
        return cls(parsed.id, parsed.asset_id, parsed.name)

    @classmethod
    def all(cls) -> list['Drink']:
        """获取所有饮品"""
        return list(_all_cached())

    @classmethod
    def ordinary_drinks_name(cls) -> list[str]:
        """获取所有平凡的（不需要额外操作）的饮料"""
        return [
            '初星水', # [kaa/resources/drinks/img_general_pdrink_1-001.png]
            '烏龍茶', # [kaa/resources/drinks/img_general_pdrink_1-004.png]
            'ミックススムージー', # [kaa/resources/drinks/img_general_pdrink_2-001.png]
            'リカバリドリンク', # [kaa/resources/drinks/img_general_pdrink_2-003.png]
            'フレッシュビネガー', # [kaa/resources/drinks/img_general_pdrink_2-004.png]
            'ブーストエキス', # [kaa/resources/drinks/img_general_pdrink_2-008.png]
            'パワフル漢方ドリンク', # [kaa/resources/drinks/img_general_pdrink_2-009.png]
            'センブリソーダ', # [kaa/resources/drinks/img_general_pdrink_2-010.png]
            '初星ホエイプロテイン', # [kaa/resources/drinks/img_general_pdrink_3-001.png]
            '初星スペシャル青汁', # [kaa/resources/drinks/img_general_pdrink_3-005.png]
            '初星スペシャル青汁X', # [kaa/resources/drinks/img_general_pdrink_3-013.png]
            'ビタミンドリンク', # [kaa/resources/drinks/img_general_pdrink_1-002.png]
            'アイスコーヒー', # [kaa/resources/drinks/img_general_pdrink_1-003.png]
            'スタミナ爆発ドリンク', # [kaa/resources/drinks/img_general_pdrink_2-005.png]
            '厳選初星マキアート', # [kaa/resources/drinks/img_general_pdrink_3-002.png]
            '初星ブーストエナジー', # [kaa/resources/drinks/img_general_pdrink_3-004.png]
            # '初星黒酢', # [kaa/resources/drinks/img_general_pdrink_3-012.png]
            'ルイボスティー', # [kaa/resources/drinks/img_general_pdrink_1-006.png]
            'ホットコーヒー', # [kaa/resources/drinks/img_general_pdrink_1-008.png]
            'おしゃれハーブティー', # [kaa/resources/drinks/img_general_pdrink_2-006.png]
            '厳選初星ティー', # [kaa/resources/drinks/img_general_pdrink_3-006.png]
            '厳選初星ブレンド', # [kaa/resources/drinks/img_general_pdrink_3-007.png]
            '特製ハツボシエキス', # [kaa/resources/drinks/img_general_pdrink_3-010.png]
            'ジンジャーエール', # [kaa/resources/drinks/img_general_pdrink_1-009.png]
            'ほうじ茶', # [kaa/resources/drinks/img_general_pdrink_1-010.png]
            # 'ほっと緑茶', # [kaa/resources/drinks/img_general_pdrink_2-007.png]
            '厳選初星チャイ', # [kaa/resources/drinks/img_general_pdrink_3-008.png]
            '初星スーパーソーダ', # [kaa/resources/drinks/img_general_pdrink_3-009.png]
            '初星湯', # [kaa/resources/drinks/img_general_pdrink_3-011.png
        ]


@lru_cache(maxsize=1)
def _all_cached() -> tuple[Drink, ...]:
    rows = select_many(f'{_PRODUCE_DRINK_SELECT};')
    return tuple(
        Drink(parsed.id, parsed.asset_id, parsed.name)
        for row in rows
        for parsed in [ProduceDrinkRow.model_validate(row_dict(row))]
    )


register_cache_clear(_all_cached.cache_clear)