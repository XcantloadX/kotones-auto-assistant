import re
import time
import unicodedata
from os import PathLike
from typing import TYPE_CHECKING, Callable, NamedTuple, overload

from kotonebot.backend.util import Rect

if TYPE_CHECKING:
    from cv2.typing import MatLike
from rapidocr_onnxruntime import RapidOCR

_engine_jp = RapidOCR(
    rec_model_path=r'res\models\japan_PP-OCRv3_rec_infer.onnx',
    use_det=True,
    use_cls=False,
    use_rec=True,
)
_engine_en = RapidOCR(
    rec_model_path=r'res\models\en_PP-OCRv3_rec_infer.onnx',
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

class Ocr:
    def __init__(self, engine: RapidOCR):
        self.__engine = engine


    # TODO: 考虑缓存 OCR 结果，避免重复调用。
    def ocr(self, img: 'MatLike') -> list[OcrResult]:
        """
        OCR 一个 cv2 的图像。注意识别结果中的**全角字符会被转换为半角字符**。

        :return: 所有识别结果
        """
        img_content = img
        result, elapse = self.__engine(img_content)
        if result is None:
            return []
        return [OcrResult(
            text=unicodedata.normalize('NFKC', r[1]).replace('ą', 'a'), # HACK: 识别结果中包含奇怪的符号，暂时替换掉
            rect=(
                int(r[0][0][0]),  # 左上x
                int(r[0][0][1]),  # 左上y
                int(r[0][2][0] - r[0][0][0]),  # 宽度 = 右下x - 左上x # type: ignore
                int(r[0][2][1] - r[0][0][1]),  # 高度 = 右下y - 左上y # type: ignore
            ),
            confidence=r[2] # type: ignore
        ) for r in result] # type: ignore

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