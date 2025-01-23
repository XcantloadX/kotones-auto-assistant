import re
import time
import unicodedata
from os import PathLike
from typing import TYPE_CHECKING, Callable, NamedTuple, overload

from .util import Rect, grayscaled, res_path
from .debug import result as debug_result, debug

import cv2
from cv2.typing import MatLike
from rapidocr_onnxruntime import RapidOCR

_engine_jp = RapidOCR(
    rec_model_path=res_path('res/models/japan_PP-OCRv3_rec_infer.onnx'),
    use_det=True,
    use_cls=False,
    use_rec=True,
)
_engine_en = RapidOCR(
    rec_model_path=res_path('res/models/en_PP-OCRv3_rec_infer.onnx'),
    use_det=True,
    use_cls=False,
    use_rec=True,
)

StringMatchFunction = Callable[[str], bool]

class OcrResult(NamedTuple):
    text: str
    rect: Rect
    confidence: float

class TextNotFoundError(Exception):
    def __init__(self, pattern: str | re.Pattern | StringMatchFunction, image: 'MatLike'):
        self.pattern = pattern
        self.image = image
        if isinstance(pattern, (str, re.Pattern)):
            super().__init__(f"Expected text not found: {pattern}")
        else:
            super().__init__(f"Expected text not found: {pattern.__name__}")


def _is_match(text: str, pattern: re.Pattern | str | StringMatchFunction) -> bool:
    if isinstance(pattern, re.Pattern):
        return pattern.match(text) is not None
    elif callable(pattern):
        return pattern(text)
    else:
        return text == pattern

# https://stackoverflow.com/questions/46335488/how-to-efficiently-find-the-bounding-box-of-a-collection-of-points
def _bounding_box(points):
    x_coordinates, y_coordinates = zip(*points)

    return [(min(x_coordinates), min(y_coordinates)), (max(x_coordinates), max(y_coordinates))]

def bounding_box(points: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    """
    计算点集的外接矩形

    :param points: 点集
    :return: 外接矩形的左上角坐标和宽高
    """
    topleft, bottomright = _bounding_box(points)
    return (topleft[0], topleft[1], bottomright[0] - topleft[0], bottomright[1] - topleft[1])

def _draw_result(image: 'MatLike', result: list[OcrResult]) -> 'MatLike':
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    
    # 转换为PIL图像
    result_image = cv2.cvtColor(image.copy(), cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(result_image)
    draw = ImageDraw.Draw(pil_image, 'RGBA')
    
    # 加载字体
    try:
        font = ImageFont.truetype(res_path('res/fonts/SourceHanSansHW-Regular.otf'), 16)
    except:
        font = ImageFont.load_default()
    
    for r in result:
        # 画矩形框
        draw.rectangle(
            [r.rect[0], r.rect[1], r.rect[0] + r.rect[2], r.rect[1] + r.rect[3]], 
            outline=(255, 0, 0), 
            width=2
        )
        
        # 获取文本大小
        text = r.text + f" ({r.confidence:.2f})"  # 添加置信度显示
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # 计算文本位置
        text_x = r.rect[0]
        text_y = r.rect[1] - text_height - 5 if r.rect[1] > text_height + 5 else r.rect[1] + r.rect[3] + 5
        
        # 添加padding
        padding = 4
        bg_rect = [
            text_x - padding,
            text_y - padding,
            text_x + text_width + padding,
            text_y + text_height + padding
        ]
        
        # 画半透明背景
        draw.rectangle(
            bg_rect,
            fill=(0, 0, 0, 128)
        )
        
        # 画文字
        draw.text(
            (text_x, text_y),
            text,
            font=font,
            fill=(255, 255, 255)
        )
    
    # 转回OpenCV格式
    result_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    return result_image

class Ocr:
    def __init__(self, engine: RapidOCR):
        self.__engine = engine


    # TODO: 考虑缓存 OCR 结果，避免重复调用。
    def ocr(self, img: 'MatLike') -> list[OcrResult]:
        """
        OCR 一个 cv2 的图像。注意识别结果中的**全角字符会被转换为半角字符**。

        :return: 所有识别结果
        """
        img_content = grayscaled(img)
        result, elapse = self.__engine(img_content)
        if result is None:
            return []
        ret = [OcrResult(
            text=unicodedata.normalize('NFKC', r[1]).replace('ą', 'a'), # HACK: 识别结果中包含奇怪的符号，暂时替换掉
            # r[0] = [左上, 右上, 右下, 左下]
            # 这里有个坑，返回的点不一定是矩形，只能保证是四边形
            # 所以这里需要计算出四个点的外接矩形
            rect=tuple(int(x) for x in bounding_box(r[0])), # type: ignore
            confidence=r[2] # type: ignore
        ) for r in result] # type: ignore
        if debug.enabled:
            result_image = _draw_result(img, ret)
            debug_result(
                'ocr',
                [result_image, img],
                f"result: \n" + \
                "<table class='result-table'><tr><th>Text</th><th>Confidence</th></tr>" + \
                "\n".join([f"<tr><td>{r.text}</td><td>{r.confidence:.2f}</td></tr>" for r in ret]) + \
                "</table>"
            )
        return ret

    def find(self, img: 'MatLike', text: str | re.Pattern | StringMatchFunction) -> OcrResult | None:
        """
        寻找指定文本
        
        :return: 找到的文本，如果未找到则返回 None
        """
        for result in self.ocr(img):
            if _is_match(result.text, text):
                return result
        return None
    
    def expect(self, img: 'MatLike', text: str | re.Pattern | StringMatchFunction) -> OcrResult:
        """
        寻找指定文本，如果未找到则抛出异常
        """
        ret = self.find(img, text)
        if ret is None:
            raise TextNotFoundError(text, img)
        return ret



jp = Ocr(_engine_jp)
"""日语 OCR 引擎。"""
en = Ocr(_engine_en)
"""英语 OCR 引擎。"""

if __name__ == '__main__':
    from pprint import pprint as print
    import cv2
    img_path = 'test_images/acquire_pdorinku.png'
    img = cv2.imread(img_path)
    result1 = jp.ocr(img)
    print(result1)