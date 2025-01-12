import cv2
from cv2.typing import MatLike, Point

from .util import Rect
from .debug import result as debug_result, debug

Color = tuple[int, int, int] | str
"""颜色。三元组 `(r, g, b)` 或十六进制颜色字符串 `#RRGGBB`"""

def _unify_color(color: Color) -> Color:
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

def find_rgb(
    image: MatLike | str,
    color: Color,
    *,
    rect: Rect | None = None,
) -> tuple[int, int] | None:
    """
    在图像中查找指定颜色的点。

    :param image: 图像。可以是 MatLike 或图像文件路径。
    :param color: 颜色。可以是三元组 `(r, g, b)` 或十六进制颜色字符串 `#RRGGBB`。
    :param rect: 查找范围。如果为 None，则在整个图像中查找。
    """
    ret = None
    color = _unify_color(color)
    image = _unify_image(image)
    
    # 转换为RGB格式
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # 提取RGB通道
    r, g, b = color
    # 计算每个通道的差异
    r_diff = abs(image[:,:,0].astype(float) - float(r))
    g_diff = abs(image[:,:,1].astype(float) - float(g))
    b_diff = abs(image[:,:,2].astype(float) - float(b))
    
    # 找到完全匹配的点
    matches = (r_diff == 0) & (g_diff == 0) & (b_diff == 0)
    
    # 如果指定了搜索范围,只在范围内查找
    if rect is not None:
        x, y, w, h = rect
        matches[:y] = False
        matches[y+h:] = False
        matches[:,:x] = False
        matches[:,x+w:] = False
        
    # 找到第一个匹配点的坐标
    y_coords, x_coords = matches.nonzero()
    if len(y_coords) > 0:
        ret = (int(x_coords[0]), int(y_coords[0]))
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
                (0, 0, 255), 2)
        # 绘制搜索范围
        if rect is not None:
            x, y, w, h = rect
            # 红色圈出rect
            cv2.rectangle(result_image, (x, y), (x+w, y+h), (255, 0, 0), 2)
        debug_result('find_rgb', result_image, f'color={color}, rect={rect}, result={ret}')
    return ret