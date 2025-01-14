import cv2

from util import BaseTestCase
from kotonebot.backend.image import *

class TestImage(BaseTestCase):
    def test_hist_match(self):
        add_black = cv2.imread('tests/images/template_match/add.png')
        add_gray = cv2.imread('tests/images/template_match/add_disabled.png')
        self.assertFalse(hist_match(add_black, add_gray))
        self.assertTrue(hist_match(add_black, add_black))
        self.assertTrue(hist_match(add_gray, add_gray))

        with self.assertRaises(ValueError):
            hist_match(add_black, add_gray, rect=(0, 0, 1, 1))
