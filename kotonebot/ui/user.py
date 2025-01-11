"""消息框、通知、推送等 UI 相关函数"""

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

def warning(
    message: str,
    once: bool = False
):
    """
    警告信息。

    :param message: 消息内容
    :param once: 每次运行是否只显示一次。
    """
    pass
