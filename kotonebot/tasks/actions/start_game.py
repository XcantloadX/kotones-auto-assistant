from kotonebot.backend.context import device

def start_game():
    """启动游戏"""
    device.launch_app("com.bandainamcoent.idolmaster_gakuen")

__actions__ = [start_game]