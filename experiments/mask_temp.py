import cv2
import numpy as np

# 读取图像
template = cv2.imread('tests/images/pdorinku.png')
mask = cv2.imread('test_mask.png')
image = cv2.imread('tests/images/acquire_pdorinku.png')

# 打印大小
print(template.shape)
print(mask.shape)
print(image.shape)

# 将掩码二值化
# mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)[1]
# 反转
# 转换掩码为单通道灰度图
mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
# mask = cv2.bitwise_not(mask)
cv2.imshow('mask', mask)



# 展示 masked 模板
# 确保掩码和模板大小一致
# mask = cv2.resize(mask, (template.shape[1], template.shape[0]))
masked_template = cv2.bitwise_and(template, template, mask=mask)
cv2.imshow('masked_template', masked_template)

# 模板匹配
result = cv2.matchTemplate(image, template, cv2.TM_CCORR_NORMED, mask=mask)
cv2.imshow('result', result)
# 获取最佳匹配位置
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

# 获取模板尺寸
h, w = template.shape[:2]

# 在原图上绘制矩形标注结果
top_left = max_loc
bottom_right = (top_left[0] + w, top_left[1] + h)
cv2.rectangle(image, top_left, bottom_right, (0, 0, 255), 2)

# 显示结果
# 缩放 1/2
image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
cv2.imshow('Result', image)
cv2.waitKey(0)
cv2.destroyAllWindows()
