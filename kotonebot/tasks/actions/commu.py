"""检测与跳过交流"""
import logging

from cv2.typing import MatLike

from .. import R
from kotonebot import device, image, color, user, rect_expand, until, action, sleep

logger = logging.getLogger(__name__)

@action('检查是否处于交流')
def is_at_commu():
    return image.find(R.Common.ButtonCommuFastforward) is not None

@action('跳过交流')
def skip_commu():
    device.click(image.expect_wait(R.Common.ButtonCommuSkip))

@action('检查并跳过交流')
def check_and_skip_commu(img: MatLike | None = None) -> bool:
    """
    检查当前是否处在未读交流，并自动跳过。

    :param img: 截图。
    :return: 是否跳过了交流。
    """
    ret = False
    logger.info('Check and skip commu')
    if img is None:
        img = device.screenshot()
    skip_btn = image.find(R.Common.ButtonCommuFastforward)
    if skip_btn is None:
        logger.info('No fast forward button found. Not at a commu.')
        return ret
    
    ret = True
    logger.debug('Fast forward button found. Check commu')
    button_bg_rect = rect_expand(skip_btn.rect, 10, 10, 50, 10)
    colors = color.raw().dominant_color(img, 2, rect=button_bg_rect)
    RANGE = ((20, 65, 95), (180, 100, 100))
    if not any(color.raw().in_range(c, RANGE) for c in colors):
        user.info('发现未读交流', [img])
        logger.debug('Not fast forwarding. Click fast forward button')
        device.click(skip_btn)
        sleep(0.7)
        if image.find(R.Common.ButtonConfirm):
            logger.debug('Click confirm button')
            device.click()
    else:
        logger.info('Fast forwarding. No action needed.')
    logger.debug('Wait until not at commu')
    until(lambda: not is_at_commu(), interval=1)
    logger.info('Fast forward done')

    return ret


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    print(is_at_commu())
    # rect = image.expect(R.Common.ButtonCommuFastforward).rect
    # print(rect)
    # rect = rect_expand(rect, 10, 10, 50, 10)
    # print(rect)
    # img = device.screenshot()
    # print(color.raw().dominant_color(img, 2, rect=rect))
    # skip_commu()
    # check_and_skip_commu()
