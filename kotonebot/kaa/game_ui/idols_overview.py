import os
import logging

import cv2
import numpy as np
from cv2.typing import MatLike

from kotonebot.kaa.tasks import R
from kotonebot.kaa.util import paths
from kotonebot.primitives import RectTuple, Rect
from kotonebot.kaa.game_ui import Scrollable
from kotonebot import device, action
from kotonebot.kaa.image_db import ImageDatabase, HistDescriptor, FileDataSource
from kotonebot.backend.preprocessor import HsvColorsRemover

logger = logging.getLogger(__name__)
_db: ImageDatabase | None = None

# OpenCV HSV 颜色范围
RED_DOT = ((157, 205, 255), (179, 255, 255))  # 红点
ORANGE_SELECT_BORDER = ((9, 50, 106), (19, 255, 255))  # 当前选中的偶像的橙色边框
WHITE_BACKGROUND = ((0, 0, 234), (179, 40, 255))  # 白色背景


def extract_idols(img: MatLike) -> list[RectTuple]:
    """
    寻找给定图像中的所有偶像。

    :img: 输入图像，格式为 BGR 720x1280。
    :return: 所有偶像的矩形区域 `(x, y, w, h)`，如果未找到则返回空列表。
    """
    # 移除不需要的颜色
    remover = HsvColorsRemover([RED_DOT, ORANGE_SELECT_BORDER, WHITE_BACKGROUND])
    img = remover.process(img)
    # 灰度、查找轮廓
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 筛选面积、比例约为 140x190 的轮廓
    rects = []
    target_ratio = 140 / 190  # 目标宽高比
    target_area = 140 * 190  # 目标面积
    ratio_tolerance = 0.1  # 允许的误差范围
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h == 0:
            continue
        ratio = w / h
        if abs(ratio - target_ratio) <= ratio_tolerance and w * h >= target_area:
            rects.append((x, y, w, h))
    return rects


def display_rects(img: MatLike, rects: list[RectTuple]) -> MatLike:
    """Draw rectangles on the image and display them."""
    result = img.copy()
    for rect in rects:
        x, y, w, h = rect
        # Draw rectangle with green color and 2px thickness
        cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # Optionally add text label
        cv2.putText(result, f"{w}x{h}", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return result


def draw_idol_preview(img: MatLike, rects: list[RectTuple], db: ImageDatabase, idol_path: str) -> MatLike:
    """
    在预览图上绘制所有匹配到的偶像。
    
    :param img: 原始图像
    :param rects: 检测到的偶像矩形区域列表
    :param db: 偶像图像数据库
    :param idol_path: 偶像图像文件路径
    :return: 带有匹配偶像的预览图
    """
    # 创建一个与原图大小相同的白色背景图片
    preview_img = np.ones_like(img) * 255

    # 在预览图上绘制所有匹配到的偶像
    for rect in rects:
        x, y, w, h = rect
        idol_img = img[y:y + h, x:x + w]
        match = db.match(idol_img, 20)
        if not match:
            continue
        file = os.path.join(idol_path, match.key)
        found_img = cv2_imread(file)

        # 将找到的偶像图片缩放至与检测到的矩形大小相同
        resized_found_img = cv2.resize(found_img, (w, h))

        # 将缩放后的图片放到预览图上对应位置
        preview_img[y:y + h, x:x + w] = resized_found_img

        # 在预览图上绘制矩形框
        cv2.rectangle(preview_img, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # 可选：添加偶像ID标签
        cv2.putText(preview_img, match.key.split('.')[0], (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return preview_img


def idols_db() -> ImageDatabase:
    global _db
    if _db is None:
        logger.info('Loading idols database...')
        path = paths.resource('idol_cards')
        db_path = paths.cache('idols.pkl')
        _db = ImageDatabase(FileDataSource(str(path)), db_path, HistDescriptor(8), name='idols')
    return _db


@action('定位偶像', screenshot_mode='manual-inherit')
def locate_idol(skin_id: str):
    device.screenshot()
    logger.info('Locating idol %s', skin_id)
    x, y, w, h = R.Produce.BoxIdolOverviewIdols.xywh
    db = idols_db()
    sc = Scrollable(color_schema='light')

    sc.update()
    logger.debug('Idol preview pages count: %s', repr(sc.page_count))
    pc = sc.page_count
    assert pc is not None
    # 1280x720 分辨率下，一行 4 个，一页共 12 个。
    # 一次只翻 0.8 行。
    for _ in sc(4 / (pc * 12) * 0.8):
        img = device.screenshot()
        # 只保留 BoxIdolOverviewIdols 区域
        mask = np.zeros_like(img)
        mask[y:y + h, x:x + w] = img[y:y + h, x:x + w]
        img = mask
        # 检测 & 查询
        rects = extract_idols(img)
        # cv2.imshow('Detected Idols', cv2.resize(display_rects(img, rects), (0, 0), fx=0.5, fy=0.5))
        # cv2.imshow('Idols Preview', cv2.resize(draw_idol_preview(img, rects, db, paths.resource('idol_cards')), (0, 0), fx=0.5, fy=0.5))
        # cv2.waitKey(0)
        for rect in rects:
            rx, ry, rw, rh = rect
            idol_img = img[ry:ry + rh, rx:rx + rw]
            match = db.match(idol_img, 20)
            logger.debug('Result rect: %s, match: %s', repr(rect), repr(match))
            # Key 格式：{skin_id}_{index}
            # 同一张卡升级前后图片不一样，index 分别为 0 和 1
            if match and match.key.startswith(skin_id):
                logger.info('Found idol %s', skin_id)
                return Rect(rx, ry, rw, rh)
    return None
    # cv2.imshow('Detected Idols', cv2.resize(display_rects(img, rects), (0, 0), fx=0.5, fy=0.5))

    # # 使用新函数绘制预览图
    # preview_img = draw_idol_preview(img, rects, db, path)


@action('重新培育页面识别偶像卡', screenshot_mode='manual-inherit')
def find_idol_skin_id_on_resume_produce(img: MatLike) -> str | None:
    """
    在 继续培育 界面查找偶像皮肤id
    默认 数据库中的key 为 偶像皮肤id_\d.png 
    :return: 
    """
    db = idols_db()
    rx, ry, rw, rh = R.Produce.BoxResumeDialogIdolCard.xywh
    idol_img = img[ry:ry + rh, rx:rx + rw]
    match = db.match(idol_img, 20)
    if match:
        return match.key.rsplit("_", 1)[0]
    else:
        return None


def test():
    from kotonebot.backend.context import init_context, manual_context
    init_context()
    manual_context().begin()
    locate_idol('i_card-skin-fktn-3-006')


if __name__ == '__main__':
    from kotonebot.util import cv2_imread

    test()
