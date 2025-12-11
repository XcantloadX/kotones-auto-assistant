import json
import locale
import logging
import os
import subprocess
import sys
import ctypes
import threading
from pathlib import Path
from typing import Dict, Any, TypedDict, Literal, List

from terminal import print_status

class BackendConfig(TypedDict, total=False):
    type: Literal['custom', 'mumu12', 'leidian', 'dmm']
    screenshot_impl: Literal['adb', 'adb_raw', 'uiautomator2', 'windows', 'remote_windows', 'nemu_ipc']


class MiscConfig(TypedDict, total=False):
    check_update: Literal['never', 'startup']
    auto_install_update: bool
    update_channel: Literal['release', 'beta']


class UserConfig(TypedDict, total=False):
    name: str
    id: str
    category: str
    description: str
    backend: BackendConfig
    keep_screenshots: bool
    options: Dict[str, Any]  # 这里包含 misc 等配置


class Config(TypedDict, total=False):
    version: int
    user_configs: List[UserConfig]


class ConfigLoadError(Exception):
    pass


def is_admin() -> bool:
    """
    检查当前进程是否具有管理员权限。

    :return: 如果具有管理员权限返回True，否则返回False
    :rtype: bool
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def load_config_logic() -> Config | None:
    """
    加载config.json配置文件。
    :param config_path: 配置文件路径
    :return: 配置字典。如果配置文件不存在，返回 None。
    """
    config_path = Path("./config.json")

    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise ConfigLoadError(f"加载配置文件失败: {e}") from e

def get_update_settings_logic(config: Config) -> tuple[bool, bool, Literal['release', 'beta']]:
    """
    从配置中获取更新设置。

    :param config: 配置字典
    :type config: Config
    :return: (是否检查更新, 是否自动安装更新, 更新通道)
    :rtype: tuple[bool, bool, Literal['release', 'beta']]
    """
    # 默认值
    check_update = True
    auto_install_update = True
    update_channel: Literal['release', 'beta'] = 'release'

    # 检查是否有用户配置
    user_configs = config.get("user_configs", [])
    if user_configs:
        first_config = user_configs[0]
        options = first_config.get("options", {})
        misc = options.get("misc", {})

        # 获取检查更新设置
        check_update_setting = misc.get("check_update", "startup")
        check_update = check_update_setting == "startup"

        # 获取自动安装更新设置
        auto_install_update = misc.get("auto_install_update", True)

        # 获取更新通道
        update_channel = misc.get("update_channel", 'release')  # type: ignore[assignment]

    return check_update, auto_install_update, update_channel

def restart_as_admin() -> None:
    """
    以管理员身份重启程序。
    """
    if is_admin():
        return
    script = os.path.abspath(sys.argv[0])
    params = '--skip-update'

    try:
        # 使用 ShellExecute 以管理员身份启动程序
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        if ret > 32:  # 返回值大于32表示成功
            msg = "正在以管理员身份重启程序..."
            print_status(msg, status='info')
            logging.info(msg)
            os._exit(0)
        else:
            msg = f"以管理员身份重启失败，错误码: {ret}"
            print_status(msg, status='error')
            logging.error(msg)
            return
    except Exception as e:
        msg = f"以管理员身份重启时发生错误: {e}"
        print_status(msg, status='error')
        logging.error(msg, exc_info=True)
        return
    
def run_command(command: str, check: bool = True, verbatim: bool = False, scroll_region_size: int = -1, log_output: bool = True) -> tuple[int, str]:
    """
    运行命令并实时输出，返回返回码和输出（仅包含 stdout，不包含 stderr）。

    :param command: 要运行的命令
    :param check: 是否检查返回码
    :param verbatim: 是否原样输出（保留参数兼容性，实际不使用）
    :param scroll_region_size: 滚动区域的大小（保留参数兼容性，实际不使用）
    :param log_output: 是否将命令输出记录到日志中
    :return: 返回码和输出（仅 stdout）
    """
    logging.info(f"执行命令: {command}")

    # 设置环境变量以确保正确的编码处理
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"  # 强制子进程（Python）无缓冲输出

    # 获取系统默认编码
    system_encoding = locale.getpreferredencoding()

    # 创建解码器
    def decode_output(line: bytes) -> str:
        try:
            # 首先尝试UTF-8解码
            return line.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # 如果UTF-8失败，尝试系统默认编码
                return line.decode(system_encoding)
            except UnicodeDecodeError:
                # 如果都失败了，使用'replace'策略
                return line.decode('utf-8', errors='replace')

    print(f"▶ 执行命令: {command}")

    stdout_chunks: list[str] = []

    try:
        process = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            bufsize=1,
            universal_newlines=False,
        )

        def read_stream(stream, is_stdout: bool) -> None:
            if not stream:
                return
            for line in iter(stream.readline, b''):
                clean_line = decode_output(line.rstrip(b'\r\n'))
                if clean_line.strip():
                    print(clean_line)
                    sys.stdout.flush()
                    if log_output:
                        if is_stdout:
                            logging.info(clean_line)
                        else:
                            logging.error(clean_line)
                if is_stdout:
                    stdout_chunks.append(clean_line)

        threads: list[threading.Thread] = []
        if process.stdout is not None:
            t_out = threading.Thread(target=read_stream, args=(process.stdout, True), daemon=True)
            threads.append(t_out)
            t_out.start()
        if process.stderr is not None:
            t_err = threading.Thread(target=read_stream, args=(process.stderr, False), daemon=True)
            threads.append(t_err)
            t_err.start()

        returncode = process.wait()
        for t in threads:
            t.join()

        logging.info(f"命令执行完毕，返回码: {returncode}")

        output = ''.join(stdout_chunks)

        if check and returncode != 0:
            msg = f"命令执行失败，返回码: {returncode}"
            print_status(msg, status='error')
            logging.error(msg)
            return returncode, output

        return returncode, output

    except FileNotFoundError:
        msg = f"命令未找到: {command.split()[0]}"
        print_status(msg, status='error')
        logging.error(msg)
        return -1, ''.join(stdout_chunks)
    except Exception as e:
        msg = f"命令执行时发生错误: {e}"
        print_status(msg, status='error')
        logging.error(msg, exc_info=True)
        return -1, ''.join(stdout_chunks)