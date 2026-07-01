"""关闭游戏"""
import os
import sys
import logging
import _thread
import threading

from kotonebot.ui import user
from ..kaa_context import instance
from kaa.config import Priority, conf
from kaa.config.base_config import CustomDevice, DmmDevice
from kaa.constants import GAME_PACKAGE_NAME, PLAYCOVER_BUNDLE_ID
from kotonebot import task, action, device

logger = logging.getLogger(__name__)

@action('关闭游戏.Android', screenshot_mode='manual-inherit')
def android_close():
    """
    前置条件：-
    结束状态：游戏关闭
    """
    logger.info("Closing game")
    if device.current_package() == GAME_PACKAGE_NAME:
        logger.info("Force stopping game")
        device.adb.shell(f"am force-stop {GAME_PACKAGE_NAME}")

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

@action('关闭游戏.macOS', screenshot_mode='manual-inherit')
def macos_close():
    """
    前置条件：-
    结束状态：游戏关闭
    """
    from kotonebot.client.playcover import Playcover
    logger.info('Closing game')
    app = Playcover.find(PLAYCOVER_BUNDLE_ID)
    if app is None:
        logger.warning('PlayCover app not found: %s', PLAYCOVER_BUNDLE_ID)
        return
    if not app.running():
        logger.info('Game is not running')
        return
    app.terminate()
    logger.info('Game closed successfully')

@task('关闭游戏', priority=Priority.END_GAME, run_at='post')
def end_game():
    """
    游戏结束时执行的任务。
    """
    # 关闭游戏
    if conf().tasks.end_game.kill_game:
        if device.platform == 'android':
            android_close()
        elif device.platform == 'windows':
            windows_close()
        elif device.platform == 'macos':
            macos_close()
        else:
            raise ValueError(f'Unsupported platform: {device.platform}')

    # 关闭 DMM
    if conf().tasks.end_game.kill_dmm:
        logger.info("Closing DMM")
        os.system('taskkill /f /im DMMGamePlayer.exe')
        logger.info("DMM closed successfully")

    # 关闭模拟器
    if conf().tasks.end_game.kill_emulator:
        lc = conf().backend.lifecycle
        if not (isinstance(lc, (CustomDevice, DmmDevice)) and lc.emulator_path):
            user.warning('未配置模拟器 exe 文件路径，无法关闭模拟器。跳过此次操作。')
        else:
            instance().stop()

    # 恢复汉化插件
    if conf().tasks.end_game.restore_gakumas_localify:
        logger.info('Restoring Gakumas Localify...')
        game_path = conf().tasks.start_game.dmm_game_path
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
    if conf().tasks.end_game.shutdown:
        logger.info("Shutting down system")
        os.system('shutdown /s /t 60')
        logger.info("System will shut down in 60 seconds")

    # 休眠
    if conf().tasks.end_game.hibernate:
        logger.info("Hibernating system")
        os.system('shutdown /h')

    # 退出 kaa
    if conf().tasks.end_game.exit_kaa:
        logger.info("Exiting kaa")
        # kaa 不在主线程中运行，一般是以 GUI 运行
        if not threading.main_thread() is threading.current_thread():
            _thread.interrupt_main()
        sys.exit(0)

    logger.info("Game ended successfully")

if __name__ == '__main__':
    conf().tasks.end_game.kill_game = True
    conf().tasks.end_game.kill_dmm = True
    conf().tasks.end_game.kill_emulator = True
    end_game()