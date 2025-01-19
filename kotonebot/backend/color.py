from os import name
from typing import Literal

import numpy as np
import cv2
from cv2.typing import MatLike, Point

from .util import Rect
from .debug import result as debug_result, debug, color as debug_color

RgbColorTuple = tuple[int, int, int]
RgbColorStr = str
RgbColor = RgbColorTuple | RgbColorStr
"""颜色。三元组 `(r, g, b)` 或十六进制颜色字符串 `#RRGGBB`"""

HsbColor = tuple[int, int, int]
"""
HSB颜色。三元组 `(h, s, b)`。

h: 0-180
s: 0-255
b: 0-255
"""

def _unify_color(color: RgbColor) -> RgbColor:
    if isinstance(color, str):
        if not color.startswith('#'):
            raise ValueError('Hex color string must start with #')
        color = color[1:]  # 去掉#
        if len(color) != 6:
            raise ValueError('Hex color string must be 6 digits')
        r = int(color[0:2], 16)
        g = int(color[2:4], 16) 
        b = int(color[4:6], 16)
        return (r, g, b)
    elif (
        isinstance(color, tuple)
        and len(color) == 3
        and all(isinstance(c, int) for c in color)
        and all(0 <= c <= 255 for c in color)
    ):
        return color
    else:
        raise ValueError('Invalid color format')

def _unify_image(image: MatLike | str) -> MatLike:
    if isinstance(image, str):
        image = cv2.imread(image)
    return image

def in_range(color: HsbColor, range: tuple[HsbColor, HsbColor]) -> bool:
    """
    判断颜色是否在范围内。

    :param color: 颜色。
    :param range: 范围。
    """
    h, s, b = color
    h1, s1, b1 = range[0]
    h2, s2, b2 = range[1]
    return h1 <= h <= h2 and s1 <= s <= s2 and b1 <= b <= b2

def find_rgb(
    image: MatLike | str,
    color: RgbColor,
    *,
    rect: Rect | None = None,
    threshold: float = 0.95,
    method: Literal['rgb_dist'] = 'rgb_dist',
) -> tuple[int, int] | None:
    """
    在图像中查找指定颜色的点。

    :param image: 
        图像。可以是 MatLike 或图像文件路径。
        注意如果参数为 MatLike，则颜色格式必须为 BGR，而不是 RGB。
    :param color: 颜色。可以是整数三元组 `(r, g, b)` 或十六进制颜色字符串 `#RRGGBB`。
    :param rect: 查找范围。如果为 None，则在整个图像中查找。
    :param threshold: 阈值，越大表示越相似，1 表示完全相似。默认为 0.95。
    :param method: 比较算法。默认为 'rgb_dist'，且目前也只有这个方法。

    ## 比较算法
    * rgb_dist:
        计算图片中每个点的颜色到目标颜色的欧氏距离，并以 442 为最大值归一化到 0-1 之间。
    """
    ret = None
    ret_similarity = 0
    found_color = None
    color = _unify_color(color)
    image = _unify_image(image)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # 将目标颜色转换为HSL
    r, g, b = color
    target_rgb = np.array([[[r, g, b]]], dtype=np.uint8)
    target_hls = cv2.cvtColor(target_rgb, cv2.COLOR_RGB2HLS)[0,0]
    target_h, target_l, target_s = target_hls

    # 将图像转换为HSL
    image_hls = cv2.cvtColor(image, cv2.COLOR_BGR2HLS).astype(np.float32)
    
    # 计算HSL空间中的距离
    # H通道需要特殊处理,因为它是环形的(0和180是相邻的)
    h_diff = np.minimum(
        np.abs(image_hls[:,:,0] - target_h),
        180 - np.abs(image_hls[:,:,0] - target_h)
    )
    l_diff = np.abs(image_hls[:,:,1] - target_l)
    s_diff = np.abs(image_hls[:,:,2] - target_s)
    
    # 归一化距离(H:0-180, L:0-255, S:0-255)
    h_diff = h_diff / 90  # 最大差值180/2
    l_diff = l_diff / 255
    s_diff = s_diff / 255
    
    # 计算加权距离
    dist = np.sqrt((h_diff * 2)**2 + l_diff**2 + s_diff**2) / np.sqrt(6)
    
    # 寻找结果
    matches: np.ndarray = dist <= (1 - threshold)
    # 只在rect范围内搜索
    if rect is not None:
        x, y, w, h = rect
        search_area = matches[y:y+h, x:x+w]
        if search_area.any():
            # 在裁剪区域中找到最小距离的点
            local_dist = dist[y:y+h, x:x+w]
            local_dist[~search_area] = float('inf')
            min_y, min_x = np.unravel_index(np.argmin(local_dist), local_dist.shape)
            # 转换回原图坐标
            ret = (int(x + min_x), int(y + min_y))
            ret_similarity = 1 - local_dist[min_y, min_x]
            found_color = tuple(image_rgb[y+min_y, x+min_x])
    # 在全图中找到最小距离的点
    else:
        if matches.any():
            dist[~matches] = float('inf')
            min_y, min_x = np.unravel_index(np.argmin(dist), dist.shape)
            ret = (int(min_x), int(min_y))
            ret_similarity = 1 - dist[min_y, min_x]
            found_color = tuple(image_rgb[min_y, min_x])
    # 调试输出
    if debug.enabled:
        result_image = image.copy()
        # 绘制结果点
        if ret is not None:
            x, y = ret
            # 蓝色圈出结果点
            cv2.rectangle(result_image, 
                (max(0, x-20), max(0, y-20)),
                (min(result_image.shape[1], x+20), min(result_image.shape[0], y+20)),
                (255, 0, 0), 2)
        # 绘制搜索范围
        if rect is not None:
            x, y, w, h = rect
            # 红色圈出rect
            cv2.rectangle(result_image, (x, y), (x+w, y+h), (0, 0, 255), 2)
        debug_result(
            'find_rgb',
            [result_image, image],
            f'target={debug_color(color)}\n'
            f'rect={rect}\n'
            f'result={ret}\n'
            f'similarity={ret_similarity}\n'
            f'found_color={debug_color(found_color)}\n'
            '(Red rect for search area, blue rect for result area)'
        )
    return ret

# https://stackoverflow.com/questions/43111029/how-to-find-the-average-colour-of-an-image-in-python-with-opencv
def dominant_color(
    image: MatLike | str,
    count: int = 1,
    *,
    rect: Rect | None = None,
) -> list[RgbColorStr]:
    """
    提取图像的主色调。

    :param image:
        图像。可以是 MatLike 或图像文件路径。
        如果是 MatLike，则颜色格式必须为 BGR。
    :param count: 提取的颜色数量。默认为 1。
    :param rect: 提取范围。如果为 None，则在整个图像中提取。
    """
    # 载入/裁剪图像
    img = _unify_image(image)
    if rect is not None:
        x, y, w, h = rect
        img = img[y:y+h, x:x+w]
    
    pixels = np.float32(img.reshape(-1, 3))

    n_colors = count
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
    flags = cv2.KMEANS_RANDOM_CENTERS

    _, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, flags) # type: ignore
    _, counts = np.unique(labels, return_counts=True)

    # 将颜色按出现次数排序
    indices = (-counts).argsort()
    dominant = palette[indices]
    
    # 转换为 RGB 格式并转为 16 进制颜色代码
    result: list[RgbColorStr] = []
    for i in range(min(n_colors, len(dominant))):
        color = dominant[i]
        # BGR -> RGB
        rgb = tuple(map(int, color[::-1]))
        hex_color = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
        result.append(hex_color)
    
    return result

if __name__ == '__main__':
    img = cv2.imread('tests/images/ui/commu_fast_forward_enabled.png')
    colors = dominant_color(img, 3)
    print("主调颜色:")
    for i, color in enumerate(colors, 1):
        print(f"{i}. {color}")
        # 创建一个纯色图像来展示颜色
        color_block = np.full((100, 100, 3), _unify_color(color)[::-1], dtype=np.uint8)
        cv2.imshow(f"Color {i}", color_block)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
