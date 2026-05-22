from dataclasses import dataclass
from functools import cached_property
import os
import cv2
import logging
from typing_extensions import override

from cv2.typing import MatLike
from kaa.db.constants import CharacterId
from kaa.image_db.descriptors.hog import HogDescriptor
from kotonebot import image
from kotonebot.primitives import Rect
from kotonebot.core import GameObject
from kotonebot.backend import color

from kaa.tasks import R
from kaa.util import paths
from kaa.image_db import ImageDatabase, FileDataSource
from kaa.db.skill_card import SkillCard

DEBUG = False
CARD_OFFSET = (57, 148) # 从字母位置到卡片左上角的偏移量 x, y
CARD_SCALE = 168 / 256 # 原始卡面图像 到 1280x720 截图中卡面图像的缩放比例

logger = logging.getLogger(__name__)
_db: ImageDatabase | None = None

@dataclass
class CardGameObject(GameObject):
    rect: Rect
    res_name: str
    card: SkillCard | None

    _screenshot: MatLike
    _letter_rect: Rect

    @cached_property
    def available(self):
        return color.find(self._screenshot, '#7a7d7d', rect=self._letter_rect) is None
    
    def __repr__(self) -> str:
        return f'CardGameObject(res_name={self.res_name}, card={self.card}, available={self.available}, _screenshot={"<...>" if self._screenshot is not None else "<None>"}, _letter_rect={self._letter_rect})'

class CardImageDatabase(ImageDatabase):
    @override
    def insert(self, key, image, *, overwrite = False):
        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                raise ValueError(f'Cannot read image from path: {image}')
        else:
            img = image
        # 截取从下边缘中点为右下角，
        # 到 CARD_OFFSET * CARD_SCALE 为左上角的区域
        h, w, _ = img.shape
        x2, y2 = w // 2, h  # 右下角
        x1 = int(x2 - CARD_OFFSET[0] / CARD_SCALE)
        y1 = int(y2 - CARD_OFFSET[1] / CARD_SCALE)
        half_img = img[y1:y2, x1:x2]

        # if DEBUG:
        #     debug_img = img.copy()
        #     cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        #     cv2.imshow('original_with_rect', cv2.resize(debug_img, (0,0), fx=0.5, fy=0.5))
        #     cv2.imshow('half_img', cv2.resize(half_img, (0,0), fx=2, fy=2))
        #     cv2.waitKey(0)
        return super().insert(key, half_img, overwrite=overwrite)

def skill_cards_db() -> ImageDatabase:
    global _db
    if _db is None:
        logger.info('Loading skill_cards database...')
        path = paths.resource('skill_cards')
        db_path = paths.cache('skill_cards.pkl')
        _db = CardImageDatabase(FileDataSource(str(path)), db_path, HogDescriptor(), name='skill_cards')
    return _db


def _show_rects(title: str, img: MatLike, results: list[GameObject] | list[Rect]):
    if not DEBUG:
        return
    debug_img = img.copy()
    for res in results:
        if isinstance(res, Rect):
            x, y, w, h = res.xywh
        else:
            x, y, w, h = res.rect.xywh
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.imshow(title, cv2.resize(debug_img, (0, 0), fx=0.5, fy=0.5))

def _locate_letters(img: MatLike) -> list[Rect]:
    # letters = AnyOf[
    #     R.InPurodyuusu.A,
    #     R.InPurodyuusu.M,
    #     R.InPurodyuusu.T,
    # ].find_all()
    x, y, w, h = R.InPurodyuusu.BoxCardLetter.xywh
    img = img[y:y+h, x:x+w]
    results = image.raw().find_all(img, R.InPurodyuusu.A.template)
    results += image.raw().find_all(img, R.InPurodyuusu.M.template)
    results += image.raw().find_all(img, R.InPurodyuusu.T.template)
    # 需要还原为全图坐标
    results2 = []
    for res in results:
        results2.append(Rect(res.rect.x1 + x, res.rect.y1 + y, res.rect.w, res.rect.h))

    _show_rects('letters', img, results2)
    return results2

def locate_cards(img: MatLike):
    letters = _locate_letters(img)
    # 根据字母的位置，计算出左半边卡面的范围
    # 字母往上 195px，往左 95px
    card_regions = []
    for l in letters:
        x2, y2 = l.center.x, l.top_left.y # x 坐标取中心，y 坐标取上边缘
        x1 = x2 - CARD_OFFSET[0]
        y1 = y2 - CARD_OFFSET[1]
        card_regions.append(Rect.from_xyxy(x1, y1, x2, y2))
    
    _show_rects('cards', img, card_regions)

    # 根据图像查卡片
    results: list[CardGameObject | None] = []
    for region, letter in zip(card_regions, letters):
        x, y, w, h = region.xywh
        card_img = img[y:y+h, x:x+w]
        result = skill_cards_db().match(card_img, threshold=150)
        available = color.find(img, '#7a7d7d', rect=letter) is None
        if result is not None:
            # 从资源名称中提取 asset_id
            card_id = result.key.removesuffix('.png')
            for c in CharacterId:
                suffix = '-' + c.value
                card_id = card_id.removesuffix(suffix)
            # 查数据库
            db_card = SkillCard.from_asset_id(card_id)
            card = CardGameObject(
                rect=region,
                res_name=result.key,
                card=db_card,
                _screenshot=img,
                _letter_rect=letter,
            )
            results.append(card)
            if card.card is not None:
                logger.info(f'Matched skill card: {card.res_name}({card.card.name}) | dist={result.distance:.2f} available={available}')
            else:
                logger.warning(f'Found skill card {card.res_name} but no database match found.')
        else:
            logger.warning('No matching skill card found.')
            results.append(None)
    results.sort(key=lambda r: r.rect.x1 if r is not None else 1e9)

    # 绘制debug结果
    # 新建一张与原图一样大小的空白图，把卡片完整图像绘制到识别区域上
    if DEBUG:
        preview = img.copy() * 0
        for res in results:
            if res is None:
                continue
            draw_rect = res.rect.copy()
            orig_card_path = os.path.join(paths.resource('skill_cards'), res.res_name)
            orig_card_img = cv2.imread(orig_card_path)
            assert orig_card_img is not None
            orig_card_img = cv2.resize(orig_card_img, None, fx=CARD_SCALE, fy=CARD_SCALE)
            x1, y1 = draw_rect.top_left
            x2, y2 = x1 + orig_card_img.shape[1], y1 + orig_card_img.shape[0]
            preview[y1:y2, x1:x2] = orig_card_img

            x, y, w, h = res.rect.xywh
        cv2.imshow('matched_cards', cv2.resize(preview, (0,0), fx=0.5, fy=0.5))
        cv2.waitKey(1)
    return results


if __name__ == "__main__":
    # sample = cv2.imread('f:/1.png')
    # db = skill_cards_db()
    # result = db.match(sample)
    # print(result)

    skill_cards_db()
    from pprint import pprint
    from time import time
    from kotonebot import device
    while True:
        img = device.screenshot()
        start_time = time()
        cards = locate_cards(img)
        end_time = time()
        print(f'Locate cards took {end_time - start_time:.2f} seconds')
        # pprint(cards)
        cv2.waitKey(0)