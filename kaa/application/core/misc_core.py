import os
import sys

from kotonebot.interop.win.shortcut import create_shortcut
from kaa.errors import LauncherNotFoundError


def create_desktop_shortcut(start_immediately: bool):
    exe_path = os.path.abspath('./kaa.exe')
    if not os.path.exists(exe_path):
        raise LauncherNotFoundError()

    icon_paths = ['./kaa.exe', './kaa.ico']
    icon_path = next((os.path.abspath(p) for p in icon_paths if os.path.exists(p)), '')

    if start_immediately:
        create_shortcut(
            target_file=exe_path,
            target_args='--start-immidiately',
            link_file=None,  # Creates on desktop
            link_name='琴音小助手（快捷启动）',
            icon_path=icon_path,
            description='启动琴音小助手并立即运行任务'
        )
    else:
        create_shortcut(
            target_file=exe_path,
            target_args='',
            link_file=None,  # Creates on desktop
            link_name='琴音小助手',
            icon_path=icon_path,
            description='启动琴音小助手'
        )
