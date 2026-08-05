import pickle
import numpy as np

from ..descriptors.base import MetricType


class FlatIndex:
    """扁平索引（线性扫描）。

    直接存储所有向量，搜索时逐一计算距离。适用于小规模数据集。
    支持 CHI2 和 L2 两种距离度量。
    """

    def __init__(self, dimension: int, metric: MetricType):
        """
        :param dimension: 向量维度
        :param metric: 距离度量类型
        """
        self.dimension = dimension
        self.metric = metric
        self._vectors: list[np.ndarray] = []
        self._ids: list[np.ndarray] = []

    @property
    def is_trained(self):
        return True

    def train(self, vectors: np.ndarray):
        pass

    def add(self, vectors: np.ndarray, ids: np.ndarray):
        """添加向量到索引。

        :param vectors: 向量，shape (M, d)
        :param ids: 向量对应的整数标签，shape (M,)
        """
        self._vectors.append(vectors)
        self._ids.append(ids)

    def search(self, queries: np.ndarray, k: int = 1) -> tuple[np.ndarray, np.ndarray]:
        """线性扫描搜索。

        :param queries: 查询向量，shape (Q, d)
        :param k: 返回的 top-k 数量
        :return: (distances, labels)，均为 shape (Q, k)
        """
        nq = len(queries)
        if not self._vectors:
            return np.full((nq, k), np.inf), np.full((nq, k), -1, dtype=np.int64)

        all_vec = np.vstack(self._vectors)
        all_ids = np.concatenate(self._ids)
        n_total = len(all_vec)

        if k > n_total:
            k = n_total

        dists = np.zeros((nq, n_total), dtype=np.float64)
        for i in range(nq):
            q = queries[i]
            if self.metric == MetricType.CHI2:
                diff = all_vec - q.reshape(1, -1)
                sum_v = all_vec + q.reshape(1, -1) + 1e-10
                dists[i] = 0.5 * np.sum(diff ** 2 / sum_v, axis=1)
            else:
                diff = all_vec - q.reshape(1, -1)
                dists[i] = np.sum(diff ** 2, axis=1)

        topk_indices = np.argpartition(dists, k - 1, axis=1)[:, :k]
        topk_dists = np.take_along_axis(dists, topk_indices, axis=1)
        topk_ids = all_ids[topk_indices]

        sort_idx = np.argsort(topk_dists, axis=1)
        topk_dists = np.take_along_axis(topk_dists, sort_idx, axis=1)
        topk_ids = np.take_along_axis(topk_ids, sort_idx, axis=1)

        return topk_dists.astype(np.float64), topk_ids.astype(np.int64)

    def save(self, path: str):
        """将索引保存到文件。

        :param path: 保存路径
        """
        with open(path, 'wb') as f:
            pickle.dump({
                'dimension': self.dimension,
                'metric': self.metric.value,
                'vectors': [v for v in self._vectors],
                'ids': [idarr for idarr in self._ids],
            }, f)

    @classmethod
    def load(cls, path: str, dimension: int = 0, metric: MetricType = MetricType.L2):
        """从文件加载索引。

        :param path: 索引文件路径
        :param dimension: 向量维度（被文件中存储的值覆盖）
        :param metric: 距离度量类型（被文件中存储的值覆盖）
        :return: 加载后的 FlatIndex
        """
        with open(path, 'rb') as f:
            data = pickle.load(f)
        obj = cls(data['dimension'], MetricType(data['metric']))
        obj._vectors = data['vectors']
        obj._ids = data['ids']
        return obj
