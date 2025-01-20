"""消息框、通知、推送等 UI 相关函数"""
import logging
from typing import Callable

from cv2.typing import MatLike

logger = logging.getLogger(__name__)

def ask(
    question: str,
    options: list[str],
    *,
    timeout: float = -1,
) -> bool:
    """
    询问用户
    """
    raise NotImplementedError

def info(
    message: str,
    images: list[MatLike],
    *,
    once: bool = False
):
    """
    信息
    """
    logger.debug('user.info: %s', message)

def warning(
    message: str,
    images: list[MatLike],
    *,
    once: bool = False
):
    """
    警告信息。

    :param message: 消息内容
    :param once: 每次运行是否只显示一次。
    """
    logger.warning('user.warning: %s', message)
