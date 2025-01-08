import unittest

from kotonebot import _c
from kotonebot.tasks.actions.in_purodyuusu import skill_card_count, click_recommended_card
from util import MockDevice


class TestActionInProduce(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.d = MockDevice()
        _c.inject_device(cls.d)

    def test_click_recommended_card(self):
        # 文件命名格式：卡片数量_预期返回值_编号.png
        self.d.screenshot_path = 'tests/images/produce/recommended_card_3_-1_0.png'
        self.assertEqual(click_recommended_card(timeout=1), -1)
        self.d.screenshot_path = 'tests/images/produce/recommended_card_4_3_0.png'
        self.assertEqual(click_recommended_card(timeout=1), 0)

    def test_current_skill_card_count(self):
        cards_1 = 'tests/images/produce/in_produce_cards_1.png'
        cards_2 = 'tests/images/produce/in_produce_cards_2.png'
        cards_3 = 'tests/images/produce/in_produce_cards_3.png'
        cards_4 = 'tests/images/produce/in_produce_cards_4.png'
        cards_4_1 = 'tests/images/produce/in_produce_cards_4_1.png'

        self.d.screenshot_path = cards_1
        self.assertEqual(skill_card_count(), 1)
        self.d.screenshot_path = cards_2
        self.assertEqual(skill_card_count(), 2)
        self.d.screenshot_path = cards_3
        self.assertEqual(skill_card_count(), 3)
        self.d.screenshot_path = cards_4
        self.assertEqual(skill_card_count(), 4)
        self.d.screenshot_path = cards_4_1
        self.assertEqual(skill_card_count(), 4)