import runpy
import logging
import argparse

from kaa.main.kaa import KaaDeviceFactory
from kotonebot.primitives.geometry import Size


def setup() -> None:
    """
    使用 runpy 运行指定的 Python 脚本

    Args:
        script_path: Python 脚本的路径
    """
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')

    # 运行脚本
    from kotonebot.backend.context import init_context, manual_context
    from kotonebot.config.config import conf
    conf().device.default_logic_resolution = Size(720, 1280)
    logging.getLogger('kotonebot').setLevel(logging.DEBUG)
    logging.getLogger('kaa').setLevel(logging.DEBUG)
    from kaa.kaa_context import init as kaa_init
    from kaa.config import manager
    configs = manager.list_profiles()
    if not configs:
        raise RuntimeError("No Kaa configuration profiles found. Please create one before running the script.")
    kaa_init(manager.read(configs[0]), configs[0])
    d = KaaDeviceFactory()()
    d.start()
    init_context(target_device=d)
    manual_context().begin()

def run_script(script_path: str) -> None:
    setup()
    
    # 获取模块名
    module_name = script_path.strip('.py').replace('\\', '/').strip('/').replace('/', '.')

    print(f"正在运行脚本: {script_path}")
    runpy.run_module(module_name, run_name="__main__")

def main():
    parser = argparse.ArgumentParser(description='运行指定的 Python 脚本')
    parser.add_argument('script_path', help='要运行的 Python 脚本路径')

    args = parser.parse_args()
    run_script(args.script_path)


if __name__ == '__main__':
    main()