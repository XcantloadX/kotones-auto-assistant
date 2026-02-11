import os
import sys
import logging
import argparse
import importlib.metadata
from datetime import datetime

try:
    from ..util.telemetry import setup # noqa: F401
    setup()
except Exception as e:
    print(f'Failed to set up telemetry: {e}')

from .kaa import Kaa
from ..util.paths import get_ahk_path
from kotonebot.client.implements.windows import WindowsImplConfig
from kotonebot.backend.context import tasks_from_id, task_registry
from kotonebot.client.implements.remote_windows import RemoteWindowsServer

version = importlib.metadata.version('ksaa')

# 主命令
psr = argparse.ArgumentParser(description='Command-line interface for Kotone\'s Auto Assistant')
psr.add_argument('-v', '--version', action='version', version='kaa v' + version)
psr.add_argument('-c', '--config', default='./config.json', help='Path to the configuration file. Default: ./config.json')
psr.add_argument('-lp', '--log-path', default=None, help='Path to the log file. Does not log to file if not specified. Default: None')
psr.add_argument('-ll', '--log-level', default='DEBUG', help='Log level. Default: DEBUG')
psr.add_argument('--kill-dmm', action='store_true', default=False, help='Kill DMM Game Player when tasks are completed. Overrides config().end_game.kill_dmm')
psr.add_argument('--kill-game', action='store_true', default=False, help='Kill gakumasu.exe when tasks are completed. Overrides config().end_game.kill_game')
psr.add_argument('--start-immidiately', action='store_true', default=False, help='Start tasks immediately after launching the UI. Only available when no subcommand is specified.')

# 子命令
subparsers = psr.add_subparsers(dest='subcommands', title='Subcommands')

# task 子命令
task_psr = subparsers.add_parser('task', help='Task related commands')
task_subparsers = task_psr.add_subparsers(dest='task_command', required=True)

# task invoke 子命令
invoke_psr = task_subparsers.add_parser('invoke', help='Invoke a task or many tasks')
invoke_psr.add_argument('task_ids', nargs='*', help='Tasks to invoke')

# task list 子命令
list_psr = task_subparsers.add_parser('list', help='List all available tasks')

# remote-server 子命令
remote_server_psr = subparsers.add_parser('remote-server', help='Start the remote Windows server')
remote_server_psr.add_argument('--host', default='0.0.0.0', help='Host to bind to')
remote_server_psr.add_argument('--port', type=int, default=8000, help='Port to bind to')

_kaa: Kaa | None = None
def kaa() -> Kaa:
    global _kaa
    if _kaa is None:
        _kaa = Kaa(psr.parse_args().config)
        # _kaa.initialize()
    return _kaa

def task_invoke() -> int:
    tasks_args = psr.parse_args().task_ids
    assert isinstance(tasks_args, list)
    if not tasks_args:
        print('No tasks specified.')
        return -1
    # 设置日志
    log_level = getattr(logging, psr.parse_args().log_level, None)
    if log_level is None:
        raise ValueError(f'Invalid log level: {psr.parse_args().log_level}')
    kaa().set_log_level(log_level)
    from kaa.util.logging import add_file_logger
    if psr.parse_args().log_path is not None:
        add_file_logger(psr.parse_args().log_path)
    # 执行任务
    print(tasks_args)
    if '*' in tasks_args:
        if len(tasks_args) > 1:
            raise ValueError('Cannot specify other tasks when using wildcard.')
        kaa().run_all()
    else:
        kaa().run(tasks_from_id(tasks_args))
    if psr.parse_args().kill_dmm:
        os.system('taskkill /f /im DMMGamePlayer.exe')
    if psr.parse_args().kill_game:
        os.system('taskkill /f /im gakumas.exe')
    return 0

def task_list() -> int:
    # 确保任务已加载
    kaa()

    if not task_registry:
        print('No tasks available.')
        return 0

    print('Available tasks:')
    for task in task_registry.values():
        print(f'  * {task.id}: {task.name}\n    {task.description.strip()}')
    return 0

def remote_server() -> int:
    args = psr.parse_args()
    try:
        ahk_path = get_ahk_path()
        server = RemoteWindowsServer(WindowsImplConfig(window_title='gakumas', ahk_exe_path=ahk_path), args.host, args.port)
        server.start()
        return 0
    except KeyboardInterrupt:
        print("Server stopped by user")
        return 0
    except Exception as e:
        print(f'Error starting remote server: {e}')
        return -1

def main():
    args = psr.parse_args()
    if args.subcommands == 'task':
        if args.task_command == 'invoke':
            sys.exit(task_invoke())
        elif args.task_command == 'list':
            sys.exit(task_list())
        else:
            raise ValueError(f'Unknown task command: {args.task_command}')
    elif args.subcommands == 'remote-server':
        sys.exit(remote_server())
    elif args.subcommands is None:
        log_filename = datetime.now().strftime('logs/%y-%m-%d-%H-%M-%S.log')
        from kaa.util.logging import setup, add_file_logger
        setup()
        add_file_logger(log_filename)
        from .gr import main as gr_main
        from ..application.ui.facade import KaaFacade
        facade = KaaFacade(kaa())
        log_level_str = facade.config_service.get_options().misc.log_level
        log_level = logging.DEBUG if log_level_str == 'verbose' else logging.INFO
        kaa().set_log_level(log_level)
        gr_main(facade, psr.parse_args().start_immidiately)

if __name__ == '__main__':
    main()