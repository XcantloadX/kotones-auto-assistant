import time
from time import sleep

import cv2
import numpy as np

from kotonebot import image, device, debug

def loading() -> bool:
    """检测是否在场景加载页面"""
    img = device.screenshot()
    # 二值化图片
    _, img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    debug.show(img)
    # 裁剪上面 10%
    img = img[:int(img.shape[0] * 0.1), :]
    debug.show(img)
    # 判断图片中颜色数量是否 <= 2
    # https://stackoverflow.com/questions/56606294/count-number-of-unique-colours-in-image
    b,g,r = cv2.split(img)
    shiftet_im = b.astype(np.int64) + 1000 * (g.astype(np.int64) + 1) + 1000 * 1000 * (r.astype(np.int64) + 1)
    return len(np.unique(shiftet_im)) <= 2

def wait_loading_start(timeout: float = 10):
    """等待加载开始"""
    start_time = time.time()
    while not loading():
        if time.time() - start_time > timeout:
            raise TimeoutError('加载超时')
        sleep(0.5)

def wait_loading_end(timeout: float = 10):
    """等待加载结束"""
    start_time = time.time()
    while loading():
        if time.time() - start_time > timeout:
            raise TimeoutError('加载超时')
        sleep(0.5)

if __name__ == '__main__':
    print(loading())
    input()
