import gradio as gr
import logging
from kaa.ui.facade import KaaFacade
from kaa.ui.common import GradioComponents

logger = logging.getLogger(__name__)

class UpdateView:
    def __init__(self, facade: KaaFacade, components: GradioComponents):
        self.facade = facade
        self.components = components

    def create_ui(self):
        """Creates the content for the 'Update' tab."""
        with gr.Tab("更新"):
            gr.Markdown("## 检查更新")
            
            check_update_btn = gr.Button("检查更新", variant="primary")
            update_info_md = gr.Markdown("")
            self.components.update_info_md = update_info_md # Store the component

            def on_check_update_click():
                gr.Info("正在检查更新...")
                return self._get_update_message()
            
            check_update_btn.click(
                fn=on_check_update_click,
                outputs=[update_info_md]
            )

    def _get_update_message(self) -> str:
        try:
            has_update, latest_version, changelog = self.facade.check_for_updates()
            if has_update:
                return f"**发现新版本！**\n\n**版本:** {latest_version}\n\n**更新日志:**\n\n{changelog}"
            else:
                return f"当前已是最新版本 ({self.facade._kaa.version})。"
        except Exception as e:
            logger.error("Failed to check for updates", exc_info=True)
            return f"检查更新失败: {e}"

    def initial_update_check_handler(self):
        if self.facade.config_service.get_options().misc.check_update == 'startup':
            # gr.Info is a UI component, not a direct function. We will just return the message
            # and let the blocks.load event update the markdown component.
            return self._get_update_message()
        return "" # Return empty string if no check is needed
