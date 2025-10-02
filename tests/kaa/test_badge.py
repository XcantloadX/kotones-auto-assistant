from unittest import TestCase

from kotonebot.primitives import Rect
from kaa.game_ui.badge import match

def rect_from_center(x: int, y: int) -> Rect:
    w, h = 20, 20
    return Rect(x - w // 2, y - h // 2, w, h)

class TestBadge(TestCase):
    def test_match(self):
        # 测试数据
        # https://www.desmos.com/calculator/dsynum9p4i
        objects = [
            rect_from_center(125, 125),
            rect_from_center(230, 230),
            rect_from_center(320, 120),
        ]
        badges = [
            # 左上角徽章
            rect_from_center(90, 160), # 对应 objects[0] 的左上
            # 右下角徽章
            rect_from_center(260, 200), # 对应 objects[1] 的右下
            # 右上角徽章
            rect_from_center(340, 130), # 对应 objects[2] 的右上
            # 不匹配任何对象的徽章
            rect_from_center(410, 410),
        ]
        
        # 测试左上角匹配
        results = match(objects, badges, 'lt', 50)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].object, objects[0])
        self.assertEqual(results[0].badge, badges[0])
        self.assertEqual(results[1].object, objects[1])
        self.assertIsNone(results[1].badge)
        self.assertEqual(results[2].object, objects[2])
        self.assertIsNone(results[2].badge)
        
        # 测试右下角匹配
        results = match(objects, badges, 'rb', 50)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].object, objects[0])
        self.assertIsNone(results[0].badge)
        self.assertEqual(results[1].object, objects[1])
        self.assertEqual(results[1].badge, badges[1])
        self.assertEqual(results[2].object, objects[2])
        self.assertIsNone(results[2].badge)
        
        # 测试右上角匹配
        results = match(objects, badges, 'rt', 50)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].object, objects[0])
        self.assertIsNone(results[0].badge)
        self.assertEqual(results[1].object, objects[1])
        self.assertIsNone(results[1].badge)
        self.assertEqual(results[2].object, objects[2])
        self.assertEqual(results[2].badge, badges[2])
        
        # 测试没有匹配的情况
        results = match(objects, [], 'lt', 50)
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIsNone(result.badge)
        
        # 测试空对象列表
        results = match([], badges, 'lt', 50)
        self.assertEqual(len(results), 0)
        
    # 测试当多个徽章符合条件时，选择最近的一个
    def test_match_with_multiple_badges(self):
        # 测试数据
        # https://www.desmos.com/calculator/pytdqaju4w
        objects = [rect_from_center(125, 125)]
        badges = [
            rect_from_center(90, 90),
            rect_from_center(80, 80),
            rect_from_center(70, 70),
        ]
        
        results = match(objects, badges, 'lb')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].object, objects[0])
        self.assertEqual(results[0].badge, badges[0])
