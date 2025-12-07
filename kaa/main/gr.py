import logging
import traceback
import gradio as gr

from kaa.main.kaa import Kaa
from kaa.application.ui.facade import KaaFacade
from kaa.application.ui.gradio_view import KaaGradioView

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

def main(kaa_ins: Kaa, start_immediately: bool = False):
    """
    Main entry point for the KAA Gradio application.
    Initializes the core application, facade, and UI view, then launches the UI.
    """
    # Configure basic logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
    logger = logging.getLogger(__name__)

    try:
        # 1. Initialize Model/Core Application
        # The Kaa instance holds the core application logic and state.
        kaa_instance = kaa_ins
        
        # 2. Initialize Facade
        # The Facade is the single point of entry for the UI to interact with the backend.
        # It orchestrates the various services.
        facade = KaaFacade(kaa_instance)

        # Set log level from config
        log_level_str = facade.config_service.get_options().misc.log_level
        log_level = logging.DEBUG if log_level_str == 'verbose' else logging.INFO
        logging.getLogger().setLevel(log_level)
        logger.info(f"Log level set to {log_level_str.upper()}")


        # 3. Initialize View
        # The View is responsible for building and rendering the UI.
        # It only interacts with the Facade.
        view = KaaGradioView(facade)

        # 4. Create and launch the Gradio UI
        blocks = view.create_ui()
        
        if start_immediately:
            facade.start_all_tasks()

        misc_opts = facade.config_service.get_options().misc
        logger.info(f"Launching Gradio UI... LAN exposure: {misc_opts.expose_to_lan}")
        
        blocks.launch(
            share=misc_opts.expose_to_lan,
            inbrowser=True,
            css=custom_css
        )

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

        error_blocks.launch(inbrowser=True)