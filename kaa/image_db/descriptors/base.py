from typing import Protocol, TYPE_CHECKING, runtime_checkable
from enum import Enum

if TYPE_CHECKING:
    from cv2.typing import MatLike
    from numpy import ndarray


class MetricType(Enum):
    """距离度量类型。"""
    L2 = 'l2'
    """欧氏距离"""
    CHI2 = 'chi2'
    """卡方距离"""
    COSINE = 'cosine'
    """余弦距离"""


@runtime_checkable
class BaseDescriptor(Protocol):
    """图像描述子协议。

    所有描述子必须实现此协议。
    """

    metric_type: MetricType
    """描述子使用的距离度量类型"""

    @property
    def dimension(self) -> int:
        """描述子向量的维度"""
        raise NotImplementedError

    def compute(self, image: 'MatLike') -> 'ndarray':
        """计算输入图像的描述子特征向量。

        :param image: 输入图像，BGR 格式
        :return: 特征向量，shape 为 (N, d)，其中 N 为向量个数，d 为向量维度
        """
        ...
