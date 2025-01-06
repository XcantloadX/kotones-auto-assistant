import cv2
import numpy as np
from device.adb import AdbDevice
from adbutils import adb

# 初始化ADB设备
adb.connect("127.0.0.1:16384")
device = AdbDevice(adb.device_list()[0])

# 定义检测参数
TARGET_ASPECT_RATIO_RANGE = (0.73, 0.80)
TARGET_COLOR = (240, 240, 240)
YELLOW_LOWER = np.array([20, 100, 100])
YELLOW_UPPER = np.array([30, 255, 255])

import ctypes
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
screen = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

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

def detect_cards(image):
    original = image.copy()
    # 保存
    cv2.imwrite("original.png", original)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY)
    edges = cv2.Canny(binary, 150, 300)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    show("edges", edges)

    card_contours = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area > 400:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            x, y, w, h = cv2.boundingRect(approx)
            # 展示裁剪后的图像
            card_region = image[y:y+h, x:x+w]
            show(f"card_region", card_region)

            # 检查长宽比
            aspect_ratio = w / float(h)
            if not (TARGET_ASPECT_RATIO_RANGE[0] < aspect_ratio < TARGET_ASPECT_RATIO_RANGE[1]):
                continue
                
            # 检查颜色
            card_region = image[y:y+h, x:x+w]
            bottom_right = card_region[-40:, -40:]
            bottom_left = card_region[-40:, :40]
            avg_color_br = np.mean(bottom_right, axis=(0, 1))
            avg_color_bl = np.mean(bottom_left, axis=(0, 1))
            
            if not (np.allclose(avg_color_br, TARGET_COLOR, atol=5) and 
                    np.allclose(avg_color_bl, TARGET_COLOR, atol=5)):
                continue
                
            # 计算黄色荧光值
            hsv = cv2.cvtColor(card_region, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)
            glow_value = cv2.countNonZero(mask)
            
            card_contours.append((x, y, w, h, glow_value))


    # 在原图上画出所有轮廓并展示
    # 按顺序画出所有轮廓
    preview = image.copy()
    for i, (x, y, w, h, glow_value) in enumerate(card_contours):
        cv2.rectangle(preview, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(preview, f"Card {i+1}", (x, y-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
    show("cards", preview)
    
    return card_contours

def main():
    while True:
        # 获取屏幕截图
        img = device.screenshot()
        
        # 检测卡片
        cards = detect_cards(img)
        
        # 如果检测到3个或更多卡片
        if len(cards) >= 3:
            print("检测到3个卡片！")
            # 在图像上绘制检测结果
            for i, (x, y, w, h, glow) in enumerate(cards[:3]):
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(img, f"Card {i+1}", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # 显示结果
            cv2.imshow("Detected Cards", img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            break
            
        # 等待1秒后继续检测
        cv2.waitKey(1000)

if __name__ == "__main__":
    main()
