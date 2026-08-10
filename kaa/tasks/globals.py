import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kotonebot import Loop

from kotonebot import device
from kotonebot.backend.context.context import vars
from kaa.tasks import R

logger = logging.getLogger(__name__)


def handle_network_error() -> bool:
    """处理网络错误弹窗，若已处理则返回 True。

    前置：-\n
    结束：网络错误弹窗被关闭（点击重试按钮）\n

    目前覆盖两类弹窗：
    - 全屏「通信エラー」（常见于加载页），对应 `R.Common.TextNetworkError` 与 `R.Common.ButtonRetry`。
    - 培育内的「通信エラー」弹窗，对应 `R.CommonDialogs.NetworkError`。

    :return: 是否处理了网络错误弹窗。
    """
    # 无截图数据时跳过检测（例如 `Loop(auto_screenshot=False)` 之类未截图的上下文）
    if vars.screenshot_data is None:
        logger.debug('No screenshot data available, skipping network error check.')
        return False
    # 横屏下跳过检测
    if device.detect_orientation() == 'landscape':
        logger.debug('Landscape orientation detected, skipping network error handling.')
        return False
    # 全屏通信エラー（加载页等）
    if R.Common.TextNetworkError.exists():
        logger.info('Network error dialog found.')
        if btn_retry := R.Common.ButtonRetry.find():
            device.click(btn_retry)
            logger.info('Clicked retry button on network error dialog.')
            return True
    # 培育内通信エラー弹窗
    if R.CommonDialogs.NetworkError.Title.exists():
        logger.info('Network error popup found.')
        if btn_retry := R.CommonDialogs.NetworkError.ButtonRetry.find():
            device.click(btn_retry)
            logger.info('Clicked retry button on network error popup.')
            return True
    return False


def global_interrupt(loop: 'Loop') -> bool:
    """全局 Loop 回调：在每次 Loop 迭代前处理网络错误等全局弹窗。

    作为 `conf().loop.loop_callbacks` 的成员被 `Loop.tick()` 调用。
    返回 True 表示已处理某个弹窗，框架会重新截图并再次调用本回调，
    直到所有弹窗都被关闭为止。

    :param loop: 当前正在执行的 Loop。
    :return: 是否处理了弹窗。
    """
    try:
        if handle_network_error():
            return True
    except Exception:
        logger.exception('Error while handling global interrupt: %s')
        return False
    return False
