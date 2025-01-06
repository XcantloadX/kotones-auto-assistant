import unittest

from kotonebot.backend.ocr import jp

import cv2


class TestOcr(unittest.TestCase):
    def setUp(self):
        self.img = cv2.imread('test_images/acquire_pdorinku.png')

    def test_ocr_ocr(self):
        result = jp.ocr(self.img)
        self.assertGreater(len(result), 0)

    def test_ocr_find(self):
        self.assertTrue(jp.find(self.img, '中間まで'))
        self.assertTrue(jp.find(self.img, '受け取るPドリンクを選んでください。'))
        self.assertTrue(jp.find(self.img, '受け取る'))
