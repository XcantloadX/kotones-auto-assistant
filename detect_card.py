import cv2
import numpy as np

def detect_glowing_card(image_path):
    # 读取图像
    img = cv2.imread(image_path)
    
    # 转换到HSV色彩空间
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 1. 首先检测卡片轮廓
    # 转换成灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 使用高斯模糊减少噪声
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    
    # 使用Canny边缘检测
    edges = cv2.Canny(blurred, 50, 150)
    
    # 膨胀边缘使轮廓更明显
    dilated = cv2.dilate(edges, None, iterations=2)
    cv2.imshow('Dilated Edges', dilated)
    cv2.waitKey(0)
    
    # 查找轮廓
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 筛选可能的卡片轮廓
    card_contours = []
    min_card_area = 5000  # 最小卡片面积
    max_card_area = 50000  # 最大卡片面积
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_card_area < area < max_card_area:
            # 计算轮廓的主要特征
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            # 计算最小外接矩形
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            
            # 计算轮廓的形状特征
            aspect_ratio = rect[1][0] / rect[1][1] if rect[1][1] != 0 else 0
            
            # 检查是否符合卡片特征
            if 0.5 < aspect_ratio < 2.0:  # 合理的宽高比
                card_contours.append(contour)
    
    # 2. 创建卡片掩码
    card_mask = np.zeros_like(gray)
    cv2.drawContours(card_mask, card_contours, -1, (255), -1)
    
    # 3. 检测黄色发光
    # 定义黄色的HSV范围
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([30, 255, 255])
    
    # 创建黄色掩码
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    # 4. 结合卡片掩码和黄色掩码
    final_mask = cv2.bitwise_and(yellow_mask, card_mask)
    
    # 5. 分析每张卡片
    glow_scores = []
    card_regions = []
    
    for contour in card_contours:
        # 获取卡片边界框
        x, y, w, h = cv2.boundingRect(contour)
        card_regions.append((x, y, x+w, y+h))
        
        # 计算该区域内的发光得分
        region_mask = final_mask[y:y+h, x:x+w]
        score = np.sum(region_mask > 0)
        glow_scores.append(score)
    
    # 6. 找出发光卡片
    if glow_scores:
        glowing_card_index = np.argmax(glow_scores)
        
        # 在原图上标记结果
        result = img.copy()
        for i, (x1, y1, x2, y2) in enumerate(card_regions):
            color = (0, 255, 0) if i == glowing_card_index else (0, 0, 255)
            cv2.rectangle(result, (x1, y1), (x2, y2), color, 2)
            
        return {
            'glowing_card_index': glowing_card_index,
            'glow_scores': glow_scores,
            'result_image': result,
            'card_mask': card_mask,
            'yellow_mask': yellow_mask,
            'final_mask': final_mask
        }
    else:
        return None

def display_results(results):
    if results is None:
        print("未检测到卡片")
        return
        
    # 显示所有处理步骤的结果
    cv2.imshow('Original with Detection', results['result_image'])
    cv2.imshow('Card Mask', results['card_mask'])
    cv2.imshow('Yellow Mask', results['yellow_mask'])
    cv2.imshow('Final Mask', results['final_mask'])
    
    print(f"发光卡片序号: {results['glowing_card_index']}")
    print(f"各卡片发光得分: {results['glow_scores']}")
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def main():
    image_path = r"C:\Users\ZhouXiaokang\Downloads\Snipaste_2024-12-26_10-11-58.png"  # 替换为实际图像路径
    results = detect_glowing_card(image_path)
    display_results(results)

if __name__ == '__main__':
    main()