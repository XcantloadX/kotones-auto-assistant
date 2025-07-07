import logging
from dataclasses import dataclass

import cv2
import numpy as np
from cv2.typing import MatLike

from kotonebot.kaa.tasks import R
from kotonebot.primitives import Rect
from kotonebot.kaa.util import paths
from kotonebot.kaa.image_db import ImageDatabase, HistDescriptor, FileDataSource
from kotonebot.kaa.db import SkillCard

BIN_COUNT = 10
logger = logging.getLogger(__name__)
_db: ImageDatabase | None = None

@dataclass
class SkillCardElement:
    rect: Rect
    skill_card: SkillCard | None

def _find_cards(img: MatLike) -> list[Rect]:
    x, y, w, h = R.InPurodyuusu.BoxSelectCardDialogCards.xywh
    # 非目标区域置白
    white = np.full_like(img, 255)
    white[y:y+h, x:x+w] = img[y:y+h, x:x+w]
    img = white
    # cv2.imshow('White', cv2.resize(img, (0, 0), fx=0.5, fy=0.5))
    # 灰度、高斯模糊、查找边缘、查找轮廓
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.GaussianBlur(img, (21, 21), 0)
    img = cv2.Canny(img, 30, 100)
    # cv2.imshow('Canny', cv2.resize(img, (0, 0), fx=0.5, fy=0.5))
    contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = np.zeros_like(img)
    # 筛选比例 1:1 的轮廓
    results = []
    for contour in contours:
        rx, ry, rw, rh = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if rw == 0 or rh == 0:
            continue
        ratio = rw / rh
        # print(rw * rh)
        if 0.8 <= ratio <= 1.2 and rw * rh > 6000:
            results.append(Rect(rx, ry, rw, rh))
            # result = cv2.rectangle(result, (rx, ry), (rx+rw, ry+rh), (0, 255, 0), 2)
            # cv2.imshow('Card ' + str(len(results)), white[ry:ry+rh, rx:rx+rw])
    # cv2.imshow('Contours', cv2.resize(result, (0, 0), fx=0.5, fy=0.5))
    results.sort(key=lambda p: p.x1)
    logger.debug(f'{len(results)} cards detected.')
    return results

def cards_db() -> ImageDatabase:
    global _db
    if _db is None:
        logger.info('Loading skill cards database...')
        path = paths.resource('skill_cards')
        db_path = paths.cache('skill_cards.pkl')
        _db = ImageDatabase(FileDataSource(str(path)), db_path, HistDescriptor(BIN_COUNT), name='skill_cards')
    return _db

def extract_cards(img: MatLike) -> list[SkillCardElement]:
    db = cards_db()
    results = []
    for rect in _find_cards(img):
        x, y, w, h = rect.xywh
        card_img = img[y:y+h, x:x+w]
        match = db.match(card_img, 20)
        if match:
            logger.debug('Skill card match: %s', match)
            asset_id = match.key.split('.')[0]
            results.append(SkillCardElement(rect, SkillCard.from_asset_id(asset_id)))
    return results

if __name__ == '__main__':
    from pprint import pprint
    path = r"E:\GithubRepos\KotonesAutoAssistant.worktrees\feat\kotonebot-resource\sprites\jp\in_purodyuusu\screenshot_select_skill_card_2.png"
    img = cv2.imread(path)
    pprint(extract_cards(img))
    cv2.waitKey(0)
