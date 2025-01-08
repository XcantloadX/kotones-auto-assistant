import cv2
import numpy as np

# 读取图像
# image = cv2.imread(r"C:\Users\ZhouXiaokang\Downloads\Snipaste_2024-12-26_10-11-58.png")
# image = cv2.imread(r"C:\Users\ZhouXiaokang\Downloads\1735194517471.jpg")
image = cv2.imread(r"C:\Users\ZhouXiaokang\Downloads\1735195113729.jpg")
original = image.copy()

# 转换为 HSV 色彩空间
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# 定义黄色的 HSV 阈值
lower_yellow = np.array([20, 100, 100])
upper_yellow = np.array([60, 255, 255])


# 使用遮罩作为二值图像
binary = cv2.threshold(original, 220, 255, cv2.THRESH_BINARY)[1]

# 创建遮罩，提取黄色区域
mask = cv2.inRange(cv2.cvtColor(binary, cv2.COLOR_BGR2HSV), lower_yellow, upper_yellow)

# 获取图像高度和宽度
height, width = image.shape[:2]

# 计算每个区域的宽度
region_width = width // 3

# 创建三个区域的遮罩
regions = []
yellow_pixels = []

for i in range(3):
    start_x = i * region_width
    end_x = (i + 1) * region_width
    region_mask = mask[:, start_x:end_x]
    regions.append(region_mask)
    yellow_pixels.append(cv2.countNonZero(region_mask))

# 找出黄色像素最多的区域
max_yellow_region = yellow_pixels.index(max(yellow_pixels))

# 截取对应区域的原图
start_x = max_yellow_region * region_width
end_x = (max_yellow_region + 1) * region_width
cropped_image = original[:, start_x:end_x]

# 显示含黄色最多的区域
cv2.imshow("Region with most yellow", cropped_image)

# 打印每个区域的黄色像素数量
for i, count in enumerate(yellow_pixels):
    print(f"Region {i + 1}: {count} yellow pixels")

# 判断是否存在突出区域
max_count = max(yellow_pixels)
avg_count = sum(yellow_pixels) / len(yellow_pixels)
if max_count > avg_count * 1.5:  # 如果最大值超过平均值的1.5倍
    print(f"Region {yellow_pixels.index(max_count) + 1} has significantly more yellow pixels")
else:
    print("No region has significantly more yellow pixels")

# 显示结果
cv2.imshow("Yellow Mask", mask)
cv2.imshow("Binary", binary)
cv2.waitKey(0)
