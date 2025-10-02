import logging
from collections import deque

import cv2
import numpy as np
from kotonebot import action
from cv2.typing import MatLike
from kotonebot.primitives import RectTuple

from kaa.tasks import R
from kaa.util import paths
from kaa.db.drink import Drink
from kaa.image_db import ImageDatabase, HistDescriptor, FileDataSource

logger = logging.getLogger(__name__)
_db: ImageDatabase | None = None

def preprocess_drink_slot_img(img: MatLike) -> MatLike:
    """预处理饮品图像，使得图像识别结果更正确
    
    :param img: 输入的饮品槽图像，大小 68x68 (BGR)
    :return: 处理后的图像，大小 68x68，其中会出现更大量的纯白色，便于识别
    """
    BLUE_THRESHOLD = 255
    FLOOD_BLUE_THRESHOLD = 240
    FLOOD_COLOR_THRESHOLD = 230

    assert img.shape[2] == 3
    h, w, _ = img.shape

    # 分通道
    b, g, r = cv2.split(img)

    # 把 b==255 的像素修正为纯白
    mask = (b >= BLUE_THRESHOLD)
    g[mask] = 255
    b[mask] = 255
    r[mask] = 255
    img = cv2.merge([b, g, r])

    # BFS 把边缘连通区域染成纯白
    visited = np.zeros((h, w), dtype=bool)
    q = deque()

    # 从边缘像素开始
    for x in range(w):
        q.append((0, x))
        q.append((h - 1, x))
    for y in range(h):
        q.append((y, 0))
        q.append((y, w - 1))
    
    # 右上角禁止传播，因为一些饮料的管子会插到圈圈外面，导致白色泄露
    right_top_x = w / 2
    right_top_y = h / 4

    while q:
        y, x = q.popleft()
        if not (0 <= x < w and 0 <= y < h):
            continue
        if visited[y, x]:
            continue
        visited[y, x] = True

        # 设置为白色
        img[y, x] = [255, 255, 255]

        # 四邻域扩展
        for dy, dx in [(-1,0), (1,0), (0,-1), (0,1)]:
            ny, nx = y + dy, x + dx
            if 0 <= nx < w and 0 <= ny < h and not (nx > right_top_x and ny < right_top_y) and not visited[ny, nx] and not np.all(img[ny, nx] >= FLOOD_COLOR_THRESHOLD) and not (img[ny, nx][0] >= FLOOD_BLUE_THRESHOLD):
                q.append((ny, nx))

    return img

def drinks_db() -> ImageDatabase:
    global _db
    if _db is None:
        logger.info('Loading drinks database...')
        path = paths.resource('drinks')
        db_path = paths.cache('drinks.pkl')
        _db = ImageDatabase(FileDataSource(str(path)), db_path, HistDescriptor(8), name='drinks')
    return _db

def match_first_drinks(img: MatLike, delta_threshold: float = 0.7) -> Drink | None:
    """
    将给定图像与所有饮品 进行匹配，并返回最接近的一个饮品

    :img: 输入图像，格式为 BGR 68x68 左右。
    :delta_threshold: 距离差值阈值，如果第1个匹配结果和第2个匹配结果的 距离的差值 超过delta_threshold，那么才视为匹配成功。
    :return: 若匹配成功，则返回 饮品的信息 和 前1~3个匹配饮品的数据库查询结果（用于更详细的日志输出）；否则返回 None。
    """


    # cv2.imshow("img", img)
    img = preprocess_drink_slot_img(img)
    # cv2.imshow("img1", img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    
    db = drinks_db()
    matches = db.match_all(img, threshold=114514)
    if len(matches) == 0:
        return None

    asset_id = matches[0].key.strip().split('.')[0]
    drink = Drink.from_asset_id(asset_id)
    if drink is None:
        return None

    if len(matches) == 1:
        logger.info("Only 1 drink match result: %s", str(drink.name))
        return drink
    
    matches = matches[:3]
    matches_distance = [round(m.distance, 2) for m in matches]

    if matches[1].distance - matches[0].distance <= delta_threshold:
        logger.info(
            "Mismatched drink: %s. First 3 matches distance: %s. Delta: %s",
            str(drink.name),
            str(matches_distance),
            str(round(matches[1].distance - matches[0].distance, 2))
        )
        return None

    logger.info(
        "Matched drink: %s. First 3 matches distance: %s. Delta: %s",
        str(drink.name),
        str(matches_distance),
        str(round(matches[1].distance - matches[0].distance, 2))
    )
    return drink

@action('定位考试中出现的所有饮品', screenshot_mode='manual')
def locate_all_drinks_in_3_drink_slots(img: MatLike) -> list[tuple[Drink, RectTuple]]:
    """
    将当前图像的左下角的3个饮品槽与所有饮品 进行匹配，并返回匹配上的所有饮品和他们的位置

    :img: 输入图像，格式为 BGR 720x1280。
    :return: 若匹配成功，则返回饮品的信息，否则返回 None。
    """
    
    potential_rects: list[RectTuple] = [
        R.InPurodyuusu.BoxDrink1.rect,
        R.InPurodyuusu.BoxDrink2.rect,
        R.InPurodyuusu.BoxDrink3.rect
    ]

    results = list[tuple[Drink, RectTuple]]()

    for rect in potential_rects:
        x, y, w, h = rect
        img_slot = img[y:y+h, x:x+w]

        drink = match_first_drinks(img_slot)

        if drink is not None:
            results.append((drink, rect))

    return results

if __name__ == '__main__':
    from logging import getLogger
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')

    # img = R.InPurodyuusu.Screenshot5Cards.data # len = 2
    # img = R.InPurodyuusu.ScreenshotSenseiTipConsult.data # len = 3
    # img = R.InPurodyuusu.Screenshot1Cards.data # len = 2
    # img = R.InPurodyuusu.ScreenshotDrinkTest.data # len = 2
    # img = R.InPurodyuusu.Screenshot4Cards.data # len = 0
    img = R.InPurodyuusu.ScreenshotDrinkTest3.data # len = 1
    results = locate_all_drinks_in_3_drink_slots(img)
    print(len(results), ":", results)