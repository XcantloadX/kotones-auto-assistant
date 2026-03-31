import numpy as np
import cv2

from util import BaseTestCase
from kotonebot.backend.color import find, find_all
from kotonebot.primitives import Rect

def _img_rgb_to_bgr(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

def hex2rgb(hex: str) -> tuple[int, int, int]:
    hex = hex.lstrip('#')
    return (int(hex[0:2], 16), int(hex[2:4], 16), int(hex[4:6], 16))

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
            self.assertEqual(find(image, color, threshold=1), expected, f'{path} {color}')
        # 错误格式
        with self.assertRaises(ValueError):
            find('tests/images/acquire_pdorinku.png', '')
            find('tests/images/acquire_pdorinku.png', 'sdasdf')
            find('tests/images/acquire_pdorinku.png', '000000')
            find('tests/images/acquire_pdorinku.png', '#000')
            find('tests/images/acquire_pdorinku.png', 'red')
            find('tests/images/acquire_pdorinku.png', 'red')
            find('tests/images/acquire_pdorinku.png', [1, 2, 3]) # type: ignore
            find('tests/images/acquire_pdorinku.png', tuple()) # type: ignore
            find('tests/images/acquire_pdorinku.png', (0, 0)) # type: ignore
            find('tests/images/acquire_pdorinku.png', (999, 999, -1)) # type: ignore

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
            self.assertEqual(find(image, color, rect=Rect(xywh=rect), threshold=1), expected, f'{path} {color} {rect}')

    def test_find_rgb_with_threshold(self):
        target_color = (252, 61, 74) # RGB
        threshold = 0.9
        colors = [
            '#fc545f',
            '#fc1d2c',
            '#f12735',
            '#fc1d2c'
        ]
        # 纯色图片测试
        for color in colors:
            img = np.full((100, 100, 3), target_color, dtype=np.uint8)
            img = _img_rgb_to_bgr(img)
            self.assertEqual(find(img, color, threshold=threshold), (0, 0), f'color={color}')
        # 随机图片测试
        for color in colors:
            # 生成10x10的随机颜色块
            img = np.zeros((100, 100, 3), dtype=np.uint8)
            for i in range(0, 100, 10):
                for j in range(0, 100, 10):
                    random_color = np.random.randint(0, 256, 3)
                    random_color[0] //= 3
                    img[i:i+10, j:j+10] = random_color
            
            # 随机选择一个10x10的块放置目标颜色
            x = np.random.randint(0, 10) * 10
            y = np.random.randint(0, 10) * 10
            img[y:y+10, x:x+10] = hex2rgb(color)
            
            img = _img_rgb_to_bgr(img)
            self.assertEqual(find(img, target_color, threshold=threshold), (x, y), f'color={color}')

    def test_hsv_web2cv(self):
        test_cases = [
            # (h, s, v) Web format -> (h, s, v) OpenCV format
            ((0, 0, 0), (0, 0, 0)),
            ((360, 100, 100), (180, 255, 255)),
            ((180, 50, 50), (90, 128, 128)),
            ((240, 75, 80), (120, 191, 204)),
        ]
        from kotonebot.backend.color import hsv_web2cv
        for input_hsv, expected in test_cases:
            self.assertEqual(hsv_web2cv(*input_hsv), expected, f'input={input_hsv}')

    def test_hsv_cv2web(self):
        test_cases = [
            # (h, s, v) OpenCV -> (h, s, v) Web format
            ((0, 0, 0), (0, 0, 0)),
            ((180, 255, 255), (360, 100, 100)),
            ((90, 128, 128), (180, 50, 50)),
            ((120, 191, 204), (240, 75, 80)),
        ]
        from kotonebot.backend.color import hsv_cv2web
        for input_hsv, expected in test_cases:
            self.assertEqual(hsv_cv2web(*input_hsv), expected, f'input={input_hsv}')

    def test_rgb_to_hsv(self):
        test_cases = [
            # RGB -> HSV (web format)
            ('#000000', (0, 0, 0)),
            ('#FFFFFF', (0, 0, 100)),
            ('#FF0000', (0, 100, 100)),
            ('#00FF00', (120, 100, 100)),
            ('#0000FF', (240, 100, 100)),
            # RGB tuple -> HSV
            ((255, 0, 0), (0, 100, 100)),
            ((0, 255, 0), (120, 100, 100)),
            ((0, 0, 255), (240, 100, 100)),
            ((128, 128, 128), (0, 0, 50)),
        ]
        from kotonebot.backend.color import rgb_to_hsv
        for input_rgb, expected in test_cases:
            self.assertEqual(rgb_to_hsv(input_rgb), expected, f'input={input_rgb}')

    def test_hsv_to_rgb(self):
        test_cases = [
            # HSV (Web format) -> RGB
            ((0, 0, 0), (0, 0, 0)),
            ((0, 100, 100), (255, 0, 0)),
            ((120, 100, 100), (0, 255, 0)),
            ((240, 100, 100), (0, 0, 255)),
            ((60, 100, 100), (255, 255, 0)),
            ((180, 100, 100), (0, 255, 255)),
        ]
        from kotonebot.backend.color import hsv_to_rgb
        for input_hsv, expected in test_cases:
            self.assertEqual(hsv_to_rgb(input_hsv), expected, f'input={input_hsv}')

    def test_find_rgb_many(self):
        # 测试纯色图片
        def create_solid_image(color: tuple[int, int, int], size=(100, 100)) -> np.ndarray:
            img = np.full((*size, 3), color, dtype=np.uint8)
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # 测试数据
        test_cases = [
            # (目标颜色, 图片, 预期结果数量)
            ('#FF0000', create_solid_image((255, 0, 0)), 100*100),  # 纯红色
            ('#00FF00', create_solid_image((0, 255, 0)), 100*100),  # 纯绿色
            ('#0000FF', create_solid_image((0, 0, 255)), 100*100),  # 纯蓝色
            ('#FFFFFF', create_solid_image((255, 255, 255)), 100*100),  # 纯白色
            ('#000000', create_solid_image((0, 0, 0)), 100*100),  # 纯黑色
        ]

        for color, img, expected_count in test_cases:
            results = find_all(img, color, threshold=1.0, filter_method='point')
            self.assertEqual(len(results), expected_count, f'color={color}')

        # 测试不同阈值
        img = create_solid_image((128, 128, 128))
        results = find_all(img, '#808080', threshold=0.9, filter_method='point')
        self.assertEqual(len(results), 100*100)
        results = find_all(img, '#808080', threshold=0.99, filter_method='point')
        self.assertEqual(len(results), 100*100)
        results = find_all(img, '#808080', threshold=1.0, filter_method='point')
        self.assertEqual(len(results), 100*100)

        # 测试不同过滤方法
        img = cv2.imread(r'tests\images\scenes\mission.png')
        # 点过滤
        results_point = find_all(img, '#ff1249', threshold=0.95, filter_method='point')
        # 轮廓过滤
        results_contour = find_all(img, '#ff1249', threshold=0.95, filter_method='contour')
        self.assertEqual(len(results_contour), 2)
        self.assertGreater(len(results_point), len(results_contour))

        # 测试最大结果数量限制
        results = find_all(img, '#ffffff', threshold=0.95, max_results=10)
        self.assertEqual(len(results), 10)

        # 测试矩形区域搜索
        rect = Rect(28, 934, 170, 170)
        results = find_all(img, '#ff1249', rect=rect, threshold=0.95)
        for result in results:
            x, y = result.position
            self.assertTrue(rect.x1 <= x < rect.x2)
            self.assertTrue(rect.y1 <= y < rect.y2)

        # 测试无效输入
        # with self.assertRaises(ValueError):
        #     find_rgb_many('invalid_path', '#000000')
        #     find_rgb_many(img, 'invalid_color')
        #     find_rgb_many(img, '#000000', rect=(0, 0, -1, -1))
        #     find_rgb_many(img, '#000000', threshold=1.1)
        #     find_rgb_many(img, '#000000', threshold=-0.1)
        #     find_rgb_many(img, '#000000', max_results=-1)

