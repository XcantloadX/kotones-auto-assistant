from dataclasses import dataclass

from .sqlite import select, select_many

@dataclass
class Drink:
    """饮品"""
    id: str
    asset_id: str
    name: str

    @classmethod
    def from_asset_id(cls, asset_id: str) -> 'Drink | None':
        """
        根据 asset_id 查询 Drink。
        """
        row = select("""
        SELECT
            id,
            assetId,
            name
        FROM ProduceDrink
        WHERE assetId = ?;
        """, asset_id)
        if row is None:
            return None
        id, asset_id, name = row
        return cls(id, asset_id, name)
    
    @classmethod
    def all(cls) -> list['Drink']:
        """获取所有饮品"""
        rows = select_many("""
        SELECT
            id,
            assetId,
            name
        FROM ProduceDrink;
        """)
        results = []
        for row in rows:
            id, asset_id, name = row
            results.append(cls(id, asset_id, name))
        return results
    
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

if __name__ == '__main__':
    from pprint import pprint as print
    print(Drink.from_asset_id('img_general_pdrink_1-001'))
    print([(str(drink.name) + '\', # [kaa/resources/drink/' + str(drink.asset_id) + '.png]') for drink in Drink.all()])