import cv2
import numpy as np
from cv2.typing import MatLike

from .base import MetricType


class HistDescriptor:
    """HSV 直方图全局描述子。

    将图像转为 HSV 空间，均分为 3x3 共 9 个区域，
    分别计算每个区域的 HSV 三通道直方图并拼接。
    """

    metric_type = MetricType.CHI2

    def __init__(self, bin_count: int):
        """
        :param bin_count: 每个通道的直方图 bin 数量
        """
        self.bin_count = bin_count

    @property
    def dimension(self):
        return (self.bin_count ** 3) * 9

    def compute(self, image: MatLike):
        img = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        masks = []
        height, width = img.shape[:2]
        for i in range(3):
            for j in range(3):
                start_row, start_col = i * height // 3, j * width // 3
                end_row, end_col = (i + 1) * height // 3, (j + 1) * width // 3
                mask = np.zeros(img.shape[:2], dtype=np.uint8)
                mask[start_row:end_row, start_col:end_col] = 255
                masks.append(mask)
        features = np.array([])
        for mask in masks:
            hist = cv2.calcHist(
                [img],
                [0, 1, 2],
                mask,
                [self.bin_count, self.bin_count, self.bin_count],
                [0, 180, 0, 256, 0, 256]
            )
            hist = cv2.normalize(hist, hist)
            features = np.append(features, hist.flatten())
        return features.reshape(1, -1)

    def __call__(self, image: MatLike):
        return self.compute(image)


if __name__ == '__main__':
    from kotonebot.backend.core import cv2_imread
    d = HistDescriptor(8)
    img = cv2_imread(r'E:\GithubRepos\KotonesAutoAssistant.worktrees\dev\kotonebot\tasks\resources\idol_cards\i_card-amao-2-000_1.png')
    print(d(img))
    cv2.waitKey(0)
