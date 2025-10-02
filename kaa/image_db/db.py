import os
import pickle
import logging
from dataclasses import dataclass
from typing import Any, NamedTuple, Protocol, Iterator

import cv2
import numpy as np
from cv2.typing import MatLike

from .descriptors import HistDescriptor
from kotonebot.backend.core import cv2_imread

logger = logging.getLogger(__name__)

DATABASE_INTERNAL_VERSION = 0

@dataclass
class Db:
    """数据库"""
    internal_version: int
    """数据库内部版本号"""
    version: str | None
    """保留字段"""
    name: str | None
    """数据库名称"""
    data: dict[str, Any]
    """数据"""

    def insert(self, key: str, value: Any):
        self.data[key] = value

    def count(self):
        return len(self.data)

class DataSource(Protocol):
    def __iter__(self) -> Iterator[tuple[str, Any]]:
        ...

class FileDataSource(DataSource):
    def __init__(self, folder_path: str, keep_ext: bool = True):
        self.path = os.path.abspath(folder_path)
        self.keep_ext = keep_ext

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for file in os.listdir(self.path):
            if not self.keep_ext:
                file = os.path.splitext(file)[0]
            yield file, cv2_imread(os.path.join(self.path, file))

class DatabaseQueryResult(NamedTuple):
    key: str
    feature: Any
    distance: float

    def __repr__(self):
        return f'DatabaseQueryResult(key={self.key}, distance={self.distance})'

def chi2_distance(hist1: np.ndarray, hist2: np.ndarray, eps=1e-10):
    return 0.5 * np.sum((hist1 - hist2) ** 2 / (hist1 + hist2 + eps))

class ImageDatabase:
    def __init__(
            self,
            source: DataSource,
            db_path: str,
            descriptor: HistDescriptor,
            *,
            name: str | None = None
        ):
        self.db_path = db_path
        self.__db: Db | None = None
        self.descriptor = descriptor
        self.source = source

        # 载入数据库
        logger.info('Loading database from %s...', db_path)
        if os.path.exists(db_path):
            try:
                with open(db_path, 'rb') as f:
                    self.__db = pickle.load(f)
                logger.info('Database loaded. Name=%s, version=%s, count=%d', self.db.name, self.db.version, self.db.count())
            except Exception as e:
                logger.warning('Failed to load database from %s: %s', db_path, e)
                self.__db = None
        if self.__db is None:
            self.__db = Db(DATABASE_INTERNAL_VERSION, None, name, {})
        
        # 检查版本
        if self.db.internal_version != DATABASE_INTERNAL_VERSION:
            logger.info('Database internal version is %d, expected %d. Clearing database...', self.db.internal_version, DATABASE_INTERNAL_VERSION)
            self.db.data.clear()
            self.db.internal_version = DATABASE_INTERNAL_VERSION
        
        # 载入数据源
        logger.debug('Loading data source...')
        for key, value in self.source:
            try:
                self.insert(key, value)
            except Exception as e:
                logger.error(
                    "\n"
                    "Error inserting key: %s\n"
                    "Error message: %s\n"
                    "资源可能损坏，请检查并删除 `kaa/resources/idol_cards` 下的损坏文件，"
                    "然后重新执行 `tools/db/extract_resources.py`",
                    key,
                    str(e).strip()
                )
                raise # 继续抛异常，让程序崩溃
        self.save()
        
    @property
    def db(self) -> Db:
        if not self.__db:
            raise RuntimeError('Database not loaded')
        return self.__db

    def save(self):
        with open(self.db_path, 'wb') as f:
            pickle.dump(self.db, f)

    def insert(self, key: str, image: MatLike | str, *, overwrite: bool = False):
        """
        向图像数据库中插入一条新记录。

        :param key: 图片的 ID。
        :param image: 图片的路径或 MatLike。
            若为 MatLike，必须为 BGR 格式。
        :param overwrite: 是否覆盖已存在的记录。
        """
        if isinstance(image, str):
            image = cv2_imread(image)
        if overwrite or key not in self.db.data:
            self.db.insert(key, self.descriptor(image))
            logger.debug('Inserted image: %s', key)

    def insert_many(self, images: dict[str, str | MatLike], *, overwrite: bool = False):
        """
        向图像数据库中插入多条新记录。

        :param images: 图片。key 为图片的 ID，value 为图片的路径或 MatLike。
            若为 MatLike，必须为 BGR 格式。
        :param overwrite: 是否覆盖已存在的记录。
        """
        for name, image in images.items():
            self.insert(name, image, overwrite=overwrite)

    def match_all(self, query: MatLike, threshold: float = 10) -> list[DatabaseQueryResult]:
        """
        搜索图片，返回所有符合阈值要求的图片，并按相似度降序排序。

        :param image: 待搜索的图片。必须为 BGR 格式。
        :param threshold: 距离阈值。阈值越大，对相似度的要求越低。
        :return: 搜索结果。
        """
        query_feature = self.descriptor(query)
        results = list[DatabaseQueryResult]()
        for key, feature in self.db.data.items():
            dist = chi2_distance(query_feature, feature)
            if dist < threshold:
                results.append(DatabaseQueryResult(key, feature, float(dist)))
        results.sort(key=lambda x: x.distance)

        # 可视化
        # print("MinDist = ", results[0].distance, results[1].distance, results[2].distance)
        # cv2.imshow("query", query)
        # # cv2.imshow("query_feature", query_feature)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        return results

    def match(self, query: MatLike, threshold: float = 10) -> DatabaseQueryResult | None:
        """
        匹配图片，寻找与输入图片最相似的图片。

        :param image: 待匹配的图片。必须为 BGR 格式。
        :param threshold: 距离阈值。阈值越大，对相似度的要求越低。
        :return: 匹配结果。
        """
        results = self.match_all(query, threshold)
        if len(results) > 0:
            return results[0]
        else:
            return None
    

if __name__ == '__main__':
    from kaa.image_db.db import Db
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    imgs_path = r'E:\GithubRepos\KotonesAutoAssistant.worktrees\dev\kotonebot\tasks\resources\idol_cards'
    needle_path = r'D:\05.png'
    db = ImageDatabase(FileDataSource(imgs_path), r'D:\idols.pkl', HistDescriptor(8), name='idols')
    # if db.db.count() == 0:
    #     db.insert({file: os.path.join(imgs_path, file) for file in os.listdir(imgs_path)})
    needle = cv2_imread(needle_path)
    result = db.match(needle)
    print(result)
