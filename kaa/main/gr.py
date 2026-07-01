import logging
import traceback
from typing import Optional
import gradio as gr
from fastapi import FastAPI

from kaa.application.ui.facade import KaaFacade
from kaa.application.ui.gradio_view import KaaGradioView

logger = logging.getLogger(__name__)
custom_css = """
.no-padding-dropdown {
    padding: 0 !important;
}
.no-padding-dropdown > label {
    padding: 0 !important;
}
.no-padding-dropdown > div {
    padding: 0 !important;
}
"""

# QML WebView 模式下使用的默认端口
DEFAULT_GRADIO_PORT = 7860


def create_profile_blocks(
    facade: KaaFacade,
) -> gr.Blocks:
    """创建 profile 的 Blocks 实例（不启动服务器）。

    :param facade: KaaFacade 实例
    :param profile_name: profile 名称（用于 UI 显示）
    :return: 配置好的 gr.Blocks 实例
    """
    view = KaaGradioView(facade)
    blocks = view.create_ui()
    return blocks


def start_server(app: FastAPI) -> str:
    """启动共享 FastAPI 服务器，返回 URL。"""
    import uvicorn
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=DEFAULT_GRADIO_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()
    return f"http://127.0.0.1:{DEFAULT_GRADIO_PORT}"


def main(
    facade: KaaFacade,
    start_immediately: bool = False,
    *,
    server_port: Optional[int] = None,
) -> Optional[str]:
    """
    Main entry point for the KAA Gradio application.
    Launches Gradio in non-blocking mode for the QML WebView.

    :param facade: The KaaFacade instance.
    :param start_immediately: Whether to start all tasks immediately.
    :param server_port: Port to bind the Gradio server to.
                        If None, uses DEFAULT_GRADIO_PORT.
    :return: The local URL of the Gradio server (e.g. ``http://127.0.0.1:7860``),
             or None on failure.
    """
    try:
        view = KaaGradioView(facade)
        blocks = view.create_ui()

        if start_immediately:
            facade.start_all_tasks()

        from kaa.config import manager as config_manager
        misc_opts = config_manager.read_shared().misc
        logger.info(f"Launching Gradio UI... LAN exposure: {misc_opts.expose_to_lan}")

        app, local_url, share_url = blocks.launch(
            share=misc_opts.expose_to_lan,
            inbrowser=False,
            css=custom_css,
            server_name='127.0.0.1',
            server_port=server_port or DEFAULT_GRADIO_PORT,
            prevent_thread_lock=True,
        )

        logger.info(f"Gradio server running at {local_url} (non-blocking)")
        return local_url

    except Exception:
        logger.exception("A critical error occurred during application startup.")
        # If startup fails, display a minimal error UI to the user.
        with gr.Blocks() as error_blocks:
            gr.Markdown("# 琴音小助手 启动失败")
            gr.Markdown(
                "kaa 在启动时遇到严重错误。\n\n"
                "请前往 [QQ 群](https://qm.qq.com/q/DFglKikW2s)或 [Github Issues](https://github.com/a-date-na/kotone-auto-assistant/issues) 寻求帮助。"
            )
            gr.Code(traceback.format_exc(), label="Traceback")

        error_blocks.launch(inbrowser=False)
        return None