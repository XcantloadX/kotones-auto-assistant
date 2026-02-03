from kotonebot.interop.win import Win32Window

class InstantService:
    def __init__(self):
        pass

    def reset_game_window(self):
        window = Win32Window.find_window('title', 'gakumas')
        if not window:
            return False
        window.set_position(50, 50)
        window.bring_foreground()
        return True