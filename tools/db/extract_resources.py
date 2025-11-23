# 此脚本用于读入 extract_schema.py 生成的数据库文件，
# 并下载对应的资源

import os
import sys
import tqdm
import sqlite3
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Tuple

import cv2
import requests
import urllib3

from kaa.db.constants import CharacterId

sys.path.append(os.path.abspath('./submodules/GkmasObjectManager'))

import GkmasObjectManager as gom # type: ignore

print('拉取清单文件...')
manifest = gom.fetch()


def make_image_validator(expected_size: tuple[int, int]) -> Callable[[str], bool]:
    """
    Creates a validation function that checks if an image file has the expected dimensions.

    :param expected_size: A tuple (width, height).
    :return: A function that takes a file path and returns True if the image has the correct size.
    """
    def validator(path: str) -> bool:
        try:
            img = cv2.imread(path)
            if img is None:
                print(f"Validation failed: OpenCV cannot read {path}")
                return False
            # img.shape is (height, width, channels)
            actual_size = (img.shape[1], img.shape[0])
            if actual_size != expected_size:
                print(f"Validation failed: incorrect size for {path}. Expected {expected_size}, got {actual_size}")
                return False
            return True
        except Exception as e:
            print(f"Validation failed: error reading {path}: {e}")
            return False
    return validator


# 定义下载任务类型：(资源ID, 下载路径, 下载完成后调用的函数, 验证函数)
DownloadTask = Tuple[str, str, Callable[[str], None] | None, Callable[[str], bool] | None]
download_tasks: List[DownloadTask] = []

MAX_RETRY_COUNT = 5
MAX_WORKERS = 32  # 最大并发下载数

def download_to(asset_id: str, path: str, overwrite: bool = False) -> bool:
    """
    单个文件下载函数
    
    :return: 是否下载了文件。如果文件已存在且未指定 overwrite，则返回 False。
    :raises: 如果下载失败，则抛出异常。
    """
    retry_count = 1
    while True:
        try:
            if not overwrite and os.path.exists(path):
                print(f'Skipped {asset_id}.')
                return False
            manifest.download(asset_id, path=path, categorize=False, no_progress=True)
            return True
        except (requests.exceptions.ReadTimeout, requests.exceptions.SSLError, requests.exceptions.ConnectionError, urllib3.exceptions.MaxRetryError) as e:
            retry_count += 1
            if retry_count >= MAX_RETRY_COUNT:
                raise e
            print(f'Network error: {e}')
            print('Retrying...')

def run(tasks: List[DownloadTask], description: str = "下载中") -> None:
    """并行执行下载任务列表"""
    def _download(task: DownloadTask) -> None:
        asset_id, path, post_process_func, validator = task
        try:
            downloaded = download_to(asset_id, path)
            if downloaded:
                if post_process_func is not None:
                    post_process_func(path)
            
            if validator is not None:
                # Validate for both downloaded and skipped files
                if os.path.exists(path):
                    if not validator(path):
                        os.remove(path) # Delete invalid file
                        print(f"Validation failed for {path}, file removed and marked for retry.")
                        return # Exit _download for this task, it's handled by retry.
                elif downloaded:
                    # This case means download_to returned True but file is not there.
                    raise FileNotFoundError(f"File {path} not found after reported download.")

        except Exception:
            print(f'Failed to download or validate {asset_id}')
            traceback.print_exc()
            raise
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {executor.submit(_download, task): task for task in tasks}

        with tqdm.tqdm(total=len(tasks), desc=description) as pbar:
            for future in as_completed(future_to_task):
                future.result()
                pbar.update(1)

# 创建目录
print("创建资源目录...")
IDOL_CARD_PATH = './kaa/resources/idol_cards'
SKILL_CARD_PATH = './kaa/resources/skill_cards'
DRINK_PATH = './kaa/resources/drinks'
os.makedirs(IDOL_CARD_PATH, exist_ok=True)
os.makedirs(SKILL_CARD_PATH, exist_ok=True)
os.makedirs(DRINK_PATH, exist_ok=True)

db = sqlite3.connect("./kaa/resources/game.db")

def resize_idol_card_image(path: str) -> None:
    """偶像卡图片后处理：调整分辨率为 140x188"""
    if os.path.exists(path):
        img = cv2.imread(path)
        if img is not None:
            img = cv2.resize(img, (140, 188), interpolation=cv2.INTER_AREA)
            cv2.imwrite(path, img)

def resize_drink_image(path: str) -> None:
    """偶像卡图片后处理：调整分辨率为 68x68"""
    if os.path.exists(path):
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            img = cv2.resize(img, (68, 68), interpolation=cv2.INTER_AREA)

            # 学偶饮料素材，alpha==0的区域，rgb不一定为0；此处进行一个清空
            assert img.shape[2] == 4 # 确定是4通道RGBA
            b, g, r, a = cv2.split(img)

            mask = (a == 0)
            b[mask] = 255
            g[mask] = 255
            r[mask] = 255

            img_clean = cv2.merge([b, g, r]) # 去掉alpha通道

            cv2.imwrite(path, img_clean)

################################################

# 1. 构建 P 偶像卡下载任务
print("添加 P 偶像卡任务...")
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

for row in tqdm.tqdm(cursor.fetchall(), desc="构建偶像卡任务"):
    _, skin_id, name, asset_id, _, _ = row

    if asset_id is None:
        raise ValueError(f"未找到P偶像卡资源：{skin_id} {name}")

    validator = make_image_validator((140, 188))

    # 低特训等级
    asset_id0 = f'img_general_{asset_id}_0-thumb-portrait'
    path0 = IDOL_CARD_PATH + f'/{skin_id}_0.png'
    download_tasks.append((asset_id0, path0, resize_idol_card_image, validator))

    # 高特训等级
    asset_id1 = f'img_general_{asset_id}_1-thumb-portrait'
    path1 = IDOL_CARD_PATH + f'/{skin_id}_1.png'
    download_tasks.append((asset_id1, path1, resize_idol_card_image, validator))

# # 2. 构建技能卡下载任务
# print("添加技能卡任务...")
# cursor = db.execute("""
# SELECT
#     DISTINCT assetId,
#     isCharacterAsset
# FROM ProduceCard;
# """)

# for row in tqdm.tqdm(cursor.fetchall(), desc="构建技能卡任务"):
#     asset_id, is_character_asset = row
#     assert asset_id is not None
#     if not is_character_asset:
#         path = SKILL_CARD_PATH + f'/{asset_id}.png'
#         download_tasks.append((asset_id, path, None, None))
#     else:
#         for ii in CharacterId:
#             actual_asset_id = f'{asset_id}-{ii.value}'
#             path = SKILL_CARD_PATH + f'/{actual_asset_id}.png'
#             download_tasks.append((actual_asset_id, path, None, None))

# 3. 构建饮品下载任务
print("添加饮品任务...")
cursor = db.execute("""
SELECT
    DISTINCT assetId
FROM ProduceDrink;
""")

for row in tqdm.tqdm(cursor.fetchall(), desc="构建饮品任务"):
    asset_id = row[0]
    assert asset_id is not None
    path = DRINK_PATH + f'/{asset_id}.png'
    download_tasks.append((asset_id, path, resize_drink_image, make_image_validator((68, 68))))

print(f'开始下载 {len(download_tasks)} 个资源，并发数 {MAX_WORKERS}...')
run(download_tasks)

################################################
# 检查下载结果并重试失败的文件
################################################

def check_downloaded_files(tasks: List[DownloadTask]) -> List[DownloadTask]:
    """检查所有下载的文件，返回需要重试的任务列表"""
    failed_tasks = []

    print("检查下载的文件...")
    for task in tqdm.tqdm(tasks, desc="检查文件"):
        _, path, _, validator = task

        # 检查文件是否存在
        if not os.path.exists(path):
            print(f"文件不存在: {path}")
            failed_tasks.append(task)
            continue

        # 使用自定义验证器（如果提供）
        if validator and not validator(path):
            failed_tasks.append(task)
            continue

        # 使用 OpenCV 读取图片检查是否为空
        try:
            img = cv2.imread(path)
            if img is None:
                print(f"OpenCV 无法读取文件: {path}")
                failed_tasks.append(task)
                continue

            # 检查图片尺寸是否合理
            if img.shape[0] == 0 or img.shape[1] == 0:
                print(f"图片尺寸异常: {path}, 尺寸: {img.shape}")
                failed_tasks.append(task)
                continue

        except Exception as e:
            print(f"检查文件时出错: {path}, 错误: {e}")
            failed_tasks.append(task)
            continue

    return failed_tasks

# 执行检查和重试
max_retry_rounds = 3
retry_round = 0
failed_tasks = []

while retry_round < max_retry_rounds:
    failed_tasks = check_downloaded_files(download_tasks)

    if not failed_tasks:
        print("所有文件验证成功！")
        break

    print(f"发现 {len(failed_tasks)} 个失败的文件，开始第 {retry_round + 1} 轮重试...")

    # 删除失败的文件，准备重新下载
    for task in failed_tasks:
        _, path, _, _ = task
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"删除损坏文件: {path}")
            except Exception as e:
                print(f"删除文件失败: {path}, 错误: {e}")

    # 重新下载失败的文件
    try:
        run(failed_tasks, f"重试下载 (第 {retry_round + 1} 轮)")
        retry_round += 1
    except Exception as e:
        print(f"重试下载时出错: {e}")
        break

if failed_tasks:
    print(f"警告：仍有 {len(failed_tasks)} 个文件下载失败：")
    for task in failed_tasks:
        asset_id, path, _, _ = task
        print(f"  - {asset_id} -> {path}")


db.close()
