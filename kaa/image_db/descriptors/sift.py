import cv2
import numpy as np
from cv2.typing import MatLike

from .base import MetricType


class SiftDescriptor:
    """SIFT 局部特征描述子。

    使用 OpenCV SIFT 检测关键点并计算 128 维局部描述子。
    每张图像产出 N 个描述子（N 取决于图像内容）。
    """

    metric_type = MetricType.L2
    dimension = 128

    def __init__(self, nfeatures: int = 0, nOctaveLayers: int = 3,
                 contrastThreshold: float = 0.04, edgeThreshold: float = 10,
                 sigma: float = 1.6):
        """
        :param nfeatures: 保留的关键点数量上限（0 表示不限制）
        :param nOctaveLayers: 每组金字塔的层数
        :param contrastThreshold: 对比度阈值，过滤弱关键点
        :param edgeThreshold: 边缘阈值，过滤边缘响应
        :param sigma: 高斯滤波 sigma
        """
        self.sift = cv2.SIFT_create(  # type: ignore[attr-defined]
            nfeatures=nfeatures,
            nOctaveLayers=nOctaveLayers,
            contrastThreshold=contrastThreshold,
            edgeThreshold=edgeThreshold,
            sigma=sigma
        )

    def compute(self, image: MatLike) -> np.ndarray:
        _, descriptors = self.sift.detectAndCompute(image, None)
        if descriptors is None:
            return np.empty((0, 128), dtype=np.float32)
        return descriptors.astype(np.float32)
