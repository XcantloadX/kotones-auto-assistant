import unittest

from kotonebot.backend.ocr import bounding_box

class TestOcr(unittest.TestCase):
    def test_bounding_box(self):
        # 测试基本情况
        # 矩形
        points = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert bounding_box(points) == (0, 0, 10, 10)
        # 三角形
        points = [(0, 0), (10, 0), (5, 10)]
        assert bounding_box(points) == (0, 0, 10, 10)
        # 不规则四边形
        points = [(0, 0), (5, 2), (8, 6), (2, 8)]
        assert bounding_box(points) == (0, 0, 8, 8)

        # 测试单点
        points = [(5, 5)]
        assert bounding_box(points) == (5, 5, 0, 0)

        # 测试负坐标
        points = [(-1, -1), (2, 3)]
        assert bounding_box(points) == (-1, -1, 3, 4)

        # 测试零宽度矩形
        points = [(0, 0), (0, 10)]
        assert bounding_box(points) == (0, 0, 0, 10)

        # 测试零高度矩形
        points = [(0, 0), (10, 0)]
        assert bounding_box(points) == (0, 0, 10, 0)

        # 测试大数值
        points = [(1000000, 1000000), (2000000, 2000000)]
        assert bounding_box(points) == (1000000, 1000000, 1000000, 1000000)

        # 测试点的无序排列
        points = [(10, 0), (0, 10), (0, 0), (10, 10)]
        assert bounding_box(points) == (0, 0, 10, 10)

        # 测试重复点
        points = [(5, 5), (5, 5), (5, 5)]
        assert bounding_box(points) == (5, 5, 0, 0)
