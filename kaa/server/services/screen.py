"""
Screen RPC 服务
处理屏幕抓取和实时推送
"""
import logging
import asyncio
import base64
from typing import Optional
import cv2
import numpy as np

from ..rpc import registry
from ..events import notify, Topics
from ..adapters.kaa_runtime import get_runtime

logger = logging.getLogger(__name__)

# 订阅者计数
_subscribers = 0
_subscription_task: Optional[asyncio.Task] = None
_subscription_interval = 1000  # 默认1秒


@registry.decorator('screen.grab')
async def screen_grab():
    """抓取一次屏幕"""
    try:
        runtime = get_runtime()
        from kotonebot import device
        
        # 抓取屏幕
        screenshot = device.screenshot()
        
        # BGR -> RGB
        screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        
        # 编码为 JPEG
        _, buffer = cv2.imencode('.jpg', screenshot_rgb, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        # Base64 编码
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {"image": image_base64}
    
    except Exception as e:
        logger.error(f"Error grabbing screen: {e}")
        raise


@registry.decorator('screen.subscribe')
async def screen_subscribe(intervalMs: int = 1000):
    """订阅屏幕推送"""
    global _subscribers, _subscription_task, _subscription_interval
    
    _subscribers += 1
    _subscription_interval = intervalMs
    
    logger.info(f"Screen subscriber added (total: {_subscribers})")
    
    # 如果还没有订阅任务，启动它
    if _subscription_task is None:
        _subscription_task = asyncio.create_task(_screen_push_loop())
    
    return {"success": True, "subscribers": _subscribers}


@registry.decorator('screen.unsubscribe')
async def screen_unsubscribe():
    """取消订阅屏幕推送"""
    global _subscribers, _subscription_task
    
    if _subscribers > 0:
        _subscribers -= 1
    
    logger.info(f"Screen subscriber removed (total: {_subscribers})")
    
    # 如果没有订阅者了，停止推送任务
    if _subscribers == 0 and _subscription_task is not None:
        _subscription_task.cancel()
        try:
            await _subscription_task
        except asyncio.CancelledError:
            pass
        _subscription_task = None
    
    return {"success": True, "subscribers": _subscribers}


async def _screen_push_loop():
    """屏幕推送循环"""
    global _subscribers, _subscription_interval
    
    try:
        while _subscribers > 0:
            try:
                # 抓取并推送
                from kotonebot import device
                screenshot = device.screenshot()
                
                # BGR -> RGB
                screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
                
                # 编码为 JPEG
                _, buffer = cv2.imencode('.jpg', screenshot_rgb, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                # Base64 编码
                image_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # 推送到客户端
                await notify(Topics.SCREEN_FRAME, {"image": image_base64})
                
                # 等待指定间隔
                await asyncio.sleep(_subscription_interval / 1000.0)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in screen push loop: {e}")
                await asyncio.sleep(1)  # 出错时等待1秒
    
    finally:
        logger.info("Screen push loop stopped")

