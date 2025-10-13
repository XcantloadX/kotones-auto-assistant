"""
事件发布器，用于向客户端推送通知
"""
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)

# 全局 Socket.IO 实例引用
_sio = None


def set_sio(sio):
    """设置 Socket.IO 实例"""
    global _sio
    _sio = sio


async def notify(topic: str, data: Any):
    """发送通知到所有连接的客户端"""
    if _sio is None:
        logger.warning(f"SIO not initialized, cannot send notify: {topic}")
        return
    
    from .models import RPCNotify
    
    notify_msg = RPCNotify(
        topic=topic,
        data=data,
        ts=int(time.time() * 1000)
    )
    
    await _sio.emit('rpc/notify', notify_msg.model_dump())
    logger.debug(f"Sent notify: {topic}")


async def stream(id: str, event: str, data: Any = None, progress: dict[str, int] = None):
    """发送流式响应"""
    if _sio is None:
        logger.warning(f"SIO not initialized, cannot send stream: {id}")
        return
    
    from .models import RPCStream
    
    stream_msg = RPCStream(
        id=id,
        event=event,
        data=data,
        progress=progress
    )
    
    await _sio.emit('rpc/stream', stream_msg.model_dump())
    logger.debug(f"Sent stream: {id} - {event}")


# 事件主题常量
class Topics:
    STATUS_RUN = "status/run"
    STATUS_TASK = "status/task"
    SCREEN_FRAME = "screen/frame"

