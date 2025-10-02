"""关闭游戏"""
import os
import sys
import logging
import _thread
import threading

from kotonebot.backend.bot import PostTaskContext
from kotonebot.ui import user
from ..kaa_context import instance
from kaa.config import Priority, conf
from kotonebot import task, action, config, device

logger = logging.getLogger(__name__)

@action('关闭游戏.Android', screenshot_mode='manual-inherit')
def android_close():
    """
    前置条件：-
    结束状态：游戏关闭
    """
    logger.info("Closing game")
    if device.current_package() == conf().start_game.game_package_name:
        logger.info("Force stopping game")
        device.adb.shell(f"am force-stop {conf().start_game.game_package_name}")

    logger.info("Game closed successfully")

@action('关闭游戏.Windows', screenshot_mode='manual-inherit')
def windows_close():
    """
    前置条件：-
    结束状态：游戏关闭
    """
    logger.info("Closing game")
    os.system('taskkill /f /im gakumas.exe')
    logger.info("Game closed successfully")

@task('关闭游戏', priority=Priority.END_GAME, run_at='post')
def end_game(ctx: PostTaskContext):
    """
    游戏结束时执行的任务。
    """
    # 关闭游戏
    if conf().end_game.kill_game:
        if device.platform == 'android':
            android_close()
        elif device.platform == 'windows':
            windows_close()
        else:
            raise ValueError(f'Unsupported platform: {device.platform}')

    # 关闭 DMM
    if conf().end_game.kill_dmm:
        logger.info("Closing DMM")
        os.system('taskkill /f /im DMMGamePlayer.exe')
        logger.info("DMM closed successfully")

    # 关闭模拟器
    if conf().end_game.kill_emulator:
        if not config.current.backend.emulator_path:
            user.warning('未配置模拟器 exe 文件路径，无法关闭模拟器。跳过此次操作。')
        else:
            instance().stop()

    # 恢复汉化插件
    if conf().end_game.restore_gakumas_localify:
        logger.info('Restoring Gakumas Localify...')
        game_path = conf().start_game.dmm_game_path
        if not game_path:
            # user.info
            raise ValueError('dmm_game_path unset.')
        plugin_path = os.path.join(os.path.dirname(game_path), 'version.dll')
        if not os.path.exists(plugin_path + '.disabled'):
            logger.warning('Disabled Gakumas Localify not found. Skipped restore.')
        else:
            os.rename(plugin_path + '.disabled', plugin_path)
            logger.info('Gakumas Localify restored.')

    # 关机
    if conf().end_game.shutdown:
        logger.info("Shutting down system")
        os.system('shutdown /s /t 60')
        logger.info("System will shut down in 60 seconds")

    # 休眠
    if conf().end_game.hibernate:
        logger.info("Hibernating system")
        os.system('shutdown /h')

    # 退出 kaa
    if conf().end_game.exit_kaa:
        logger.info("Exiting kaa")
        # kaa 不在主线程中运行，一般是以 GUI 运行
        if not threading.main_thread() is threading.current_thread():
            _thread.interrupt_main()
        sys.exit(0)

    logger.info("Game ended successfully")

if __name__ == '__main__':
    conf().end_game.kill_game = True
    conf().end_game.kill_dmm = True
    conf().end_game.kill_emulator = True
    end_game(PostTaskContext(False, None))