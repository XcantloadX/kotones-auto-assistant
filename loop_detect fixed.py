import cv2
from cv2.typing import MatLike
import numpy as np
from client.device.adb import AdbDevice
from adbutils import adb
from typing import NamedTuple
# 初始化ADB设备
adb.connect("127.0.0.1:16384")
device = AdbDevice(adb.device_list()[0])

# 定义检测参数
TARGET_ASPECT_RATIO_RANGE = (0.73, 0.80)
TARGET_COLOR = (240, 240, 240)
YELLOW_LOWER = np.array([20, 100, 100])
YELLOW_UPPER = np.array([30, 255, 255])
GLOW_EXTENSION = 10  # 向外扩展的像素数
GLOW_THRESHOLD = 1200  # 荧光值阈值

import ctypes
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
screen = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

class CardDetectResult(NamedTuple):
    x: int
    y: int
    w: int
    h: int
    glow_value: int
    is_target: bool

def show(title, image):
    img_h, img_w = image.shape[:2]
    scale_x = screen[0] * 0.8 / img_w
    scale_y = screen[1] * 0.8 / img_h
    
    if scale_x < 1 or scale_y < 1:
        scale = min(scale_x, scale_y)
        resized = cv2.resize(image, (0, 0), fx=scale, fy=scale)
    else:
        resized = image

    cv2.imshow(title, resized)
    # cv2.waitKey(0)
    # cv2.destroyWindow(title)

# 添加固定的卡片坐标
# for: 1280x720
CARD_POSITIONS = [
    (47, 883, 192, 252),  # 左卡片 (x, y, w, h)
    (264, 883, 192, 252),  # 中卡片
    (481, 883, 192, 252)   # 右卡片
]
CARD_PAD = 25
CARD_SCREEN_PAD = 17

def calc_pos(count: int) -> list[tuple[int, int, int, int]]:
    # 算法：根据 CARD_POSITIONS（三张的情况），
    # 如果卡片数量过多导致无法保持原间距，则改为重叠布局
    # 重叠时保持与屏幕两边间距为CARD_PAD
    # 算出 count 张卡片的位置
    
    # 如果只有一张卡片,直接返回中间位置
    if count == 1:
        middle_card = CARD_POSITIONS[1]  # 取中间卡片位置
        return [middle_card]
    
    # 计算原始卡片间距
    card_spacing = CARD_POSITIONS[1][0] - CARD_POSITIONS[0][0]  # 相邻卡片x坐标之差
    card_width = CARD_POSITIONS[0][2]
    
    # 计算屏幕可用宽度(减去两边的padding)
    screen_width = 720  # 使用最右卡片右边缘作为屏幕宽度
    available_width = screen_width - (CARD_SCREEN_PAD * 2)
    
    # 计算使用原始间距时的总宽度
    original_total_width = (count - 1) * card_spacing + card_width
    
    # 判断是否需要重叠布局
    if original_total_width > available_width:
        # 需要重叠布局
        # 计算重叠距离 = (总宽度 - 可用宽度) / (卡片数量 - 1)
        # overlap = (original_total_width - available_width) // (count - 1)
        # spacing = card_width - overlap
        spacing = (available_width - card_width * count - CARD_SCREEN_PAD * 2) // (count)
        start_x = CARD_SCREEN_PAD
    else:
        # 使用原始间距，水平居中
        spacing = card_spacing
        start_x = (screen_width - original_total_width) // 2
    
    # 生成所有卡片位置
    positions = []
    x = start_x
    for i in range(count):
        # y,w,h 保持不变,使用第一张卡的参数
        y = CARD_POSITIONS[0][1]
        w = CARD_POSITIONS[0][2]
        h = CARD_POSITIONS[0][3]
        positions.append((x, y, w, h))
        x += spacing + card_width  # 确保x是整数
    # 四舍五入
    positions = [(round(x), round(y), round(w), round(h)) for x, y, w, h in positions]
    return positions


def detect_cards(image: MatLike, card_dimensions: list[tuple[int, int, int, int]]) -> list[CardDetectResult]:
    card_contours = []
    preview = image.copy()
    # 圈出所有卡片预览
    pv = image.copy()
    # for x, y, w, h in CARD_POSITIONS:
    #     cv2.rectangle(pv, (x, y), (x+w, y+h), (0, 255, 0), 1)
    #     # 红色画出外围
    #     cv2.rectangle(pv, (x-GLOW_EXTENSION, y-GLOW_EXTENSION), (x+w+GLOW_EXTENSION, y+h+GLOW_EXTENSION), (0, 0, 255), 1)
    # show("pv", pv)

    for x, y, w, h in card_dimensions:
        # 获取扩展后的卡片区域坐标
        outer_x = max(0, x - GLOW_EXTENSION)
        outer_y = max(0, y - GLOW_EXTENSION)
        outer_w = w + (GLOW_EXTENSION * 2)
        outer_h = h + (GLOW_EXTENSION * 2)
        
        # 获取内外两个区域
        outer_region = image[outer_y:y+h+GLOW_EXTENSION, outer_x:x+w+GLOW_EXTENSION]
        inner_region = image[y:y+h, x:x+w]
        
        # 创建掩码
        outer_hsv = cv2.cvtColor(outer_region, cv2.COLOR_BGR2HSV)
        inner_hsv = cv2.cvtColor(inner_region, cv2.COLOR_BGR2HSV)
        
        # 计算外部区域的黄色部分
        outer_mask = cv2.inRange(outer_hsv, YELLOW_LOWER, YELLOW_UPPER)
        inner_mask = cv2.inRange(inner_hsv, YELLOW_LOWER, YELLOW_UPPER)
        
        # 创建环形区域的掩码（仅计算扩展区域的荧光值）
        ring_mask = outer_mask.copy()
        ring_mask[GLOW_EXTENSION:GLOW_EXTENSION+h, GLOW_EXTENSION:GLOW_EXTENSION+w] = 0
        
        # 计算环形区域的荧光值
        glow_value = cv2.countNonZero(ring_mask)
        
        card_contours.append(CardDetectResult(
            x,
            y,
            w,
            h,
            glow_value,
            glow_value > GLOW_THRESHOLD
        ))
        
        # 在预览图像上画出内外区域
        cv2.rectangle(preview, (outer_x, outer_y), (outer_x+outer_w, outer_y+outer_h), (0, 0, 255), 2)
        cv2.rectangle(preview, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(preview, f"Glow: {glow_value}", (x, y-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        if glow_value > GLOW_THRESHOLD:  # 假设阈值为200
            cv2.putText(preview, "TargetCard", (x, y+20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    show("cards", preview)
    cv2.waitKey(1)
    return card_contours

def main():
    # while True:
    #     # 获取屏幕截图
    #     img = device.screenshot()
        
    #     # 检测卡片
    #     cards = detect_cards(img)
        
    #     # 如果检测到3个或更多卡片
    #     if len(cards) >= 3:
    #         print("检测到3个卡片！")
    #         # 在图像上绘制检测结果
    #         for i, (x, y, w, h, glow) in enumerate(cards[:3]):
    #             cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
    #             cv2.putText(img, f"Card {i+1}", (x, y-10), 
    #                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
    #         # 显示结果
    #         cv2.imshow("Detected Cards", img)
    #         # cv2.waitKey(0)
    #         # cv2.destroyAllWindows()
    #         # break
            
    #     # 等待1秒后继续检测
    #     cv2.waitKey(1000)

    from kotonebot.client.device.fast_screenshot import AdbFastScreenshots
    with AdbFastScreenshots(
        adb_path=r"D:\SDK\Android\platform-tools\adb.exe",
        device_serial="127.0.0.1:16384",
        time_interval=179,
        width=720,
        height=1280,
        bitrate="5M",
        use_busybox=False,
        connect_to_device=True,
        screenshotbuffer=10,
        go_idle=0,
    ) as adbscreen:
        pos_tobe_clicked = None
        pos_clicked_count = 0
        for image in adbscreen:
            if pos_tobe_clicked is not None:
                pos_clicked_count += 1
                if pos_clicked_count >= 2:
                    pos_tobe_clicked = None
                    pos_clicked_count = 0
                    continue
                device.click(*pos_tobe_clicked)
            
            # 获取屏幕截图
            img = image
            
            # 检测卡片
            cards = detect_cards(img, CARD_POSITIONS)
            
            # 如果检测到3个或更多卡片
            if len(cards) >= 3:
                # print("检测到3个卡片！")
                # 在图像上绘制检测结果
                for i, card in enumerate(cards[:3]):
                    cv2.rectangle(img, (card.x, card.y), (card.x+card.w, card.y+card.h), (0, 255, 0), 2)
                    cv2.putText(img, f"Card {i+1}", (card.x, card.y-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)                    
                # 打印最大荧光值
                print(f"最大荧光值: {max(card.glow_value for card in cards)}")
                # 显示结果
                # cv2.imshow("Detected Cards", img)
                cv2.waitKey(1)
                # 如果有则点击目标卡
                if not pos_tobe_clicked and any(card.is_target for card in cards):
                    target_card = next(card for card in cards if card.is_target)
                    pos = (target_card.x + target_card.w // 2, target_card.y + target_card.h // 2)
                    print(f"点击位置: {pos}")
                    pos_tobe_clicked = pos
                    pos_clicked_count = 0

# TODO: 最终考试前练习不榨干体力

if __name__ == "__main__":
    main()
