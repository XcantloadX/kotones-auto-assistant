import unittest

from kotonebot import _c
from kotonebot.tasks.actions.in_purodyuusu import skill_card_count
from util import MockDevice


class TestActionInProduce(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.d = MockDevice()
        _c.inject_device(cls.d)

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