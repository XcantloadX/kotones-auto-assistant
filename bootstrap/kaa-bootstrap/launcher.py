import os
import sys
import logging
import importlib.metadata
import argparse
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime
from time import sleep
from typing import Optional, Literal

from meta import VERSION
from request import head, HTTPError, NetworkError
from terminal import (
    Color, print_header, print_status, clear_screen, wait_key
)
from repo import Version, PipPackage
from util import (
    is_admin,
    load_config_logic,
    get_update_settings_logic,
    ConfigLoadError,
    Config,
    restart_as_admin,
    run_command
)

# 获取当前Python解释器路径
PYTHON_EXECUTABLE = sys.executable
_TRUSTED_HOSTS = "pypi.org files.pythonhosted.org pypi.python.org mirrors.aliyun.com mirrors.cloud.tencent.com mirrors.tuna.tsinghua.edu.cn pypi.1ichika.de"
TRUSTED_HOSTS = [
    "pypi.org",
    "files.pythonhosted.org",
    "pypi.python.org",
    "mirrors.aliyun.com",
    "mirrors.cloud.tencent.com",
    "mirrors.tuna.tsinghua.edu.cn",
    "pypi.1ichika.de"
]
EXTRA_PIP_SERVER = "https://pypi.1ichika.de/simple"
PIP_SERVERS = [
    "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple",
    "https://mirrors.aliyun.com/pypi/simple",
    "https://mirrors.cloud.tencent.com/pypi/simple",
    "https://pypi.org/simple",
]
pip_ksaa: PipPackage = PipPackage("ksaa", execute_command=run_command)
pip_kotonebot: PipPackage = PipPackage("kotonebot", execute_command=run_command)

def setup_logging():
    """
    配置日志记录。
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    log_file = log_dir / f"bootstrap-{timestamp}.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d] %(message)s',
        filename=log_file,
        filemode='w',
        encoding='utf-8'
    )

    # 记录未捕获的异常
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.error("未捕获的异常", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
    logging.info("日志已初始化。")
    logging.info(f"Python 路径: {PYTHON_EXECUTABLE}")
    logging.info(f"Python 版本: {sys.version}")
    logging.info(f"启动器版本: {VERSION}")

def test_url_availability(url: str) -> bool:
    """
    测试URL是否可访问（返回200状态码）。
    
    :param url: 要测试的URL
    :type url: str
    :return: 如果URL可访问返回True，否则返回False
    :rtype: bool
    """
    try:
        with head(url, timeout=10) as response:
            return response.status_code == 200
    except (HTTPError, NetworkError):
        return False
    except Exception:
        return False

def get_working_pip_server() -> Optional[str]:
    """
    获取可用的pip服务器。
    
    :return: 第一个可用的pip服务器URL，如果都不可用返回None
    :rtype: Optional[str]
    """
    for server in PIP_SERVERS:
        msg = f"正在测试: {server}"
        print_status(msg, status='info', indent=1)
        logging.info(msg)
        if test_url_availability(server):
            msg = f"找到可用的pip服务器: {server}"
            print_status(msg, status='success', indent=1)
            logging.info(msg)
            return server
    msg = "所有pip服务器都不可用"
    print_status(msg, status='error')
    logging.error(msg)
    return None

def package_version(package_name: str) -> Optional[str]:
    """
    获取指定包的版本信息。
    
    :param package_name: 包名称
    :type package_name: str
    :return: 包版本字符串，如果包不存在则返回 None
    :rtype: Optional[str]
    
    :Example:
    
    .. code-block:: python
    
        >>> package_version("requests")
        '2.31.0'
        >>> package_version("nonexistent_package")
        None
    
    :raises: 无异常抛出，包不存在时返回 None
    """
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None

def get_ksaa_version_from_filesystem() -> Optional[str]:
    """
    通过文件系统检测 ksaa 版本信息。
    
    :return: ksaa 版本字符串，如果检测失败则返回 None
    :rtype: Optional[str]
    """
    try:
        # 查找 ksaa 包的安装路径
        import site
        import glob
        
        # 在 site-packages 中查找 ksaa-*.dist-info 目录
        for site_path in site.getsitepackages():
            site_path_obj = Path(site_path)
            
            # 使用 glob 查找匹配的 dist-info 目录
            dist_info_pattern = str(site_path_obj / "ksaa-*.dist-info")
            dist_info_dirs = glob.glob(dist_info_pattern)
            
            for dist_info_dir in dist_info_dirs:
                # 从目录名提取版本号
                # 例如: ksaa-2025.7.13.0.dist-info -> 2025.7.13.0
                dir_name = Path(dist_info_dir).name
                if dir_name.startswith("ksaa-") and dir_name.endswith(".dist-info"):
                    version = dir_name[5:-10]  # 去掉 "ksaa-" 前缀和 ".dist-info" 后缀
                    if version:
                        return version
        
        return None
        
    except Exception as e:
        logging.warning(f"通过文件系统检测 ksaa 版本失败: {e}")
        return None

def print_update_notice(current_version: str, latest_version: str):
    """
    打印更新提示信息。
    
    :param current_version: 当前版本
    :type current_version: str
    :param latest_version: 最新版本
    :type latest_version: str
    """
    clear_screen()
    print()
    print(f"{Color.YELLOW}{Color.BOLD}" + "=" * 60)
    print(f"{Color.YELLOW}{Color.BOLD}⚠️  发现新版本可用！")
    print(f"{Color.YELLOW}{Color.BOLD}" + "=" * 60)
    print(f"{Color.YELLOW}当前版本: {current_version}")
    print(f"{Color.YELLOW}最新版本: {latest_version}")
    print(f"{Color.YELLOW}建议开启自动更新或在设置中手动安装新版本。")
    print(f"{Color.YELLOW}5s 后继续启动")
    print(f"{Color.YELLOW}{Color.BOLD}" + "=" * 60 + f"{Color.RESET}")
    print()
    sleep(5)

def clean():
    print_status("卸载现有的琴音小助手", status='info')
    ret1 = pip_ksaa.uninstall()
    ret2 = pip_kotonebot.uninstall()
    if not ret1 or not ret2:
        user_input = input("卸载失败，是否继续安装？(直接回车继续，输入 q 退出)")
        if user_input == 'q':
            raise RuntimeError("卸载失败")

def install_ksaa_version(version: str) -> bool:
    """
    安装指定版本的ksaa包。

    :param pip_server: pip服务器URL
    :type pip_server: str
    :param trusted_hosts: 信任的主机列表
    :type trusted_hosts: str
    :param version: 要安装的版本号
    :type version: str
    :return: 安装是否成功
    :rtype: bool
    """
    clean()
    
    print_status(f"安装琴音小助手 v{version}", status='info')
    return pip_ksaa.install(version)

def install_ksaa_from_zip(zip_path: str) -> bool:
    """
    从zip文件安装ksaa包。

    :param zip_path: zip文件路径
    :type zip_path: str
    :return: 安装是否成功
    :rtype: bool
    """
    zip_file = Path(zip_path)
    if not zip_file.exists():
        msg = f"zip文件不存在: {zip_path}"
        print_status(msg, status='error')
        logging.error(msg)
        return False

    if not zip_file.suffix.lower() == '.zip':
        msg = f"文件不是zip格式: {zip_path}"
        print_status(msg, status='error')
        logging.error(msg)
        return False

    print_status(f"从zip文件安装琴音小助手: {zip_path}", status='info')

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        try:
            # 解压zip文件
            print_status("解压zip文件...", status='info', indent=1)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            # 先卸载 ksaa 和 kotonebot
            clean()

            print_status("安装ksaa包...", status='info', indent=1)
            return pip_ksaa.install_from_folder(str(temp_path.absolute()))

        except zipfile.BadZipFile:
            msg = f"无效的zip文件: {zip_path}"
            print_status(msg, status='error')
            logging.error(msg)
            return False
        except Exception as e:
            msg = f"从zip文件安装失败: {e}"
            print_status(msg, status='error')
            logging.error(msg, exc_info=True)
            return False


def install_ksaa_from_package(package_path: str) -> bool:
    """
    从 .whl 或 .tar.gz 文件安装ksaa包。

    :param package_path: .whl或.tar.gz文件路径
    :type package_path: str
    :return: 安装是否成功
    :rtype: bool
    """
    package_file = Path(package_path)
    if not package_file.exists():
        msg = f"包文件不存在: {package_path}"
        print_status(msg, status='error')
        logging.error(msg)
        return False

    suffix = package_file.suffix.lower()
    if not (suffix == '.whl' or package_path.lower().endswith('.tar.gz')):
        msg = f"文件不是 .whl 或 .tar.gz 格式: {package_path}"
        print_status(msg, status='error')
        logging.error(msg)
        return False
    clean()
    print_status(f"从包文件安装琴音小助手: {package_path}", status='info')
    return pip_ksaa.install_from_file(str(package_file.absolute()))

def install_pip_and_ksaa(pip_server: str, check_update: bool = True, install_update: bool = True, update_channel: Literal['release', 'beta'] = 'release') -> bool:
    """
    安装和更新pip以及ksaa包。

    :param pip_server: pip服务器URL
    :type pip_server: str
    :param check_update: 是否检查更新
    :type check_update: bool
    :param install_update: 是否安装更新
    :type install_update: bool
    :param update_channel: 更新通道（release 或 beta）。beta 将包含预发布版本。
    :type update_channel: Literal['release', 'beta']
    :return: 安装是否成功
    :rtype: bool
    """
    print_header("安装与更新小助手", color=Color.BLUE)

    # 升级pip
    if check_update:
        print_status("更新 pip", status='info')
        upgrade_pip_command = (
            f'"{PYTHON_EXECUTABLE}" -m pip install -i {pip_server} '
            f'--extra-index-url {EXTRA_PIP_SERVER} --trusted-host "{TRUSTED_HOSTS}" --upgrade pip'
        )
        if not run_command(upgrade_pip_command):
            return False

    # 检查更新
    pre_flag = update_channel == 'beta'
    local = pip_ksaa.local_version()
    latest = pip_ksaa.latest_version(pre=pre_flag)
    if not latest:
        msg = "获取最新版本失败，请检查网络连接。"
        print_status(msg, status='warning')
        logging.warning(msg)
        return False

    if not local:
        print_status("未安装琴音小助手，正在安装...", status='info')
        return pip_ksaa.install(str(latest))
    elif latest and local < latest:
        if not install_update:
            print_update_notice(str(local), str(latest))
            return True
    else:
        return True

    # 安装琴音小助手
    clean()
    print_status("安装琴音小助手", status='info')
    return pip_ksaa.install(str(latest))

def load_config() -> Optional[Config]:
    """
    加载config.json配置文件。
    
    :return: 配置字典，如果加载失败返回None
    """
    try:
        config = load_config_logic()
        msg = "成功加载配置文件"
        print_status(msg, status='success')
        logging.info(msg)
        return config
    except ConfigLoadError as e:
        msg = str(e)
        print_status(msg, status='error')
        logging.error(msg, exc_info=True)
        return None

def get_update_settings(config: Config) -> tuple[bool, bool, Literal['release', 'beta']]:
    """
    从配置中获取更新设置。
    
    :param config: 配置字典
    :type config: Config
    :return: (是否检查更新, 是否自动安装更新, 更新通道)
    :rtype: tuple[bool, bool, Literal['release', 'beta']]
    """
    check_update, auto_install_update, update_channel = get_update_settings_logic(config)
    msg = f"更新设置: 检查更新={check_update}, 自动安装={auto_install_update}, 更新通道={update_channel}"
    logging.info(msg)
    return check_update, auto_install_update, update_channel

def check_admin(config: Config) -> bool:
    """
    检查Windows截图权限（管理员权限）。
    
    :param config: 配置字典
    :type config: Config
    :return: 权限检查是否通过
    :rtype: bool
    """
    # 检查是否有用户配置
    user_configs = config.get("user_configs", [])
    if not user_configs:
        msg = "配置文件中没有用户配置"
        print_status(msg, status='warning')
        logging.warning(msg)
        return True # Not a fatal error, allow to continue
    
    # 检查第一个用户配置的截图方式
    first_config = user_configs[0]
    backend = first_config.get("backend", {})
    screenshot_impl = backend.get("screenshot_impl")
    
    if screenshot_impl == "windows":
        msg = "检测到Windows截图模式，检查管理员权限..."
        print_status(msg, status='info')
        logging.info(msg)
        if not is_admin():
            msg1 = "无管理员权限，正在尝试以管理员身份重启..."
            print_status(msg1, status='info')
            logging.info(msg1)
            
            restart_as_admin()
            return False
        else:
            msg = "管理员权限检查通过"
            print_status(msg, status='success')
            logging.info(msg)
    
    return True

def run_kaa(args: list[str]) -> bool:
    """
    运行琴音小助手。
    
    :return: 运行是否成功
    :rtype: bool
    """
    print_header("运行琴音小助手", color=Color.GREEN)
    clear_screen()
    
    # 设置环境变量
    os.environ["no_proxy"] = "localhost, 127.0.0.1, ::1"
    
    # 根据版本选择程序入口
    entry_point = "kaa.main.cli"
    
    # 检测 ksaa 版本（优先使用文件系统检测，失败时使用 pip 检测）
    detected_version = get_ksaa_version_from_filesystem() or package_version("ksaa")
    
    if detected_version:
        try:
            current_version = Version(detected_version)
            target_version = Version("2025.9b2")
            
            if current_version < target_version:
                entry_point = "kotonebot.kaa.main.cli"
            
            print_status(f"kaa 版本 {detected_version} {'<' if current_version < target_version else '>='} 25.9，使用入口点: {entry_point}", status='info')
            
        except Exception as e:
            print_status(f"版本比较失败: {e}，使用默认入口点: {entry_point}", status='warning')
            logging.warning(f"版本比较失败: {e}")
    else:
        print_status(f"无法检测到 ksaa 版本，使用默认入口点: {entry_point}", status='warning')
    
    # 运行kaa命令
    retcode, _ = run_command(f'"{PYTHON_EXECUTABLE}" -m {entry_point} {" ".join(args)}', verbatim=True, log_output=False)
    if retcode != 0:
        return False
    
    print_header("运行结束", color=Color.GREEN)
    return True

def recovery_mode():
    print_status("按任意键进入恢复流程...", status='info')
    wait_key()
    clear_screen()

    package_versions = pip_ksaa.list_versions()
    local = pip_ksaa.local_version()
    if not package_versions:
        print_status("没有找到可用的 ksaa 版本，请检查网络连接。", status='error')
        return False
    
    clear_screen()
    print_status("可用版本:", status='info')
    versions = [str(v.version) for v in package_versions]
    for i in range(0, len(versions), 3):
        print_status("  " + "\t\t".join(versions[i:i+3]), status='info', indent=1)
    print_status("当前版本:", status='info')
    print_status(f"  {local}", status='info', indent=1)
    
    while True:
        user_input = input("请输入要安装的版本号: ")

        if user_input in versions:
            print_status(f"正在安装版本 {user_input}...", status='info')
            pip_ksaa.install(user_input)
            print_status("安装成功，请重启 kaa", status='info')
            break
        else:
            print_status("版本不存在，请重新输入。", status='error')

def parse_arguments():
    """
    解析命令行参数。

    :return: 解析后的参数
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(description='琴音小助手启动器')
    parser.add_argument('package_file', nargs='?', help='要安装的包文件路径（.whl, .tar.gz, .zip）')
    parser.add_argument('--install-version', type=str, help='安装指定版本的 ksaa (例如: --install-version=1.2.3)')
    parser.add_argument('--install-from-zip', type=str, help='从 zip 文件安装 ksaa (例如: --install-from-zip=/path/to/file.zip)')
    parser.add_argument('--install-from-package', type=str, help='从 .whl 或 .tar.gz 文件安装 ksaa')
    parser.add_argument('--skip-update', action='store_true', help='跳过 pip 和 kaa 的检查更新')

    args, extra_args = parser.parse_known_args()
    args.extra_args = extra_args

    return args

def main_launch():
    """
    主启动函数，执行完整的安装和启动流程。
    """
    # 解析命令行参数
    args = parse_arguments()

    # 处理位置参数
    if args.package_file:
        lower_path = args.package_file.lower()
        if lower_path.endswith('.zip'):
            if not args.install_from_zip:
                args.install_from_zip = args.package_file
        elif lower_path.endswith('.whl') or lower_path.endswith('.tar.gz'):
            if not args.install_from_package:
                args.install_from_package = args.package_file
        else:
            raise ValueError(f"不支持的文件类型: {args.package_file}")

    setup_logging()
    run_command(f"title 琴音小助手启动器（运行时请勿关闭此窗口） v{VERSION}", verbatim=True, log_output=False)
    clear_screen()
    print_header("琴音小助手启动器")
    logging.info("启动器已启动。")

    try:
        # 1. 加载配置文件（提前加载以获取更新设置）
        print_header("加载配置", color=Color.BLUE)
        logging.info("加载配置。")
        config = load_config()

        # 2. 获取更新设置
        check_update, auto_install_update, update_channel = get_update_settings(config if config else {"version": 5, "user_configs": []})

        # 3. 如果指定了特殊安装参数或跳过更新，跳过更新检查
        if args.install_version or args.install_from_zip or args.install_from_package or args.skip_update:
            check_update = False
            auto_install_update = False
        
        # 4. 根据配置决定是否检查更新
        print_status("正在寻找最快的 PyPI 镜像源...", status='info')
        logging.info("正在寻找最快的 PyPI 镜像源...")
        pip_server = get_working_pip_server()
        if not pip_server:
            raise RuntimeError("没有找到可用的pip服务器，请检查网络连接。")
        pip_ksaa.server_url = pip_server
        pip_kotonebot.server_url = pip_server
        pip_ksaa.extra_index_urls = [EXTRA_PIP_SERVER]
        pip_kotonebot.extra_index_urls = [EXTRA_PIP_SERVER]
        pip_ksaa.trusted_hosts = TRUSTED_HOSTS
        pip_kotonebot.trusted_hosts = TRUSTED_HOSTS

        # 5. 处理特殊安装情况
        if args.install_from_zip:
            # 从zip文件安装
            print_header("安装补丁", color=Color.BLUE)
            if not install_ksaa_from_zip(args.install_from_zip):
                raise RuntimeError("从zip文件安装失败，请检查上面的错误日志。")
        elif args.install_from_package:
            # 从包文件安装
            print_header("安装补丁", color=Color.BLUE)
            if not install_ksaa_from_package(args.install_from_package):
                raise RuntimeError("从包文件安装失败，请检查上面的错误日志。")
        elif args.install_version:
            # 安装指定版本
            print_header("安装指定版本", color=Color.BLUE)
            if not install_ksaa_version(args.install_version):
                raise RuntimeError("安装指定版本失败，请检查上面的错误日志。")
        else:
            # 默认安装和更新逻辑
            if not install_pip_and_ksaa(pip_server, check_update, auto_install_update, update_channel):
                raise RuntimeError("依赖安装失败，请检查上面的错误日志。")

        # 6. 检查Windows截图权限
        if config:
            if not check_admin(config):
                raise RuntimeError("权限检查失败。")

        # 7. 运行琴音小助手
        if not run_kaa(args.extra_args):
            raise RuntimeError("琴音小助手主程序运行失败。")

        msg = "琴音小助手已退出。"
        print_status(msg, status='success')
        logging.info(msg)

    except Exception as e:
        msg = f"发生致命错误: {e}"
        print_status(msg, status='error')
        print_status("可尝试进入恢复流程，安装旧版本小助手", status='info')
        print_status("如需反馈，压缩 kaa 目录下的 logs 文件夹并给此窗口截图后一并发送给开发者", status='info')
        logging.critical(msg, exc_info=True)
        print()
        recovery_mode()
    finally:
        logging.info("启动器运行结束。")
        wait_key("\n按任意键退出...")

if __name__ == "__main__":
    try:
        main_launch()
    except KeyboardInterrupt:
        print_status("运行结束。现在可以安全关闭此窗口。", status='info')
