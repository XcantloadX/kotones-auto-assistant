from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from numpy import ndarray

from ..descriptors.base import MetricType


class Index(Protocol):
    """向量索引协议。

    所有索引实现（FlatIndex、FaissIndex）必须实现此协议。
    """

    @property
    def is_trained(self) -> bool:
        """索引是否已完成训练。"""
        raise NotImplementedError

    def train(self, vectors: 'ndarray') -> None:
        """训练索引（IVF 等需聚类；FlatIndex 为空操作）。

        :param vectors: 训练向量，shape (N, d)
        """
        raise NotImplementedError

    def add(self, vectors: 'ndarray', ids: 'ndarray') -> None:
        """向索引中添加向量。

        :param vectors: 向量，shape (M, d)
        :param ids: 向量对应的整数标签，shape (M,)
        """
        raise NotImplementedError

    def search(self, queries: 'ndarray', k: int = 1) -> tuple['ndarray', 'ndarray']:
        """搜索与查询向量最相似的 k 个向量。

        :param queries: 查询向量，shape (Q, d)
        :param k: 返回的 top-k 数量
        :return: (distances, labels)，均为 shape (Q, k)
        """
        raise NotImplementedError

    def save(self, path: str) -> None:
        """将索引保存到文件。

        :param path: 保存路径
        """
        raise NotImplementedError

    @classmethod
    def load(cls, path: str, dimension: int, metric: MetricType) -> 'Index':
        """从文件加载索引。

        :param path: 索引文件路径
        :param dimension: 向量维度
        :param metric: 距离度量类型
        :return: 加载后的索引对象
        """
        raise NotImplementedError
