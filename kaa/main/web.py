import os
import logging
import argparse
import webbrowser
import threading
import time

import uvicorn

logger = logging.getLogger(__name__)


def main(
    *,
    host: str | None = None,
    port: int | None = None,
    config: str | None = None,
    static: str | None = None,
    dev: bool | None = None,
    browser: bool | None = None,
):
    """启动 Web UI 服务器
    
    :param host: 监听地址，默认 '127.0.0.1'
    :param port: 监听端口，默认 8000
    :param config: 配置文件路径，默认 'config.json'
    :param static: 静态文件目录，默认 'kaa-ui/dist'
    :param dev: 开发模式，默认 False
    :param browser: 是否自动打开浏览器，默认 True
    """
    parser = argparse.ArgumentParser(description='Kotones Auto Assistant Web UI')
    parser.add_argument('--host', default='127.0.0.1', help='Listening address')
    parser.add_argument('--port', type=int, default=8000, help='Listening port')
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--static', default='kaa-ui/dist', help='Static files directory (production environment)')
    parser.add_argument('--dev', action='store_true', help='Development mode (do not mount static files)')
    parser.add_argument('--browser', action='store_true', default=True, help='Auto open browser (default: True)')
    parser.add_argument('--no-browser', action='store_true', help='Do not auto open browser')
    args = parser.parse_args()
    
    # 函数参数优先级高于命令行参数
    final_host = host if host is not None else args.host
    final_port = port if port is not None else args.port
    final_config = config if config is not None else args.config
    final_static = static if static is not None else args.static
    final_dev = dev if dev is not None else args.dev
    
    # 处理 browser 参数
    if browser is not None:
        final_browser = browser
    elif args.no_browser:
        final_browser = False
    else:
        final_browser = args.browser
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s][%(levelname)s][%(name)s] %(message)s'
    )
    
    logger.info("=" * 60)
    logger.info("Kotones Auto Assistant Web UI")
    logger.info("=" * 60)
    logger.info(f"Config file: {final_config}")
    logger.info(f"Listening address: {final_host}:{final_port}")
    
    # 导入服务（触发 RPC 注册）
    from kaa.server import services
    from kaa.server import asgi_app, setup_static_files, registry
    
    logger.info("Registered RPC methods:")
    for method in registry.list_methods():
        logger.info(f"  - {method}")
    
    # 初始化 KaaRuntime
    from kaa.server.adapters import get_runtime
    runtime = get_runtime(final_config)
    logger.info("KaaRuntime initialized")
    
    # 生产环境：挂载静态文件
    if not final_dev and os.path.exists(final_static):
        setup_static_files(final_static)
        logger.info(f"Static files: {final_static}")
    elif not final_dev:
        logger.warning(f"Static files directory does not exist: {final_static}")
        logger.warning("If in development environment, please use --dev flag")
    
    # 自动打开浏览器
    if final_browser:
        def open_browser():
            time.sleep(1.5)
            if final_dev:
                url = f"http://localhost:5173"
            else:
                url = f"http://{final_host}:{final_port}"
            logger.info(f"Opening browser: {url}")
            webbrowser.open(url)
        
        threading.Thread(target=open_browser, daemon=True).start()
    
    # 启动服务器
    logger.info("=" * 60)
    logger.info("Server starting...")
    logger.info("=" * 60)

    uvicorn.run(
        asgi_app,
        host=final_host,
        port=final_port,
        log_level="critical"
    )


if __name__ == '__main__':
    main()

