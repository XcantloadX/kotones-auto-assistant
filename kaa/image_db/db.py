import os
import pickle
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, NamedTuple

import numpy as np
from cv2.typing import MatLike

from .descriptors.base import BaseDescriptor, MetricType
from .datasource import DataSource
from .index import FlatIndex, FaissIndex, FAISS_AVAILABLE

logger = logging.getLogger(__name__)

DATABASE_INTERNAL_VERSION = 1

META_FILENAME = 'meta.pkl'
INDEX_FILENAME = 'index.bin'


class DatabaseQueryResult(NamedTuple):
    """数据库查询结果。

    :param key: 匹配到的图像 key
    :param feature: 特征向量（仅内部使用，可能为 None）
    :param distance: 查询图像与匹配图像之间的距离
    """
    key: str
    feature: Any
    distance: float

    def __repr__(self):
        return f'DatabaseQueryResult(key={self.key}, distance={self.distance})'


@dataclass
class DatabaseMeta:
    """数据库元数据，持久化到 meta.pkl。"""
    internal_version: int
    name: str | None
    version: str | None
    descriptor_type: str
    descriptor_params: dict[str, Any]
    metric_type: str
    dimension: int
    index_type: str
    key_to_id: dict[str, int]
    id_to_key: dict[int, str]
    index_params: dict[str, Any] | None = None


class ImageDatabase:
    """图像数据库。

    使用描述子提取特征，通过后端索引（FlatIndex / FaissIndex）进行相似度检索。
    支持全局描述子（每图 1 个向量）和局部描述子（每图 N 个向量）。

    使用方式：:

        db = ImageDatabase(source, db_dir, descriptor)
        if not db.is_built:
            db.build()
        results = db.query(image, k=3)
    """

    def __init__(
            self,
            source: DataSource,
            db_dir: str,
            descriptor: BaseDescriptor,
            *,
            name: str | None = None
        ):
        """
        :param source: 数据源
        :param db_dir: 数据库目录（存放 meta.pkl + index.bin）
        :param descriptor: 图像描述子
        :param name: 数据库名称（可选）
        """
        self.db_dir = os.path.abspath(db_dir)
        self.descriptor = descriptor
        self.source = source
        self.name = name

        self._meta: DatabaseMeta | None = None
        self._index: FlatIndex | FaissIndex | None = None
        self._built = False

        meta_path = os.path.join(self.db_dir, META_FILENAME)
        index_path = os.path.join(self.db_dir, INDEX_FILENAME)

        if os.path.exists(meta_path) and os.path.exists(index_path):
            try:
                self._load_meta(meta_path)
                self._load_index(index_path)
                self._built = True
                logger.info('Database loaded. name=%s, count=%d', self.name, len(self))
            except Exception as e:
                logger.warning('Failed to load database from %s: %s', db_dir, e)
                self._meta = None
                self._index = None
                self._built = False
        else:
            logger.info('No existing database at %s. Call build() to create it.', db_dir)

    @property
    def is_built(self) -> bool:
        """数据库是否已构建。"""
        return self._built

    def __len__(self) -> int:
        if self._meta is None:
            return 0
        return len(self._meta.key_to_id)

    def build(self):
        """构建数据库索引。

        遍历数据源，提取所有图像的特征向量，训练索引并持久化。
        """
        logger.info('Building database from source...')
        key_to_id: dict[str, int] = {}
        id_to_key: dict[int, str] = {}
        next_id = 0

        all_vectors: list[np.ndarray] = []
        all_ids: list[int] = []

        items = list(self.source)
        total_items = len(items)

        if total_items == 0:
            logger.warning('No images found in source.')
            return

        workers = min(os.cpu_count() or 4, 4)
        logger.info('Extracting features with %d workers...', workers)

        def extract(key: str, image: np.ndarray) -> tuple[str, np.ndarray | None]:
            try:
                features = self.descriptor.compute(image)
                if features.shape[0] == 0:
                    return key, None
                return key, features
            except Exception as e:
                logger.error('Error extracting features for %s: %s', key, e)
                return key, None

        completed = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(extract, key, image) for key, image in items]
            for future in as_completed(futures):
                key, features = future.result()
                completed += 1
                if completed % 100 == 0:
                    logger.info('  Progress: %d/%d', completed, total_items)
                if features is None:
                    continue
                image_id = next_id
                next_id += 1
                key_to_id[key] = image_id
                id_to_key[image_id] = key
                all_vectors.append(features)
                all_ids.extend([image_id] * features.shape[0])

        if not all_vectors:
            logger.warning('No valid features extracted from any image.')
            return

        vectors = np.vstack(all_vectors).astype(np.float32)
        ids = np.array(all_ids, dtype=np.int64)
        total_images = next_id
        total_vectors = len(ids)
        logger.info('Collected %d vectors from %d images', total_vectors, total_images)

        d = self.descriptor.dimension
        metric = self.descriptor.metric_type

        if metric == MetricType.CHI2:
            self._index = FlatIndex(d, metric)
        else:
            if not FAISS_AVAILABLE:
                raise ImportError(
                    'faiss-cpu is required for L2/COSINE metrics. '
                    'Install it with: uv pip install faiss-cpu'
                )
            self._index = FaissIndex(d, metric, hnsw=True, hnsw_M=16, hnsw_efSearch=128)

        self._index.train(vectors)
        self._index.add(vectors, ids)

        index_params: dict[str, Any] = {}
        if isinstance(self._index, FaissIndex):
            index_params = {'hnsw': self._index.hnsw}

        self._meta = DatabaseMeta(
            internal_version=DATABASE_INTERNAL_VERSION,
            name=self.name,
            version=None,
            descriptor_type=type(self.descriptor).__name__,
            descriptor_params=self._get_descriptor_params(),
            metric_type=metric.value,
            dimension=d,
            index_type=type(self._index).__name__,
            index_params=index_params,
            key_to_id=key_to_id,
            id_to_key=id_to_key,
        )

        self._save()
        self._built = True
        logger.info('Database built. name=%s, images=%d, total_vectors=%d',
                     self.name, total_images, total_vectors)

    def _get_descriptor_params(self) -> dict[str, Any]:
        params = {}
        for attr in dir(self.descriptor):
            if attr.startswith('_') or attr in ('metric_type', 'dimension', 'compute', '__call__', 'hog', 'sift'):
                continue
            val = getattr(self.descriptor, attr)
            if isinstance(val, (str, int, float, bool, tuple, list, dict)):
                params[attr] = val
        return params

    def _save(self):
        os.makedirs(self.db_dir, exist_ok=True)
        meta_path = os.path.join(self.db_dir, META_FILENAME)
        assert self._meta is not None
        assert self._index is not None
        with open(meta_path, 'wb') as f:
            pickle.dump(self._meta, f)
        index_path = os.path.join(self.db_dir, INDEX_FILENAME)
        self._index.save(index_path)
        logger.debug('Database saved to %s', self.db_dir)

    def _load_meta(self, path: str):
        with open(path, 'rb') as f:
            self._meta: DatabaseMeta = pickle.load(f)
        if self._meta.internal_version != DATABASE_INTERNAL_VERSION:
            raise ValueError(f'Database version mismatch: {self._meta.internal_version} != {DATABASE_INTERNAL_VERSION}')

    def _load_index(self, path: str):
        if self._meta is None:
            raise RuntimeError('Metadata must be loaded before index')
        d = self._meta.dimension
        metric = MetricType(self._meta.metric_type)

        if self._meta.index_type == 'FlatIndex':
            self._index = FlatIndex.load(path, d, metric)
        elif self._meta.index_type == 'FaissIndex':
            hnsw = (self._meta.index_params or {}).get('hnsw', False)
            self._index = FaissIndex.load(path, d, metric, hnsw=hnsw)
        else:
            raise ValueError(f'Unknown index type: {self._meta.index_type}')

    def query(self, image: MatLike, k: int = 1, threshold: float | None = None) -> list[DatabaseQueryResult]:
        """搜索与查询图像最相似的图像。

        对全局描述子（每图 1 向量），直接搜索索引中 top-k 最近邻。
        对局部描述子（SIFT 等），搜索每个 query 描述子的最近邻后按图像 ID 投票。
        投票策略：匹配数最多的图像优先，相同匹配数时取更低距离。

        :param image: 查询图像，BGR 格式
        :param k: 返回的 top-k 结果数量
        :param threshold: 距离阈值，超过此阈值的结果会被过滤
        :return: 按相关性降序排列的结果列表
        """
        if not self._built or self._index is None:
            raise RuntimeError('Database not built. Call build() first.')

        features = self.descriptor.compute(image)
        if features.shape[0] == 0:
            return []

        nq = features.shape[0]
        search_k = k if nq == 1 else 1

        distances, labels = self._index.search(features.astype(np.float32), k=search_k)

        if nq == 1:
            flat_dist = distances[0]
            flat_labels = labels[0]
        else:
            flat_dist = distances[:, 0]
            flat_labels = labels[:, 0]

        if self._meta is None:
            return []

        GOOD_MATCH_MAX_DIST = 20000.0

        score: dict[str, float] = {}
        min_dist: dict[str, float] = {}
        for dist, label in zip(flat_dist, flat_labels):
            if label < 0 or float(dist) > GOOD_MATCH_MAX_DIST:
                continue
            key = self._meta.id_to_key.get(int(label))
            if key is None:
                continue
            d = float(dist)
            score[key] = score.get(key, 0.0) + 1.0 / (1.0 + d)
            if key not in min_dist or d < min_dist[key]:
                min_dist[key] = d

        results = [
            DatabaseQueryResult(key, None, min_dist[key])
            for key in score
            if threshold is None or min_dist[key] < threshold
        ]
        results.sort(key=lambda r: (-score[r.key], r.distance))
        return results[:k]

    def match(self, image: MatLike, threshold: float = 10) -> DatabaseQueryResult | None:
        """匹配最相似的图像（兼容旧接口）。

        :param image: 查询图像，BGR 格式
        :param threshold: 距离阈值
        :return: 最佳匹配结果，无匹配时返回 None
        """
        results = self.query(image, k=1, threshold=threshold)
        return results[0] if results else None

    def match_all(self, image: MatLike, threshold: float = 10) -> list[DatabaseQueryResult]:
        """搜索所有匹配的图像（兼容旧接口）。

        :param image: 查询图像，BGR 格式
        :param threshold: 距离阈值
        :return: 按距离升序排列的结果列表
        """
        return self.query(image, k=len(self), threshold=threshold)


if __name__ == '__main__':
    from kotonebot.backend.core import cv2_imread
    from .datasource import FileDataSource
    from kaa.image_db.descriptors.hist import HistDescriptor
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    imgs_path = r'E:\GithubRepos\KotonesAutoAssistant.worktrees\dev\kotonebot\tasks\resources\idol_cards'
    needle_path = r'D:\05.png'
    db = ImageDatabase(
        FileDataSource(imgs_path),
        r'D:\_idols_db',
        HistDescriptor(8),
        name='idols'
    )
    if not db.is_built:
        db.build()
    needle = cv2_imread(needle_path)
    result = db.query(needle, k=3)
    print(result)
