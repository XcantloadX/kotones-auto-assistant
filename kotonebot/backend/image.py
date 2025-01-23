import os
from typing import NamedTuple, Protocol, TypeVar, Sequence, runtime_checkable
from logging import getLogger

from .debug import result as debug_result, debug, img

import cv2
import numpy as np
from cv2.typing import MatLike, Rect, Point, Size
from skimage.metrics import structural_similarity

logger = getLogger(__name__)

class TemplateNoMatchError(Exception):
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

    @classmethod
    def from_template_match_result(cls, result: TemplateMatchResult, index: int):
        return cls(
            score=result.score,
            position=result.position,
            size=result.size,
            index=index
        )

class CropResult(NamedTuple):
    score: float
    position: Point
    size: Size
    image: MatLike

    @property
    def rect(self) -> Rect:
        return (self.position[0], self.position[1], self.size[0], self.size[1])

def _unify_image(image: MatLike | str, transparent: bool = False) -> MatLike:
    if isinstance(image, str):
        if not transparent:
            image = cv2.imread(image)
        else:
            image = cv2.imread(image, cv2.IMREAD_UNCHANGED)
    return image

def _draw_result(image: MatLike, matches: Sequence[ResultProtocol] | ResultProtocol | None) -> MatLike:
    """在图像上绘制匹配结果的矩形框。"""
    if matches is None:
        return image
    if isinstance(matches, ResultProtocol):
        matches = [matches]
    result_image = image.copy()
    for match in matches:
        cv2.rectangle(result_image, match.rect, (0, 0, 255), 2)
    return result_image

def _img2str(image: MatLike | str | None) -> str:
    if image is None:
        return 'None'
    if isinstance(image, str):
        try:
            return os.path.relpath(image)
        except ValueError:
            # ValueError: path is on mount 'C:', start on mount 'E:'
            # 程序路径与资源路径不在同一个地方的情况
            return image
    else:
        return '<opencv Mat>'

def _imgs2str(images: Sequence[MatLike | str | None] | None) -> str:
    if images is None:
        return 'None'
    return ', '.join([_img2str(image) for image in images])

def _result2str(result: TemplateMatchResult | MultipleTemplateMatchResult | None) -> str:
    if result is None:
        return 'None'
    return f'{result.rect} {result.score}'

def _results2str(results: Sequence[TemplateMatchResult | MultipleTemplateMatchResult] | None) -> str:
    if results is None:
        return 'None'
    return ', '.join([_result2str(result) for result in results])

def template_match(
    template: MatLike | str,
    image: MatLike | str,
    mask: MatLike | str | None = None,
    *,
    transparent: bool = False,
    threshold: float = 0.8,
    max_results: int = 5,
    remove_duplicate: bool = True,
    colored: bool = False,
) -> list[TemplateMatchResult]:
    """
    寻找模板在图像中的位置。

    .. note::
        `mask` 和 `transparent` 参数不能同时使用。
        如果使用透明图像，所有透明像素必须为 100% 透明，不能包含半透明像素。

    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param max_results: 最大结果数，默认为 1。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    :param colored: 是否匹配颜色，默认为 False。
    """
    # 统一参数
    template = _unify_image(template, transparent)
    image = _unify_image(image)
    if transparent is True and mask is not None:
        raise ValueError('mask and transparent cannot be used together')
    if mask is not None:
        mask = _unify_image(mask)
        mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)[1]
    if transparent is True:
        # https://stackoverflow.com/questions/57899997/how-to-create-mask-from-alpha-channel-in-opencv
        # 从透明图像中提取 alpha 通道作为 mask
        mask = cv2.threshold(template[:, :, 3], 0, 255, cv2.THRESH_BINARY)[1]
        template = template[:, :, :3]
    if (transparent or mask is not None) and threshold < 0.999:
        logger.warning(
            f'For template matching with transparent image or mask, '
            'threshold is recommended to be set to 0.999 or higher. '
            f'Got {threshold}'
        )
    # 匹配模板
    if mask is not None:
        # https://stackoverflow.com/questions/35642497/python-opencv-cv2-matchtemplate-with-transparency
        # 使用 Mask 时，必须使用 TM_CCORR_NORMED 方法
        result = cv2.matchTemplate(image, template, cv2.TM_CCORR_NORMED, mask=mask)
    else:
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    
    # ========== 整理结果 ==========
    # 去重、排序、转换为 TemplateMatchResult

    # 获取所有大于阈值的匹配结果并按分数排序
    h, w = template.shape[:2]
    matches = []
    if remove_duplicate:
        # 创建一个掩码来标记已匹配区域
        used_mask = np.zeros((image.shape[0], image.shape[1]), np.uint8)
    
    # 获取所有匹配点并按分数从高到低排序
    match_points = np.where(result >= threshold)
    scores = result[match_points]
    sorted_indices = np.argsort(-scores)  # 降序排序
    
    for idx in sorted_indices:
        y, x = match_points[0][idx], match_points[1][idx]
        score = float(scores[idx])
        
        # 去重
        if remove_duplicate:
            # 获取匹配区域的中心点
            center_x = x + w // 2
            center_y = y + h // 2
            
            # 如果中心点已被标记，跳过此匹配
            if used_mask[center_y, center_x] == 255:
                continue
                
            # 标记整个匹配区域
            used_mask[y:y+h, x:x+w] = 255
        
        # 颜色匹配
        if colored:
            img1, img2 = image[y:y+h, x:x+w], template
            if mask is not None:
                # 如果用了 Mask，需要裁剪出 Mask 区域，其余部分置黑
                img1 = cv2.bitwise_and(img1, img1, mask=mask)
                img2 = cv2.bitwise_and(img2, img2, mask=mask)

            if not hist_match(img1, img2, (0, 0, w, h)):
                continue
        
        matches.append(TemplateMatchResult(
            score=score,
            position=(int(x), int(y)),
            size=(int(w), int(h))
        ))
        
        # 如果达到最大结果数，提前结束
        if max_results > 0 and len(matches) >= max_results:
            break
    
    return matches

def hist_match(
    image: MatLike | str,
    template: MatLike | str,
    rect: Rect | None = None,
    threshold: float = 0.9,
) -> bool:
    """
    对输入图像的矩形部分与模板进行颜色直方图匹配。
    将图像分为上中下三个区域，分别计算直方图并比较相似度。

    https://answers.opencv.org/question/59027/template-matching-using-color/

    :param image: 输入图像
    :param template: 模板图像
    :param rect: 输入图像中待匹配的矩形区域
    :param threshold: 相似度阈值，默认为 0.8
    :return: 是否匹配成功
    """
    # 统一参数
    image = _unify_image(image)
    template = _unify_image(template)

    # 从图像中裁剪出矩形区域
    if rect is None:
        roi = image
    else:
        x, y, w, h = rect
        roi = image[y:y+h, x:x+w]

    # 确保尺寸一致
    if roi.shape != template.shape:
        # roi = cv2.resize(roi, (template.shape[1], template.shape[0]))
        raise ValueError('Expected two images with the same size.')

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

def find_all_crop(
    image: MatLike | str,
    template: MatLike | str,
    mask: MatLike | str | None = None,
    transparent: bool = False,
    threshold: float = 0.8,
    *,
    colored: bool = False,
    remove_duplicate: bool = True,
) -> list[CropResult]:
    """
    指定一个模板，在输入图像中寻找其出现的所有位置，并裁剪出结果。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param colored: 是否匹配颜色，默认为 False。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    """
    matches = template_match(
        template,
        image,
        mask,
        transparent=transparent,
        threshold=threshold,
        max_results=-1,
        remove_duplicate=remove_duplicate,
        colored=colored,
    )
    logger.debug(
        f'find_all_crop(): template: {_img2str(template)} image: {_img2str(image)} mask: {_img2str(mask)} '
        f'matches: {_results2str(matches)}'
    )
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
    *,
    transparent: bool = False,
    threshold: float = 0.8,
    debug_output: bool = True,
    colored: bool = False,
    remove_duplicate: bool = True,
) -> TemplateMatchResult | None:
    """
    指定一个模板，在输入图像中寻找其出现的第一个位置。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param debug_output: 是否输出调试信息，默认为 True。
    :param colored: 是否匹配颜色，默认为 False。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    """
    matches = template_match(
        template,
        image,
        mask,
        transparent=transparent,
        threshold=threshold,
        max_results=1,
        remove_duplicate=remove_duplicate,
        colored=colored,
    )
    logger.debug(
        f'find(): template: {_img2str(template)} image: {_img2str(image)} mask: {_img2str(mask)} '
        f'matches: {_results2str(matches)}'
    )
    # 调试输出
    if debug.enabled and debug_output:
        result_image = _draw_result(image, matches)
        result_text = f"template: {img(template)} \n"
        result_text += f"matches: {len(matches)} \n"
        for match in matches:
            result_text += f"score: {match.score} position: {match.position} size: {match.size} \n"
        debug_result(
            'image.find',
            [result_image, image],
            result_text
        )
    return matches[0] if len(matches) > 0 else None

def find_all(
    image: MatLike,
    template: MatLike | str,
    mask: MatLike | str | None = None,
    *,
    transparent: bool = False,
    threshold: float = 0.8,
    remove_duplicate: bool = True,
    colored: bool = False,
    debug_output: bool = True,
) -> list[TemplateMatchResult]:
    """
    指定一个模板，在输入图像中寻找其出现的所有位置。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    :param colored: 是否匹配颜色，默认为 False。
    """
    results = template_match(
        template,
        image,
        mask,
        transparent=transparent,
        threshold=threshold,
        max_results=-1,
        remove_duplicate=remove_duplicate,
        colored=colored,
    )
    logger.debug(
        f'find_all(): template: {_img2str(template)} image: {_img2str(image)} mask: {_img2str(mask)} '
        f'matches: {_results2str(results)}'
    )
    if debug.enabled and debug_output:
        result_image = _draw_result(image, results)
        debug_result(
            'image.find_all',
            [result_image, image],
            f"template: {img(template)} \n"
            f"matches: {len(results)} \n"
        )
    return results

def find_multi(
    image: MatLike,
    templates: list[MatLike | str],
    masks: list[MatLike | str | None] | None = None,
    *,
    transparent: bool = False,
    threshold: float = 0.8,
    colored: bool = False,
    remove_duplicate: bool = True,
) -> MultipleTemplateMatchResult | None:
    """
    指定多个模板，在输入图像中逐个寻找模板，返回第一个匹配到的结果。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param templates: 模板图像列表，可以是图像路径或 cv2.Mat。
    :param masks: 掩码图像列表，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param colored: 是否匹配颜色，默认为 False。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    """
    ret = None
    if masks is None:
        _masks = [None] * len(templates)
    else:
        _masks = masks
    for index, (template, mask) in enumerate(zip(templates, _masks)):
        find_result = find(
            image,
            template,
            mask,
            transparent=transparent,
            threshold=threshold,
            colored=colored,
            debug_output=False,
            remove_duplicate=remove_duplicate,
        )
        # 调试输出
        if find_result is not None:
            ret = MultipleTemplateMatchResult(
                score=find_result.score,
                position=find_result.position,
                size=find_result.size,
                index=index
            )
            break
    logger.debug(
        f'find_multi(): templates: {_imgs2str(templates)} images: {_img2str(image)} masks: {_imgs2str(masks)} '
        f'result: {_result2str(ret)}'
    )
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
        debug_result(
            'image.find_multi',
            [_draw_result(image, ret), image],
            msg
        )
    return ret

def find_all_multi(
    image: MatLike,
    templates: list[MatLike | str],
    masks: list[MatLike | str | None] | None = None,
    *,
    transparent: bool = False,
    threshold: float = 0.8,
    colored: bool = False,
    remove_duplicate: bool = True,
) -> list[MultipleTemplateMatchResult]:
    """
    指定多个模板，在输入图像中逐个寻找模板，返回所有匹配到的结果。

    此函数等价于
    ```python
    result = []
    for template in templates:
        result.append(find_all(template, ...))
    ```

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param templates: 模板图像列表，可以是图像路径或 cv2.Mat。
    :param masks: 掩码图像列表，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param colored: 是否匹配颜色，默认为 False。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    :return: 匹配到的一维结果列表。
    """
    ret: list[MultipleTemplateMatchResult] = []
    if masks is None:
        _masks = [None] * len(templates)
    else:
        _masks = masks

    for index, (template, mask) in enumerate(zip(templates, _masks)):
        results = find_all(
            image,
            template,
            mask,
            transparent=transparent,
            threshold=threshold,
            colored=colored,
            remove_duplicate=remove_duplicate,
            debug_output=False,
        )
        ret.extend([
            MultipleTemplateMatchResult.from_template_match_result(r, index)
            for r in results
        ])
    logger.debug(
        f'find_all_multi(): templates: {_imgs2str(templates)} images: {_img2str(image)} masks: {_imgs2str(masks)} '
        f'result: {_results2str(ret)}'
    )
    if debug.enabled:
        # 参数表格
        msg = (
            "<center>Templates</center>"
            "<table class='result-table'>"
            "<tr><th>Template</th><th>Mask</th></tr>"
        )
        for t, m in zip(templates, _masks):
            msg += f"<tr><td>{img(t)}</td><td>{img(m)}</td></tr>"
        msg += "</table>"
        msg += "<br>"
        # 结果表格
        msg += (
            "<center>Results</center>"
            "<table class='result-table'>"
            "<tr><th>Template</th><th>Mask</th><th>Result</th></tr>"
        )
        for result in ret:
            template = templates[result.index]
            mask = _masks[result.index]
            msg += f"<tr><td>{img(template)}</td><td>{img(mask)}</td><td>{result.position}</td></tr>"
        msg += "</table>"
        debug_result(
            'image.find_all_multi',
            [_draw_result(image, ret), image], 
            msg
        )
    return ret

def count(
    image: MatLike,
    template: MatLike | str,
    mask: MatLike | str | None = None,
    *,
    transparent: bool = False,
    threshold: float = 0.8,
    remove_duplicate: bool = True,
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
    results = template_match(
        template,
        image,
        mask,
        transparent=transparent,
        threshold=threshold,
        max_results=-1,
        remove_duplicate=remove_duplicate,
        colored=colored,
    )
    logger.debug(
        f'count(): template: {_img2str(template)} image: {_img2str(image)} mask: {_img2str(mask)} '
        f'result: {_results2str(results)}'
    )
    if debug.enabled:
        result_image = _draw_result(image, results)
        debug_result(
            'image.count',
            [result_image, image],
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
    *,
    transparent: bool = False,
    threshold: float = 0.8,
    colored: bool = False,
    remove_duplicate: bool = True,
) -> TemplateMatchResult:
    """
    指定一个模板，寻找其出现的第一个位置。若未找到，则抛出异常。

    :param image: 图像，可以是图像路径或 cv2.Mat。
    :param template: 模板图像，可以是图像路径或 cv2.Mat。
    :param mask: 掩码图像，可以是图像路径或 cv2.Mat。
    :param transparent: 若为 True，则认为输入模板是透明的，并自动将透明模板转换为 Mask 图像。
    :param threshold: 阈值，默认为 0.8。
    :param colored: 是否匹配颜色，默认为 False。
    :param remove_duplicate: 是否移除重复结果，默认为 True。
    """
    ret = find(
        image,
        template,
        mask,
        transparent=transparent,
        threshold=threshold,
        colored=colored,
        remove_duplicate=remove_duplicate,
        debug_output=False,
    )
    logger.debug(
        f'expect(): template: {_img2str(template)} image: {_img2str(image)} mask: {_img2str(mask)} '
        f'result: {_result2str(ret)}'
    )
    if debug.enabled:
        debug_result(
            'image.expect',
            [_draw_result(image, ret), image],
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
        raise TemplateNoMatchError(image, template)
    else:
        return ret

def similar(
    image1: MatLike,
    image2: MatLike,
    threshold: float = 0.9
) -> bool:
    """
    判断两张图像是否相似（灰度）。输入的两张图片必须为相同尺寸。
    """
    if image1.shape != image2.shape:
        raise ValueError('Expected two images with the same size.')
    image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
    result = structural_similarity(image1, image2, multichannel=True)
    logger.debug(
        f'similar(): image1: {_img2str(image1)} image2: {_img2str(image2)} '
        f'result: {result}'
    )
    # 调试输出
    if debug.enabled:
        result_image = np.hstack([image1, image2])
        debug_result(
            'image.similar',
            [result_image, image1, image2],
            f"result: {result} >= {threshold} == {result >= threshold} \n"
        )
    return result >= threshold


