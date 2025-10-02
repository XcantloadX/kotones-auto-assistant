import logging

from kaa.tasks import R
from kotonebot import device, image

logger = logging.getLogger(__name__)

def expect_yes(*, msg: str | None = None):
    """
    点击对话框上的✔️按钮。若不存在，会等待其出现，直至超时异常。
    
    前置条件：当前打开了任意对话框\n
    结束状态：点击了肯定意义按钮（✔️图标，橙色背景）后瞬间

    :param msg: 成功点击后输出的日志信息。信息中的动词建议使用过去式。
    """
    device.click(image.expect(R.Common.IconButtonCheck))
    if msg is not None:
        logger.debug(msg)

def yes(*, msg: str | None = None) -> bool:
    """
    点击对话框上的✔️按钮。

    前置条件：当前打开了任意对话框\n
    结束状态：点击了肯定意义按钮（✔️图标，橙色背景）后瞬间

    :param msg: 成功点击后输出的日志信息。信息中的动词建议使用过去式。
    """
    if image.find(R.Common.IconButtonCheck):
        device.click()
        if msg is not None:
            logger.debug(msg)
        return True
    return False

def expect_no(*, msg: str | None = None):
    """
    点击对话框上的✖️按钮。若不存在，会等待其出现，直至超时异常。
    
    前置条件：当前打开了任意对话框\n
    结束状态：点击了否定意义按钮（✖️图标，白色背景）后瞬间

    :param msg: 成功点击后输出的日志信息。信息中的动词建议使用过去式。
    """
    device.click(image.expect(R.Common.IconButtonCross))
    if msg is not None:
        logger.debug(msg)

def no(*, msg: str | None = None):
    """
    点击对话框上的✖️按钮。

    前置条件：当前打开了任意对话框\n
    结束状态：点击了否定意义按钮（✖️图标，白色背景）后瞬间

    :param msg: 成功点击后输出的日志信息。信息中的动词建议使用过去式。
    """
    if image.find(R.Common.IconButtonCross):
        device.click()
        if msg is not None:
            logger.debug(msg)
        return True
    return False

__all__ = ['yes', 'no', 'expect_yes', 'expect_no']
