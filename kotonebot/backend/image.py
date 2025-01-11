import os
from typing import NamedTuple, Protocol, TypeVar, Sequence, runtime_checkable
from logging import getLogger

from .debug import result, debug, img

import cv2
import numpy as np
from cv2.typing import MatLike, Rect, Point, Size
from skimage.metrics import structural_similarity

logger = getLogger(__name__)

class TemplateNotFoundError(Exception):
    """模板未找到异常。"""
    def __init__(self, image: MatLike, template: MatLike | str):
        self.image = image
        self.template = template
        super().__init__(f"Template not found: {template}")

@runtime_checkable
class ResultProtocol(Protocol):
    @property
    def rect(self) -> Rect:
        """结果区域。左上角坐标和宽高。"""
        ...


class TemplateMatchResult(NamedTuple):
    score: float
    position: Point
    """结果位置。左上角坐标。"""
    size: Size
    """输入模板的大小。宽高。"""

    @property
    def rect(self) -> Rect:
        """结果区域。左上角坐标和宽高。"""
        return (self.position[0], self.position[1], self.size[0], self.size[1])
    
    @property
    def right_bottom(self) -> Point:
        """结果右下角坐标。"""
        return (self.position[0] + self.size[0], self.position[1] + self.size[1])

class MultipleTemplateMatchResult(NamedTuple):
    score: float
    position: Point
    """结果位置。左上角坐标。"""
    size: Size
    """命中模板的大小。宽高。"""
    index: int
    """命中模板在列表中的索引。"""

    @property
    def rect(self) -> Rect:
        """结果区域。左上角坐标和宽高。"""
        return (self.position[0], self.position[1], self.size[0], self.size[1])
    
    @property
    def right_bottom(self) -> Point:
        """结果右下角坐标。"""
        return (self.position[0] + self.size[0], self.position[1] + self.size[1])

class CropResult(NamedTuple):
    score: float
    position: Point
    size: Size
    image: MatLike

    @property
    def rect(self) -> Rect:
        return (self.position[0], self.position[1], self.size[0], self.size[1])

def _unify_image(image: MatLike | str) -> MatLike:
    if isinstance(image, str):
        image = cv2.imread(image)
    return image

T = TypeVar('T')
# TODO: 这个方法太慢了，需要优化
def _remove_duplicate_matches(
        matches: list[T],
        offset: int = 10
    ) -> list[T]:
    result = []
    # 创建一个掩码来标记已匹配区域
    mask = np.zeros((2000, 2000), np.uint8) # 使用足够大的尺寸
    
    # 按匹配分数排序,优先保留分数高的
    sorted_matches = sorted(matches, key=lambda x: x.score, reverse=True) # type: ignore
    
    for match in sorted_matches:
        # 获取匹配区域的中心点
        x = match.position[0] + match.size[0] // 2 # type: ignore
        y = match.position[1] + match.size[1] // 2 # type: ignore
        
        # 检查该区域是否已被标记
        if mask[y, x] != 255:
            # 将整个匹配区域标记为已匹配
            x1, y1 = match.position # type: ignore
            w, h = match.size # type: ignore
            mask[y1:y1+h, x1:x1+w] = 255
            result.append(match)
            
    return result

def _draw_result(image: MatLike, matches: Sequence[ResultProtocol] | ResultProtocol | None) -> MatLike:
    if matches is None:
        return image
    if isinstance(matches, ResultProtocol):
        matches = [matches]
    result_image = image.copy()
    for match in matches:
        cv2.rectangle(result_image, match.rect, (0, 0, 255), 2)
    return result_image

def template_match(
    template: MatLike | str,
    image: MatLike | str,
    mask: MatLike | str | None = None,
    transparent: bool = False,
    threshold: float = 0.8,
    max_results: int = 5,
) -> list[TemplateMatchResult]:
    """
    寻找模板在图像中的位置。

    .. note::
        `mask` 和 `transparent` 参数不能同时使用。

    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param max_results: 最大结果数，默认为 1。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    """
    if isinstance(template, str):
        _template_name = os.path.relpath(template)
    else:
        _template_name = '<opencv Mat>'
    logger.debug(f'match template: {_template_name} threshold: {threshold} max_results: {max_results}')
    # 统一参数
    template = _unify_image(template)
    image = _unify_image(image)
    if mask is not None:
        mask = _unify_image(mask)
        mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)[1]
    
    # 匹配模板
    if mask is not None:
        # https://stackoverflow.com/questions/35642497/python-opencv-cv2-matchtemplate-with-transparency
        # 使用 Mask 时，必须使用 TM_CCORR_NORMED 方法
        result = cv2.matchTemplate(image, template, cv2.TM_CCORR_NORMED, mask=mask)
    else:
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    # 获取所有大于阈值的匹配结果
    locations = list(zip(*np.where(result >= threshold)))
    
    # 转换为 TemplateMatchResult 列表
    matches = []
    for y, x in locations:
        h, w = template.shape[:2]
        score = float(result[y, x])
        matches.append(TemplateMatchResult(score=score, position=(int(x), int(y)), size=(int(w), int(h))))
    
    # 按分数排序并限制结果数量
    matches.sort(key=lambda x: x.score, reverse=True)
    if max_results > 0:
        matches = matches[:max_results]
        
    return matches

def hist_match(
    image: MatLike | str,
    template: MatLike | str,
    rect: Rect,
    threshold: float = 0.8,
) -> bool:
    """
    对输入图像的矩形部分与模板进行颜色直方图匹配。
    将图像分为上中下三个区域，分别计算直方图并比较相似度。

    https://answers.opencv.org/question/59027/template-matching-using-color/

    :param image: 输入图像
    :param template: 模板图像
    :param rect: 待匹配的矩形区域
    :param threshold: 相似度阈值，默认为 0.8
    :return: 是否匹配成功
    """
    # 统一参数
    image = _unify_image(image)
    template = _unify_image(template)

    # 从图像中裁剪出矩形区域
    x, y, w, h = rect
    roi = image[y:y+h, x:x+w]

    # 确保尺寸一致
    if roi.shape != template.shape:
        roi = cv2.resize(roi, (template.shape[1], template.shape[0]))

    # 将图像分为上中下三个区域
    h = roi.shape[0]
    h_band = h // 3
    bands_roi = [
        roi[0:h_band],
        roi[h_band:2*h_band],
        roi[2*h_band:h]
    ]
    bands_template = [
        template[0:h_band],
        template[h_band:2*h_band],
        template[2*h_band:h]
    ]

    # 计算每个区域的直方图
    total_score = 0
    for roi_band, template_band in zip(bands_roi, bands_template):
        hist_roi = cv2.calcHist([roi_band], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist_template = cv2.calcHist([template_band], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        
        # 归一化直方图
        cv2.normalize(hist_roi, hist_roi)
        cv2.normalize(hist_template, hist_template)
        
        # 计算直方图相似度
        score = cv2.compareHist(hist_roi, hist_template, cv2.HISTCMP_CORREL)
        total_score += score

    # 计算平均相似度
    avg_score = total_score / 3
    return avg_score >= threshold

def find_crop(
    image: MatLike | str,
    template: MatLike | str,
    mask: MatLike | str | None = None,
    transparent: bool = False,
    threshold: float = 0.8,
    *,
    colored: bool = False,
) -> list[CropResult]:
    """
    指定一个模板，寻找其出现的所有位置，并裁剪出结果。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param colored: 是否匹配颜色，默认为 False。
    """
    matches = template_match(template, image, mask, transparent, threshold, max_results=-1)
    matches = _remove_duplicate_matches(matches)
    if colored:
        matches = [
            match for match in matches 
            if hist_match(image, template, match.rect, threshold)
        ]
    return [CropResult(
        match.score,
        match.position,
        match.size,
        image[match.rect[1]:match.rect[1]+match.rect[3], match.rect[0]:match.rect[0]+match.rect[2]] # type: ignore
    ) for match in matches]

def find(
    image: MatLike,
    template: MatLike | str,
    mask: MatLike | str | None = None,
    transparent: bool = False,
    threshold: float = 0.8,
    *,
    debug_output: bool = True,
    colored: bool = False,
) -> TemplateMatchResult | None:
    """
    指定一个模板，寻找其出现的第一个位置。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param debug_output: 是否输出调试信息，默认为 True。
    :param colored: 是否匹配颜色，默认为 False。
    """
    matches = template_match(template, image, mask, transparent, threshold, max_results=-1)
    if colored:
        matches = [
            match for match in matches 
            if hist_match(image, template, match.rect, threshold)
        ]
    # 调试输出
    if debug.enabled and debug_output:
        result_image = _draw_result(image, matches)
        result_text = f"template: {img(template)} \n"
        result_text += f"matches: {len(matches)} \n"
        for match in matches:
            result_text += f"score: {match.score} position: {match.position} size: {match.size} \n"
        result(f"image.find", result_image, result_text)
    return matches[0] if len(matches) > 0 else None

def find_many(
    image: MatLike,
    template: MatLike | str,
    mask: MatLike | str | None = None,
    transparent: bool = False,
    threshold: float = 0.8,
    remove_duplicate: bool = True,
    *,
    colored: bool = False,
) -> list[TemplateMatchResult]:
    """
    指定一个模板，寻找所有出现的位置。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    :param colored: 是否匹配颜色，默认为 False。
    """
    results = template_match(template, image, mask, transparent, threshold, max_results=-1)
    if remove_duplicate:
        results = _remove_duplicate_matches(results)
    if colored:
        results = [
            match for match in results 
            if hist_match(image, template, match.rect, threshold)
        ]
    if debug.enabled:
        result_image = _draw_result(image, results)
        result(
            'image.find_many',
            result_image,
            f"template: {img(template)} \n"
            f"matches: {len(results)} \n"
        )
    return results

def find_any(
    image: MatLike,
    templates: list[MatLike | str],
    masks: list[MatLike | str | None] | None = None,
    transparent: bool = False,
    threshold: float = 0.8,
    *,
    colored: bool = False,
) -> MultipleTemplateMatchResult | None:
    """
    指定多个模板，返回第一个匹配到的结果。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param templates: 模板图像列表，可以是图像路径或 cv2.Mat。
    :param masks: 掩码图像列表，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param colored: 是否匹配颜色，默认为 False。
    """
    ret = None
    if masks is None:
        _masks = [None] * len(templates)
    else:
        _masks = masks
    for index, (template, mask) in enumerate(zip(templates, _masks)):
        find_result = find(image, template, mask, transparent, threshold, colored=colored, debug_output=False)
        # 调试输出
        if find_result is not None:
            ret = MultipleTemplateMatchResult(
                score=find_result.score,
                position=find_result.position,
                size=find_result.size,
                index=index
            )
            break
    if debug.enabled:
        msg = (
            "<table class='result-table'>" +
            "<tr><th>Template</th><th>Mask</th><th>Result</th></tr>" +
            "\n".join([
                f"<tr><td>{img(t)}</td><td>{img(m)}</td><td>{'✓' if ret and t == templates[0] else '✗'}</td></tr>"
                for t, m in zip(templates, _masks)
            ]) +
            "</table>\n"
        )
        result(
            'image.find_any',
            _draw_result(image, ret),
            msg
        )
    return ret

def count(
    image: MatLike,
    template: MatLike | str,
    mask: MatLike | str | None = None,
    transparent: bool = False,
    threshold: float = 0.9,
    remove_duplicate: bool = True,
    *,
    colored: bool = False,
) -> int:
    """
    指定一个模板，统计其出现的次数。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    :param colored: 是否匹配颜色，默认为 False。
    """
    results = template_match(template, image, mask, transparent, threshold, max_results=-1)
    if remove_duplicate:
        results = _remove_duplicate_matches(results)
    if colored:
        results = [
            match for match in results 
            if hist_match(image, template, match.rect, threshold)
        ]
    if debug.enabled:
        result_image = _draw_result(image, results)
        result(
            'image.count',
            result_image,
            (
                f"template: {img(template)} \n"
                f"mask: {img(mask)} \n"
                f"transparent: {transparent} \n"
                f"threshold: {threshold} \n"
                f"count: {len(results)} \n"
            )
        )
    return len(results)

def expect(
    image: MatLike,
    template: MatLike | str,
    mask: MatLike | str | None = None,
    transparent: bool = False,
    threshold: float = 0.9,
    *,
    colored: bool = False,
) -> TemplateMatchResult:
    """
    指定一个模板，寻找其出现的第一个位置。若未找到，则抛出异常。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param colored: 是否匹配颜色，默认为 False。
    """
    ret = find(image, template, mask, transparent, threshold, colored=colored)
    if debug.enabled:
        result(
            'image.expect',
            _draw_result(image, ret),
            (
                f"template: {img(template)} \n"
                f"mask: {img(mask)} \n"
                f"args: transparent={transparent} threshold={threshold} \n"
                f"result: {ret}  "
                '<span class="text-success">SUCCESS</span>' if ret is not None 
                    else '<span class="text-danger">FAILED</span>'
            )
        )
    if ret is None:
        raise TemplateNotFoundError(image, template)
    else:
        return ret

def similar(
    image1: MatLike,
    image2: MatLike,
    threshold: float = 0.8
) -> bool:
    """
    判断两张图像是否相似。输入的两张图片必须为相同尺寸。
    """
    if image1.shape != image2.shape:
        raise ValueError('Expected two images with the same size.')
    return structural_similarity(image1, image2, multichannel=True) >= threshold
