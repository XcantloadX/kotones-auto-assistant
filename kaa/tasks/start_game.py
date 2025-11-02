"""启动游戏，领取登录奖励，直到首页为止"""
import os
import re
import json
import ctypes
import logging
import subprocess

from kotonebot.util import Countdown
from kotonebot.backend.loop import Loop
from kotonebot import task, action, sleep, device, image, ocr, config
from kotonebot.backend.context.context import vars

from kaa.tasks import R
from .actions.loading import loading
from kaa.config import Priority, conf
from .actions.scenes import at_home, goto_home
from .actions.commu import handle_unread_commu
from kaa.errors import ElevationRequiredError, GameUpdateNeededError, DmmGameLaunchError

logger = logging.getLogger(__name__)

def locate_game_path() -> str | None:
    """自动获取 DMM 版游戏路径。"""
    logger.info('Locating DMM game path...')
    app_data = os.getenv('APPDATA')
    if not app_data:
        logger.info('APPDATA not found. Location failed.')
        return None
    dmm_config_path = os.path.join(app_data, 'dmmgameplayer5', 'dmmgame.cnf')
    if not os.path.exists(dmm_config_path):
        logger.warning('DMM config does not exist. Location failed.')
        return None
    with open(dmm_config_path, 'r', encoding='utf-8') as f:
        dmm_config = json.load(f)
    for content in dmm_config.get('contents', []):
        if content.get('productId') == 'gakumas':
            game_path = content.get('detail', {}).get('path')
            if game_path:
                break
    else:
        logger.warning('Game "gakumas" not found in DMM config.')
        return None
    logger.info(f'Game path: {game_path}')
    if game_path:
        game_path = os.path.join(game_path, 'gakumas.exe')
    if game_path and not conf().start_game.dmm_game_path:
        logger.info('Saving game path to config...')
        conf().start_game.dmm_game_path = game_path
        config.save()
    return game_path

def start_windows_bypass():
    """
    绕过 DMMPlayer 直接启动游戏。
    """
    appdata = os.getenv('APPDATA')
    if not appdata:
        raise DmmGameLaunchError('APPDATA not found.')
    log_path = os.path.join(appdata, 'dmmgameplayer5', 'logs', 'dll.log')

    if not os.path.exists(log_path):
        raise DmmGameLaunchError(f'DMMGamePlayer log file not found at {log_path}')

    last_launch_line = None
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "Execute of:: gakumas exe" in line:
                last_launch_line = line

    if not last_launch_line:
        raise DmmGameLaunchError('Could not find any run records for "Gakumas" in the DMM log. Please launch the game normally once through the DMM client.')

    regex = r'exe:\s*(?P<exe_path>.*?gakumas\.exe).*?/viewer_id=(?P<viewer_id>[^\s]+).*?/open_id=(?P<open_id>[^\s]+).*?/pf_access_token=(?P<pf_token>[^\s]+)'
    match = re.search(regex, last_launch_line)

    if not match:
        raise DmmGameLaunchError('Failed to extract complete launch information from the log. The log format may have changed.')

    game_info = match.groupdict()
    exe_path = game_info['exe_path']
    working_dir = os.path.dirname(exe_path)
    args = [
        exe_path,
        f"/viewer_id={game_info['viewer_id']}",
        f"/open_id={game_info['open_id']}",
        f"/pf_access_token={game_info['pf_token']}"
    ]

    try:
        # CREATE_NO_WINDOW to avoid console popup
        subprocess.Popen(args, cwd=working_dir, creationflags=0x08000000)
    except Exception as e:
        raise DmmGameLaunchError(f'Failed to start the game directly: {e}')

# TODO: 这个函数功能和 kaa\tasks\actions\scenes.py 中的 goto_home 重复了，后续需要合并
@action('启动游戏.进入首页', screenshot_mode='manual-inherit')
def wait_for_home():
    """
    前置条件：游戏已启动\n
    结束状态：游戏首页
    """
    logger.info('Entering home...')
    click_cd = Countdown(1).start()
    should_click = False
    for _ in Loop():
        logger.info('尝试进入/返回主页中...')
        # 首页
        if image.find(R.Daily.ButtonHomeCurrent):
            break
        # TAP TO START 画面
        # [screenshots/startup/1.png]
        elif image.find(R.Daily.ButonLinkData):
            should_click = True
        elif loading():
            pass
        # 热更新
        # [screenshots/startup/update.png]
        elif image.find(R.Common.TextGameUpdate) and image.find(R.Common.ButtonConfirm):
            device.click()
        # 本体更新
        # [kotonebot-resource/sprites/jp/daily/screenshot_apk_update.png]
        elif ocr.find('アップデート', rect=R.Daily.BoxApkUpdateDialogTitle):
            raise GameUpdateNeededError()
        # 公告
        # [screenshots/startup/announcement1.png]
        elif image.find(R.Common.ButtonIconClose):
            device.click()
        # 生日
        # [screenshots/startup/birthday.png]
        elif handle_unread_commu():
            pass
        # 如果已经进入游戏，但是在其他页面，也尝试跳转回主页面
        # 左下角是否有 Home 图标
        elif image.find(R.Common.ButtonToolbarHome):
            device.click()
        elif image.find(R.Common.ButtonHome):
            device.click()

        if should_click and click_cd.expired():
            device.click(10, 10)
            click_cd.reset()

@action('启动游戏.Android', screenshot_mode='manual-inherit')
def android_launch():
    """
    前置条件：-
    结束状态：-
    """
    _device = device.of_android()
    # 如果已经在游戏中，直接返回home
    if _device.current_package() == conf().start_game.game_package_name:
        logger.info("Game already started")
        if not at_home():
            logger.info("Not at home, going to home")
            goto_home()
        return
    
    # 如果不在游戏中，启动游戏
    if not conf().start_game.start_through_kuyo:
        # 直接启动
        _device.launch_app(conf().start_game.game_package_name)
    else:
        # 通过Kuyo启动
        if _device.current_package() == conf().start_game.kuyo_package_name:
            logger.warning("Kuyo already started. Auto start game failed.")
            # TODO: Kuyo支持改进
            return
        # 启动kuyo
        _device.launch_app('org.kuyo.game')
        # 点击"加速"
        device.click(image.expect_wait(R.Kuyo.ButtonTab3Speedup, timeout=10))
        # Kuyo会延迟加入广告，导致识别后，原位置突然弹出广告，导致进入广告页面
        sleep(2)
        # 点击"K空间启动"
        device.click(image.expect_wait(R.Kuyo.ButtonStartGame, timeout=10))

@action('启动游戏.Windows', screenshot_mode='manual-inherit')
def windows_launch():
    """
    前置条件：-
    结束状态：游戏窗口出现
    """
    # 检查管理员权限
    # TODO: 检查截图类型不应该依赖配置文件，而是直接检查 device 实例
    if config.current.backend.screenshot_impl == 'remote_windows':
        raise NotImplementedError("Task `start_game` is not supported on remote_windows.")
    try:
        is_admin = os.getuid() == 0 # type: ignore
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    if not is_admin:
        raise ElevationRequiredError()
    
    # 处理汉化插件
    if conf().start_game.disable_gakumas_localify:
        logger.info('Disabling Gakumas Localify...')
        game_path = conf().start_game.dmm_game_path or locate_game_path()
        logger.debug('Game path: %s', game_path)
        if not game_path:
            raise ValueError('dmm_game_path unset and auto-locate failed.')
        
        plugin_path = os.path.join(os.path.dirname(game_path), 'version.dll')
        logger.debug('Plugin path: %s', plugin_path)
        if not os.path.exists(plugin_path):
            logger.warning('Gakumas Localify not found. Skipped disable.')
        else:
            os.rename(plugin_path, plugin_path + '.disabled')
            logger.info('Gakumas Localify disabled.')
    
    from ahk import AHK
    from kaa.util.paths import get_ahk_path
    ahk_path = get_ahk_path()
    ahk = AHK(executable_path=ahk_path)

    if ahk.find_window(title='gakumas', title_match_mode=3): # 3=精确匹配
        logger.debug('Game already started.')
        return
    
    for _ in [1]:
        if conf().start_game.dmm_bypass:
            logger.info('Bypassing DMM launcher to start game directly...')
            try:
                start_windows_bypass()
                break
            except DmmGameLaunchError:
                logger.exception('Failed to bypass DMM launcher, fallback to DMM launcher...')
        
        logger.info('Starting game via DMM launcher...')
        os.startfile('dmmgameplayer://play/GCL/gakumas/cl/win')
    
    # 等待游戏窗口出现
    for _ in Loop(auto_screenshot=False):
        if ahk.find_window(title='gakumas', title_match_mode=3):
            logger.debug('Game window found.')
            break
        logger.debug('Waiting for game window...')

@task('启动游戏', priority=Priority.START_GAME)
def start_game():
    """
    启动游戏，直到游戏进入首页为止。
    """
    if not conf().start_game.enabled:
        logger.info('"Start game" is disabled.')
        return
    
    if device.platform == 'android':
        android_launch()
    elif device.platform == 'windows':
        windows_launch()
    else:
        raise ValueError(f'Unsupported platform: {device.platform}')

    wait_for_home()

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    start_game()

