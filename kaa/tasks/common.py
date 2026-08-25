from kotonebot import device

def skip():
    """点击游戏空白区域。用于跳过动画。"""
    device.click(12, 12, log='verbose')