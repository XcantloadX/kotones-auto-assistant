from typing import cast

import cv2
from cv2.typing import MatLike
from numpy import ndarray

from .base import MetricType


class HogDescriptor:
    """HOG 全局描述子。

    使用 OpenCV HOGDescriptor 提取方向梯度直方图特征。
    默认参数：窗口 64x128，块 16x16，步长 8x8，细胞 8x8，9 个方向。
    """

    metric_type = MetricType.L2

    def __init__(self, size=(64, 128)):
        """
        :param size: 调整图像的目标尺寸 (w, h)
        """
        self.size = size
        self.hog = cv2.HOGDescriptor(_winSize=size, _blockSize=(16,16), _blockStride=(8,8), _cellSize=(8,8), _nbins=9)

    @property
    def dimension(self):
        return self.hog.getDescriptorSize()

    def compute(self, image: MatLike):
        img_resized = cv2.resize(image, self.size)
        hist: ndarray = cast(ndarray, self.hog.compute(img_resized))
        return hist.reshape(1, -1)

    def __call__(self, image: MatLike):
        return self.compute(image)
