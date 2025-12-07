import gradio as gr
import logging
from typing import Generator, Tuple
from kaa.application.ui.facade import KaaFacade
from kaa.application.ui.common import GradioComponents
from kaa.errors import UpdateServiceError, UpdateFetchListError

logger = logging.getLogger(__name__)

class UpdateView:
    def __init__(self, facade: KaaFacade, components: GradioComponents):
        self.facade = facade
        self.components = components

    def create_ui(self):
        """Creates the content for the 'Update' tab."""
        with gr.Tab("更新"):
            gr.Markdown("## 版本管理")
            
            with gr.Accordion("更新日志", open=False):
                try:
                    from kaa.metadata import WHATS_NEW
                    gr.Markdown(WHATS_NEW)
                except ImportError:
                    gr.Markdown("更新日志不可用")
            
            load_info_btn = gr.Button("载入信息", variant="primary")
            status_text = gr.Markdown("")
            version_dropdown = gr.Dropdown(
                label="选择要安装的版本",
                choices=[],
                value=None,
                visible=False,
                interactive=True
            )
            install_selected_btn = gr.Button("安装选定版本", visible=False)
            
            # Store components for later access
            self.components.update_status_text = status_text
            self.components.update_version_dropdown = version_dropdown
            self.components.update_install_btn = install_selected_btn

            def on_load_info():
                """使用 UpdateService 加载版本信息。"""
                yield (
                    "正在载入版本信息...",
                    gr.Button(value="载入中...", interactive=False),
                    gr.Dropdown(visible=False),
                    gr.Button(visible=False)
                )
                try:
                    versions_data = self.facade.update_service.list_remote_versions()
                except UpdateFetchListError as e:
                    gr.Error(str(e))
                    yield (
                        str(e),
                        gr.Button(value="载入信息", interactive=True),
                        gr.Dropdown(visible=False),
                        gr.Button(visible=False)
                    )
                    return

                status_info = [
                    f"**当前安装版本:** {versions_data.installed_version or '未知'}",
                    f"**最新版本:** {versions_data.latest or '未知'}",
                ]
                if versions_data.launcher_version:
                    if versions_data.launcher_version == "0.4.x":
                        status_info.append("**启动器版本:** < v0.5.0 (旧版本)")
                    else:
                        status_info.append(f"**启动器版本:** v{versions_data.launcher_version}")
                else:
                    status_info.append("**启动器版本:** 未知")
                
                status_info.append(f"**找到 {len(versions_data.versions)} 个可用版本**")
                status_message = "\n\n".join(status_info)

                yield (
                    status_message,
                    gr.Button(value="载入信息", interactive=True),
                    gr.Dropdown(choices=versions_data.versions, value=versions_data.versions[0] if versions_data.versions else None, visible=True),
                    gr.Button(visible=True)
                )

            def on_install_selected(selected_version: str):
                """使用 UpdateService 安装所选版本。"""
                if not selected_version:
                    gr.Warning("请先选择一个版本。")
                    return

                try:
                    self.facade.update_service.install_version(selected_version)
                    gr.Info(f"正在启动器中安装版本 {selected_version}，程序将自动重启...")
                except UpdateServiceError as e:
                    gr.Error(str(e))

            load_info_btn.click(
                fn=on_load_info,
                outputs=[status_text, load_info_btn, version_dropdown, install_selected_btn]
            )

            install_selected_btn.click(
                fn=on_install_selected,
                inputs=[version_dropdown],
                outputs=[] 
            )