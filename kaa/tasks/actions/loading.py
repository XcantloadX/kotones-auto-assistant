import time
from logging import getLogger

import cv2
import numpy as np

from kotonebot import device, action, sleep
from kotonebot.backend.debug import result
from kaa.tasks import R

logger = getLogger(__name__)

@action('检测加载页面', screenshot_mode='manual')
def loading() -> bool:
    """检测是否在场景加载页面"""
    img = device.screenshot()
    original_img = img.copy()
    # 二值化图片
    _, img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    # 裁剪上面 35%
    img = img[:int(img.shape[0] * 0.35), :]
    # 判断图片中颜色数量是否 <= 2
    # https://stackoverflow.com/questions/56606294/count-number-of-unique-colours-in-image
    b,g,r = cv2.split(img)
    shiftet_im = b.astype(np.int64) + 1000 * (g.astype(np.int64) + 1) + 1000 * 1000 * (r.astype(np.int64) + 1)
    ret = len(np.unique(shiftet_im)) <= 2
    result('tasks.actions.loading', [img, original_img], f'result={ret}')
    return ret

@action('等待加载开始')
def wait_loading_start(timeout: float = 60):
    """等待加载开始"""
    start_time = time.time()
    while not loading():
        if time.time() - start_time > timeout:
            raise TimeoutError('加载超时')
        logger.debug('Not loading...')
        sleep(1)

@action('等待加载结束')
def wait_loading_end(timeout: float = 60):
    """等待加载结束"""
    start_time = time.time()
    while loading():
        if time.time() - start_time > timeout:
            raise TimeoutError('加载超时')
        # 检查网络错误
        if R.Common.TextNetworkError.exists():
            R.Common.ButtonRetry.click()
        logger.debug('Loading...')
        sleep(1)

if __name__ == '__main__':
    print(loading())
    input()
