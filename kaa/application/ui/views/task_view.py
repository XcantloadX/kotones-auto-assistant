import gradio as gr
from kaa.application.ui.facade import KaaFacade
from kaa.application.ui.common import GradioComponents

class TaskView:
    def __init__(self, facade: KaaFacade, components: GradioComponents):
        self.facade = facade
        self.components = components

    def create_ui(self):
        """Creates the content for the 'Task' tab for running single tasks."""
        gr.Markdown("## 执行任务")

        # Get all tasks from the facade
        task_names = self.facade.task_service.get_all_task_names()
        
        with gr.Row():
            stop_all_btn = gr.Button("停止任务", variant="stop", scale=1)
            pause_btn = gr.Button("暂停", scale=1)

        task_result = gr.Markdown("")
        
        task_buttons = []
        for task_name in task_names:
            with gr.Row():
                with gr.Column(scale=1, min_width=50):
                    task_btn = gr.Button("启动", variant="primary", size="sm")
                    task_buttons.append(task_btn)
                with gr.Column(scale=7):
                    gr.Markdown(f"### {task_name}")

        def start_single_task_by_name(task_name: str):
            """Event handler to start a single task."""
            try:
                self.facade.start_single_task(task_name)
                gr.Info(f"任务 {task_name} 开始执行")
            except ValueError as e:
                gr.Warning(str(e))
            except Exception as e:
                gr.Error(f"启动任务失败: {e}")

        def stop_all_tasks():
            """Event handler to stop the running single task."""
            self.facade.stop_tasks()

        def on_pause_click():
            self.facade.toggle_pause()

        # Bind click events
        for i, task_name in enumerate(task_names):
            # Use a closure/factory function to capture the correct task_name
            def create_handler(name):
                return lambda: start_single_task_by_name(name)
            task_buttons[i].click(fn=create_handler(task_name), outputs=None)

        stop_all_btn.click(fn=stop_all_tasks, outputs=None)
        pause_btn.click(fn=on_pause_click, outputs=None)
        
        # --- Timers for status updates ---

        def update_task_ui_status():
            tcs = self.facade.task_service
            is_running = tcs.is_running_single
            is_stopping = tcs.is_stopping

            # Update buttons
            btn_updates = {}
            if is_running or is_stopping:
                btn_text = "停止中" if is_stopping else "运行中"
                for btn in task_buttons:
                    btn_updates[btn] = gr.Button(value=btn_text, interactive=False)
            else:
                for btn in task_buttons:
                    btn_updates[btn] = gr.Button(value="启动", interactive=True)
            
            # Update status message
            status_msg = ""
            if is_running:
                for name, status in tcs.get_task_statuses():
                    if status == 'running':
                        status_msg = f"正在执行任务: {name}"
                        break

            btn_updates[task_result] = gr.Markdown(value=status_msg)

            # Update pause button
            pause_status = self.facade.get_pause_button_status()
            btn_updates[pause_btn] = gr.Button(value=pause_status['text'], interactive=pause_status['interactive'])
            
            return btn_updates

        gr.Timer(1.0).tick(
            fn=update_task_ui_status,
            outputs=task_buttons + [task_result, pause_btn]
        )
