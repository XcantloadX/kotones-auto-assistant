import cv2
import numpy as np

def cv_imread(filePath):
    cv_img=cv2.imdecode(np.fromfile(filePath,dtype=np.uint8),-1)
    ## imdecode读取的是rgb，如果后续需要opencv处理的话，需要转换成bgr，转换后图片颜色会变化
    ##cv_img=cv2.cvtColor(cv_img,cv2.COLOR_RGB2BGR)
    return cv_img

VERTICAL_BOX_COUNT = 12
HORIZONTAL_BOX_COUNT = 10
LINE_WIDTH = 2
FONT_SIZE = 1.2
FONT_STROKE_WIDTH = 3
COLOR = (0, 255, 0)

def draw_grid_with_numbers(image_path, output_path):
    # 读取图像
    img = cv_imread(image_path)
    height, width = img.shape[:2]
    
    # 计算网格大小
    grid_height = height // VERTICAL_BOX_COUNT
    grid_width = width // HORIZONTAL_BOX_COUNT
    
    # 画垂直线
    for i in range(HORIZONTAL_BOX_COUNT + 1):
        x = i * grid_width
        cv2.line(img, (x, 0), (x, height), COLOR, LINE_WIDTH)
    
    # 画水平线
    for i in range(VERTICAL_BOX_COUNT + 1):
        y = i * grid_height
        cv2.line(img, (0, y), (width, y), COLOR, LINE_WIDTH)
    
    # 在每个网格中添加编号
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = FONT_SIZE
    number = 0
    
    for i in range(VERTICAL_BOX_COUNT):
        for j in range(HORIZONTAL_BOX_COUNT):
            x = j * grid_width + grid_width // 2
            y = i * grid_height + grid_height // 2
            
            # 获取文本大小以居中显示
            text = str(number)
            (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, 1)
            text_x = int(x - text_width // 2)
            text_y = int(y + text_height // 2)
            
            cv2.putText(img, text, (text_x, text_y), font, font_scale, COLOR, FONT_STROKE_WIDTH)
            number += 1
    
    # 保存图像
    cv2.imwrite(output_path, img)
    return img

# 使用示例
image_path = r"C:\Users\ZhouXiaokang\Documents\MuMu共享文件夹\Screenshots\MuMu12-20250105-100943.png"
# 复制原图为 ai_grid_original.jpg
import shutil
shutil.copy(image_path, "ai_grid_original.jpg")

output_path = "ai_grid_pre_process.jpg"
result = draw_grid_with_numbers(image_path, output_path)
