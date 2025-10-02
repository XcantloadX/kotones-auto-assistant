"""
badge 模块，用于关联带附加徽章的 UI。
例如：培育中的课程按钮+SP 图标、工作中分配偶像时偶像图标+好调图标
"""
from typing import Literal, NamedTuple

from kotonebot.primitives import Rect, RectTuple, PointTuple

BadgeCorner = Literal['lt', 'lm', 'lb', 'rt', 'rm', 'rb', 'mt', 'm', 'mb']
"""
Badge 位置。

可选 ``['l', 'm', 'r']``（左、中、右） 与 ``['t', 'm', 'b']``（上、中、下） 的组合。
"""

class BadgeResult(NamedTuple):
    object: Rect
    badge: Rect | None

def match(
        objects: list[Rect],
        badges: list[Rect],
        corner: BadgeCorner,
        threshold_distance: float = float('inf')
    ) -> list[BadgeResult]:
    """
    将对象与徽章匹配，根据指定的角落位置。

    :param objects: 对象矩形列表
    :param badges: 徽章矩形列表
    :param corner: 徽章相对于对象的位置，如 'lt'（左上）、'rb'（右下）等
    :param threshold_distance: 匹配的最大距离阈值，超过此距离的匹配将被忽略
    :return: 匹配结果列表
    """
    # 将 rect 转换为中心点
    def center(rect: RectTuple) -> PointTuple:
        return rect[0] + rect[2] // 2, rect[1] + rect[3] // 2
    
    # 判断 badge 是否在 object 的指定角落位置
    def is_in_corner(obj_rect: RectTuple, badge_center: PointTuple) -> bool:
        obj_center = center(obj_rect)
        x_obj, y_obj = obj_center
        x_badge, y_badge = badge_center
        
        # 获取对象的边界
        obj_left = obj_rect[0]
        obj_right = obj_rect[0] + obj_rect[2]
        obj_top = obj_rect[1]
        obj_bottom = obj_rect[1] + obj_rect[3]
        
        # 检查水平位置
        if corner.startswith('l') and x_badge >= x_obj:
            return False
        if corner.startswith('r') and x_badge <= x_obj:
            return False
        if corner.startswith('m') and (x_badge < obj_left or x_badge > obj_right):
            # 水平中间位置需要在对象的水平范围内
            return False
            
        # 检查垂直位置
        if corner.endswith('t') and y_badge >= y_obj:
            return False
        if corner.endswith('b') and y_badge <= y_obj:
            return False
        if corner.endswith('m') and (y_badge < obj_top or y_badge > obj_bottom):
            # 垂直中间位置需要在对象的垂直范围内
            return False
            
        return True

    results = []
    available_badges = badges.copy()

    for obj_rect in objects:
        obj_center = center(obj_rect.xywh)
        target_badge = None
        min_dist = float('inf')
        target_index = -1
        
        # 查找最近的符合条件的徽章
        for i, badge_rect in enumerate(available_badges):
            badge_center = center(badge_rect.xywh)
            if is_in_corner(obj_rect.xywh, badge_center):
                dist = ((badge_center[0] - obj_center[0]) ** 2 + (badge_center[1] - obj_center[1]) ** 2) ** 0.5
                if dist < min_dist and dist <= threshold_distance:
                    min_dist = dist
                    target_badge = badge_rect
                    target_index = i
        
        # 如果找到匹配的徽章，从可用徽章列表中移除
        if target_badge is not None:
            available_badges.pop(target_index)
            
        results.append(BadgeResult(obj_rect, target_badge))
        
    return results