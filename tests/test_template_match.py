import unittest

import cv2

from kotonebot.backend.image import template_match, find_crop

def save(image, name: str):
    import os
    if not os.path.exists('./tests/output_images'):
        os.makedirs('./tests/output_images')
    cv2.imwrite(f'./tests/output_images/{name}.png', image)


class TestTemplateMatch(unittest.TestCase):
    def setUp(self):
        self.template = cv2.imread('tests/images/pdorinku.png')
        self.mask = cv2.imread('tests/images/pdorinku_mask.png')
        self.image = cv2.imread('tests/images/acquire_pdorinku.png')

    def __assert_pos(self, result, x, y, offset=10):
        self.assertGreater(result.position[0], x - offset)
        self.assertGreater(result.position[1], y - offset)
        self.assertLess(result.position[0], x + offset)
        self.assertLess(result.position[1], y + offset)

    def test_basic(self):
        result = template_match(self.template, self.image)
        # 圈出结果并保存
        cv2.rectangle(self.image, result[0].rect, (0, 0, 255), 2)
        save(self.image, 'TestTemplateMatch.basic')

        self.assertGreater(len(result), 0)
        self.assertGreater(result[0].score, 0.9)
        # 坐标位于 (167, 829) 附近
        self.__assert_pos(result[0], 167, 829)

    def test_masked(self):
        result = template_match(
            self.template,
            self.image,
            mask=self.mask,
            max_results=3,
            remove_duplicate=False,
            threshold=0.999,
        )
        # 圈出结果并保存
        for i, r in enumerate(result):
            cv2.rectangle(self.image, r.rect, (0, 0, 255), 2)
        save(self.image, 'TestTemplateMatch.masked')

        self.assertEqual(len(result), 3)
        self.assertGreater(result[0].score, 0.9)
        self.assertGreater(result[1].score, 0.9)
        self.assertGreater(result[2].score, 0.9)
        # 坐标位于 (167, 829) 附近
        self.__assert_pos(result[0], 167, 829)
        self.__assert_pos(result[1], 306, 829)
        self.__assert_pos(result[2], 444, 829)

    def test_crop(self):
        result = find_crop(
            self.image,
            self.template,
            self.mask,
            threshold=0.999,
        )
        for i, r in enumerate(result):
            cv2.imwrite(f'./tests/output_images/TestTemplateMatch.crop_{i}.png', r.image)

        self.assertEqual(len(result), 3)
