# 此脚本用于读入 extract_schema.py 生成的数据库文件，
# 并下载对应的资源

import os
import sys
import tqdm
import sqlite3

import cv2
import requests
import urllib3

from kotonebot.kaa.db.constants import CharacterId

sys.path.append(os.path.abspath('./submodules/GkmasObjectManager'))

import GkmasObjectManager as gom # type: ignore

print('拉取资源...')
manifest = gom.fetch()

MAX_RETRY_COUNT = 5
def download_to(asset_id: str, path: str, overwrite: bool = False):
    retry_count = 1
    while True:
        try:
            if not overwrite and os.path.exists(path):
                print(f'Skipped {asset_id}.')
                return
            manifest.download(asset_id, path=path, categorize=False)
            break
        except requests.exceptions.ReadTimeout | requests.exceptions.SSLError | requests.exceptions.ConnectionError | urllib3.exceptions.MaxRetryError as e:
            retry_count += 1
            if retry_count >= MAX_RETRY_COUNT:
                raise e
            print(f'Network error: {e}')
            print('Retrying...')

print("提取 P 偶像卡资源...")
base_path = './kotonebot/kaa/resources/idol_cards'
os.makedirs(base_path, exist_ok=True)

db = sqlite3.connect("./kotonebot/kaa/resources/game.db")
cursor = db.execute("""
SELECT
    IC.id AS cardId,
    ICS.id AS skinId,
    Char.lastName || ' ' || Char.firstName || ' - ' || IC.name AS name,
    ICS.assetId,
    -- アナザー 版本偶像相关
    NOT (IC.originalIdolCardSkinId = ICS.id) AS isAnotherVer,
    ICS.name AS anotherVerName
FROM IdolCard IC
JOIN Character Char ON characterId = Char.id
JOIN IdolCardSkin ICS ON IC.id = ICS.idolCardId;
""")

print("下载 P 偶像卡资源...")
for row in tqdm.tqdm(cursor.fetchall()):
    _, skin_id, name, asset_id, _, _ = row

    # 下载资源
    # 低特训等级
    asset_id0 = f'img_general_{asset_id}_0-thumb-portrait'
    path0 = base_path + f'/{skin_id}_0.png'
    # 高特训等级
    asset_id1 = f'img_general_{asset_id}_1-thumb-portrait'
    path1 = base_path + f'/{skin_id}_1.png'
    if asset_id is None:
        raise ValueError(f"未找到P偶像卡资源：{skin_id} {name}")

    download_to(asset_id0, path0)
    # 转换分辨率 140x188
    img0 = cv2.imread(path0)
    assert img0 is not None
    img0 = cv2.resize(img0, (140, 188), interpolation=cv2.INTER_AREA)
    cv2.imwrite(path0, img0)

    download_to(asset_id1, path1)
    # 转换分辨率 140x188
    img1 = cv2.imread(path1)
    assert img1 is not None
    img1 = cv2.resize(img1, (140, 188), interpolation=cv2.INTER_AREA)
    cv2.imwrite(path1, img1)

print('下载技能卡资源...')
SKILL_CARD_PATH = './kotonebot/kaa/resources/skill_cards'
os.makedirs(SKILL_CARD_PATH, exist_ok=True)

cursor = db.execute("""
SELECT
    DISTINCT assetId,
    isCharacterAsset
FROM ProduceCard;
""")

for row in tqdm.tqdm(cursor.fetchall()):
    asset_id, is_character_asset = row
    assert asset_id is not None
    if not is_character_asset:
        path = SKILL_CARD_PATH + f'/{asset_id}.png'
        download_to(asset_id, path)
    else:
        for ii in CharacterId:
            actual_asset_id = f'{asset_id}-{ii.value}'
            path = SKILL_CARD_PATH + f'/{actual_asset_id}.png'
            download_to(actual_asset_id, path)
