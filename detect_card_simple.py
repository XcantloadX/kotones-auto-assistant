import cv2
import numpy as np

# 使用其他 API 获取屏幕尺寸
import ctypes
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
screen = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

ignore_show = False

def show(title, image):
    img_h, img_w = image.shape[:2]
    scale_x = screen[0] * 0.9 / img_w
    scale_y = screen[1] * 0.9 / img_h
    
    if scale_x < 1 or scale_y < 1:
        scale = min(scale_x, scale_y)
        resized = cv2.resize(image, (0, 0), fx=scale, fy=scale)
    else:
        resized = image

    if not ignore_show:
        cv2.imshow(title, resized)
        cv2.waitKey(0)
        cv2.destroyWindow(title)

# 读取图像
# image = cv2.imread(r"C:\Users\ZhouXiaokang\Downloads\1735195113729.jpg")
# image = cv2.imread(r"./test_images/1.jpg")
image = cv2.imread(r"./test_images/test1.png")
original = image.copy()

# 转换为灰度图像，并模糊以减少噪声
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
# blurred = cv2.GaussianBlur(gray, (5, 5), 0)
# _, binary = cv2.threshold(original, 150, 255, cv2.THRESH_BINARY)
_, binary = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY)

kernel = np.ones((2, 2),np.uint8) # 定义卷积核大小，可以根据实际情况调整
erosion = cv2.erode(binary, kernel,iterations = 7)
dilation = cv2.dilate(binary, kernel,iterations = 10) # 膨胀操作
# closing = cv2.morphologyEx(dilation, cv2.MORPH_CLOSE, kernel) # 闭运算


# 边缘检测
edges = cv2.Canny(binary, 150, 300)

show("Binary", binary)
# show("erosion", erosion)
# show("dilation", dilation)
show("Edges", edges)
cv2.waitKey(0)

# 找到所有轮廓
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


# 封闭轮廓
# closed_contours = []
# for contour in contours:
#     epsilon = 0.01 * cv2.arcLength(contour, True)
#     approx = cv2.approxPolyDP(contour, epsilon, True)
#     closed_contours.append(approx)

# 按轮廓长度排序，只保留前10个
# contours = sorted(contours, key=lambda c: cv2.arcLength(c, False), reverse=True)[:10]

# # # 只保留直线轮廓
# filtered_contours = []
# for contour in contours:
#     # 使用最小二乘法拟合直线
#     [vx, vy, x, y] = cv2.fitLine(contour, cv2.DIST_L2, 0, 0.01, 0.01)
#     # 计算轮廓的角度
#     angle = np.arctan2(vy, vx) * 180 / np.pi
#     # 如果角度接近水平或垂直，则保留该轮廓
#     if abs(angle) < 30 or abs(angle - 90) < 30:
#         filtered_contours.append(contour)
# contours = filtered_contours


# # 移除长度过短的轮廓
# min_contour_length = 150  # 设置最小轮廓长度阈值
# filtered_contours = [contour for contour in contours if cv2.arcLength(contour, True) > min_contour_length]
# contours = filtered_contours


# 绘制所有封闭轮廓
cv2.drawContours(original, contours, -1, (0, 255, 0), 2)
show("Contours", original)


cv2.waitKey(0)
cv2.destroyAllWindows()


# 创建一个空白图像用于绘制轮廓
contour_image = np.zeros_like(image)

# 绘制所有轮廓
cv2.drawContours(contour_image, contours, -1, (255, 255, 255), 1)

# 显示只有轮廓的图像
show("Contours Only", contour_image)
cv2.waitKey(0)
cv2.destroyAllWindows()


# 用于存储每张卡片的荧光值
card_glow_values = []
card_contours = []

# 遍历轮廓，筛选出卡片区域
for contour in contours:
    area = cv2.contourArea(contour)
    if area > 800:  # 忽略小区域
        # 近似轮廓形状
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        # 计算外接矩形
        x, y, w, h = cv2.boundingRect(approx)
        
        card_region = image[y:y+h, x:x+w]
        # 绘制并展示该区域
        # cv2.rectangle(original, (x, y), (x + w, y + h), (0, 0, 255), 2)
        # show("Card Region pre", card_region)
        # cv2.waitKey(0)

        # 一起展示轮廓
        # Create a tight black background for the contour
        x, y, w, h = cv2.boundingRect(approx)
        padding = 50
        contour_img = np.zeros((h + padding*2, w + padding*2, 3), dtype=np.uint8)
        # Adjust contour coordinates for padding
        shifted_contour = approx.copy()
        shifted_contour[:,:,0] = approx[:,:,0] - x + padding
        shifted_contour[:,:,1] = approx[:,:,1] - y + padding
        # Draw contour on black background
        # cv2.drawContours(contour_img, [shifted_contour], -1, (0, 255, 0), 2)
        # show("Contour on Black", contour_img)
        # cv2.waitKey(0)
        
        # 条件 1：满足长宽比
        aspect_ratio = w / float(h)
        TARGET_ASPECT_RATIO_RANGE = (0.73, 0.80)
        if not (TARGET_ASPECT_RATIO_RANGE[0] < aspect_ratio < TARGET_ASPECT_RATIO_RANGE[1]):
            continue
        # 条件 3：颜色要求
        # 提取区域右下角与左下角(40, 40)正方形区域的平均颜色
        bottom_right = card_region[-40:, -40:]
        bottom_left = card_region[-40:, :40]
        avg_color_br = np.mean(bottom_right, axis=(0, 1))
        avg_color_bl = np.mean(bottom_left, axis=(0, 1))
        # 检查是否都近似 #f0f0f0
        TARGET_COLOR = (240, 240, 240)
        # 绘制并展示该区域
        cv2.rectangle(original, (x, y), (x + w, y + h), (0, 0, 255), 2)
        # 把颜色画上去

        # 绘制并展示该区域
        cv2.rectangle(original, (x, y), (x + w, y + h), (0, 0, 255), 2)
        show("Card Region pre", card_region)
        
        # preview = cv2.putText(original.copy(), str(avg_color_br), (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        # show("Card Region", preview)
        # cv2.waitKey(0)
        if not (
            np.allclose(avg_color_br, TARGET_COLOR, atol=5) 
            and np.allclose(avg_color_bl, TARGET_COLOR, atol=5)
        ): 
            continue


        if TARGET_ASPECT_RATIO_RANGE[0] < aspect_ratio < TARGET_ASPECT_RATIO_RANGE[1]:
            # 提取卡片区域
            card_region = image[y:y+h, x:x+w]

            # 转换为 HSV 色彩空间
            hsv = cv2.cvtColor(card_region, cv2.COLOR_BGR2HSV)
            
            # 定义黄色的 HSV 阈值
            lower_yellow = np.array([20, 100, 100])
            upper_yellow = np.array([30, 255, 255])
            
            # 创建遮罩，提取黄色区域
            mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
            
            # 计算荧光值（黄色像素的总数）
            glow_value = cv2.countNonZero(mask)
            
            # 保存卡片轮廓和对应的荧光值
            card_glow_values.append(glow_value)
            card_contours.append((x, y, w, h))
            


# 绘制筛选后的边缘
for contour in card_contours:
    x, y, w, h = contour
    cv2.rectangle(original, (x, y), (x + w, y + h), (255, 0, 0), 5)

# 找到荧光值最高的卡片
if card_glow_values:
    max_glow_index = np.argmax(card_glow_values)
    max_glow_card = card_contours[max_glow_index]
    
    # 绘制荧光值最高的卡片轮廓
    x, y, w, h = max_glow_card
    cv2.rectangle(original, (x, y), (x + w, y + h), (0, 255, 0), 5)
    cv2.putText(original, "Max Glow", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

# 显示结果
show("Detected Cards", original)
cv2.waitKey(0)
cv2.destroyAllWindows()