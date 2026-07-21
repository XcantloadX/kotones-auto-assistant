import os
from typing import Any, Protocol, Iterator

from kotonebot.backend.core import cv2_imread


class DataSource(Protocol):
    """图像数据源协议。

    迭代时产生 (key, image) 二元组，
    其中 key 为图片标识（如文件名），image 为 BGR 格式的图像。
    """

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        ...


class FileDataSource(DataSource):
    """文件系统图像数据源。

    遍历指定目录中的所有图像文件，以文件名为 key，图像数据为 value。
    """

    def __init__(self, folder_path: str, keep_ext: bool = True):
        """
        :param folder_path: 图像文件夹路径
        :param keep_ext: 是否保留文件名中的扩展名作为 key
        """
        self.path = os.path.abspath(folder_path)
        self.keep_ext = keep_ext

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for file in os.listdir(self.path):
            if not self.keep_ext:
                file = os.path.splitext(file)[0]
            yield file, cv2_imread(os.path.join(self.path, file))
