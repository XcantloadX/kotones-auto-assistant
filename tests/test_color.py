import cv2

from util import BaseTestCase
from kotonebot.backend.color import find_rgb

class TestColor(BaseTestCase):
    def test_find_rgb(self):
        test_cases = [
            # #RRGGBB
            ('#80a9f1', (621, 96), 'tests/images/acquire_pdorinku.png'),
            ('#fb4142', (28, 47), 'tests/images/pdorinku.png'),
            ('#00ff00', None, 'tests/images/pdorinku_mask.png'),
            # (r, g, b)
            ((128, 169, 241), (621, 96), 'tests/images/acquire_pdorinku.png'),
            ((251, 65, 66), (28, 47), 'tests/images/pdorinku.png'),
            ((0, 255, 0), None, 'tests/images/pdorinku_mask.png'),
        ]
        for color, expected, path in test_cases:
            image = cv2.imread(path)
            self.assertEqual(find_rgb(image, color), expected, f'{path} {color}')
        # 错误格式
        with self.assertRaises(ValueError):
            find_rgb('tests/images/acquire_pdorinku.png', '')
            find_rgb('tests/images/acquire_pdorinku.png', 'sdasdf')
            find_rgb('tests/images/acquire_pdorinku.png', '000000')
            find_rgb('tests/images/acquire_pdorinku.png', '#000')
            find_rgb('tests/images/acquire_pdorinku.png', 'red')
            find_rgb('tests/images/acquire_pdorinku.png', 'red')
            find_rgb('tests/images/acquire_pdorinku.png', [1, 2, 3]) # type: ignore
            find_rgb('tests/images/acquire_pdorinku.png', tuple()) # type: ignore
            find_rgb('tests/images/acquire_pdorinku.png', (0, 0)) # type: ignore
            find_rgb('tests/images/acquire_pdorinku.png', (999, 999, -1)) # type: ignore

    def test_find_rgb_with_rect(self):
        test_cases = [
            # #RRGGBB
            ('#ffffff', (272, 685), (272, 685, 10, 10), 'tests/images/acquire_pdorinku.png'),
            ('#dafcff', (171, 832), (154, 817, 137, 137), 'tests/images/acquire_pdorinku.png'),
            ('#000000', None, (154, 817, 137, 137), 'tests/images/acquire_pdorinku.png'),
            # (r, g, b)
            ((255, 255, 255), (272, 685), (272, 685, 10, 10), 'tests/images/acquire_pdorinku.png'),
            ((218, 252, 255), (171, 832), (154, 817, 137, 137), 'tests/images/acquire_pdorinku.png'),
            ((0, 0, 0), None, (154, 817, 137, 137), 'tests/images/acquire_pdorinku.png'),
        ]
        for color, expected, rect, path in test_cases:
            image = cv2.imread(path)
            self.assertEqual(find_rgb(image, color, rect=rect), expected, f'{path} {color} {rect}')
