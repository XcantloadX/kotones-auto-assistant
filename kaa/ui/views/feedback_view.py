import gradio as gr
from typing import Dict, Any
from functools import partial
from kaa.ui.facade import KaaFacade
from kaa.ui.common import GradioComponents
from kaa.errors import FeedbackServiceError

class FeedbackView:
    def __init__(self, facade: KaaFacade, components: GradioComponents):
        self.facade = facade
        self.components = components

    def create_ui(self) -> None:
        gr.Markdown("## 反馈")
        gr.Markdown('脚本报错或者卡住？在这里填写信息可以快速反馈！')
        with gr.Column():
            report_title = gr.Textbox(label="标题", placeholder="用一句话概括问题")
            report_type = gr.Dropdown(label="反馈类型", choices=["bug"], value="bug", interactive=False)
            report_description = gr.Textbox(label="描述", lines=5, placeholder="详细描述问题。例如：什么时候出错、是否每次都出错、出错时的步骤是什么")
            with gr.Row():
                upload_report_btn = gr.Button("上传")
                save_local_report_btn = gr.Button("保存至本地")

            result_text = gr.Markdown("等待操作\n\n\n")

        def create_report(title: str, description: str, upload: bool, progress=gr.Progress()):
            
            def on_progress(data: Dict[str, Any]):
                progress_val = data['step'] / data['total_steps']
                if data['type'] == 'packing':
                    desc = f"({data['step']}/{data['total_steps']}) 正在打包 {data['item']}"
                elif data['type'] == 'uploading':
                    desc = f"({data['step']}/{data['total_steps']}) 正在上传 {data['item']}"
                elif data['type'] == 'done':
                    if 'url' in data:
                        desc = "上传完成"
                    else:
                        desc = "已保存至本地"
                else:
                    desc = "正在处理..."
                progress(progress_val, desc=desc)

            try:
                result = self.facade.feedback_service.report(
                    title=title,
                    description=description,
                    version=self.facade._kaa.version,
                    upload=upload,
                    on_progress=on_progress
                )
                return result.message
            except FeedbackServiceError as e:
                gr.Error(str(e))
                return f"### 操作失败\n\n{e}"

        upload_report_btn.click(
            fn=partial(create_report, upload=True),
            inputs=[report_title, report_description],
            outputs=[result_text]
        )
        save_local_report_btn.click(
            fn=partial(create_report, upload=False),
            inputs=[report_title, report_description],
            outputs=[result_text]
        )
