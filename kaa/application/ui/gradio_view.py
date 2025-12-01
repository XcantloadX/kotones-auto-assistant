import logging
import gradio as gr

from kaa.application.ui.facade import KaaFacade
from kaa.application.ui.common import GradioComponents, ConfigBuilderReturnValue
from kaa.application.ui.views.status_view import StatusView
from kaa.application.ui.views.task_view import TaskView
from kaa.application.ui.views.produce_view import ProduceView
from kaa.application.ui.views.settings_view import SettingsView
from kaa.application.ui.views.feedback_view import FeedbackView
from kaa.application.ui.views.update_view import UpdateView

logger = logging.getLogger(__name__)

class KaaGradioView:
    """
    The View layer for the kaa application, responsible for rendering the UI
    and delegating all user actions to the Facade.
    """

    def __init__(self, facade: KaaFacade):
        self.facade = facade
        # A dataclass to hold all UI components that need to be accessed later
        self.components = GradioComponents()
        # A list to hold all the config builder return values for the save function
        self.config_builders: list[ConfigBuilderReturnValue] = []

        # Initialize sub-views
        self.status_view = StatusView(facade, self.components)
        self.task_view = TaskView(facade, self.components)
        self.produce_view = ProduceView(facade, self.components)
        self.settings_view = SettingsView(facade, self.components, self.config_builders)
        self.feedback_view = FeedbackView(facade, self.components)
        self.update_view = UpdateView(facade, self.components)

    def create_ui(self) -> gr.Blocks:
        """
        Builds the entire Gradio UI and returns the final Blocks object.
        """
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
        with gr.Blocks(title=f"琴音小助手 v{self.facade._kaa.version}", css=custom_css) as blocks:
            self._create_header()
            with gr.Tabs() as tabs:
                self.components.tabs = tabs
                with gr.Tab("状态", id="status"):
                    self.status_view.create_ui()
                with gr.Tab("任务", id="tasks"):
                    self.task_view.create_ui()
                with gr.Tab("培育", id="produce"):
                    self.produce_view.create_ui()
                with gr.Tab("设置", id="settings"):
                    self.settings_view.create_ui()
                with gr.Tab("反馈", id="feedback"):
                    self.feedback_view.create_ui()
                # Update tab is created inside the view itself because it's a single tab
                self.update_view.create_ui()

            self._setup_timers()

            # Add blocks.load for initial update check and produce solution details
            all_load_outputs = [self.components.update_info_md] + self.components.produce_all_detail_components
            blocks.load(
                fn=self._on_ui_load,
                outputs=all_load_outputs
            )
        return blocks

    def _on_ui_load(self):
        # 1. Handle update check
        update_msg = self.update_view.initial_update_check_handler()

        # 2. Handle produce solution details
        initial_solution_id = self.components.produce_tab_solution_dropdown.value
        produce_updates_dict = self.produce_view.update_produce_solution_details(initial_solution_id)
        
        # 3. Order the produce updates correctly according to the component list
        produce_updates_tuple = tuple(
            produce_updates_dict[comp] for comp in self.components.produce_all_detail_components
        )
        
        # 4. Return combined tuple of all updates
        return (update_msg,) + produce_updates_tuple
    
    def _create_header(self):
        gr.Markdown(f"# 琴音小助手 v{self.facade._kaa.version}")

    def _setup_timers(self):
        """Sets up all the UI polling timers."""

        # Timer for run/pause buttons
        def update_run_buttons():
            run_status = self.facade.get_run_status()
            pause_status = self.facade.get_pause_button_status()
            return {
                self.components.run_btn: gr.Button(value=run_status['text'], interactive=run_status['interactive']),
                self.components.pause_btn: gr.Button(value=pause_status['text'], interactive=pause_status['interactive']),
            }
        gr.Timer(1.0).tick(
            fn=update_run_buttons,
            outputs=[self.components.run_btn, self.components.pause_btn]
        )

        # Timer for task status dataframe
        def update_task_status_df():
            statuses = self.facade.get_task_statuses()
            # Convert status keys to display text
            status_map = {
                'pending': '等待中', 'running': '运行中', 'finished': '已完成',
                'error': '出错', 'cancelled': '已取消'
            }
            display_statuses = [[name, status_map.get(status, '未知')] for name, status in statuses]
            return gr.Dataframe(value=display_statuses)

        gr.Timer(1.0).tick(
            fn=update_task_status_df,
            outputs=[self.components.task_status_df]
        )

        # Timer for task runtime
        def update_task_runtime():
            runtime_str = self.facade.get_task_runtime()
            return gr.Textbox(value=runtime_str)

        gr.Timer(1.0).tick(
            fn=update_task_runtime,
            outputs=[self.components.task_runtime_text]
        )
        
        # Timer for quick-setting checkboxes
        def update_quick_checkboxes():
            opts = self.facade.config_service.get_options()
            
            end_game_opts = opts.end_game
            if end_game_opts.shutdown:
                end_action_val = "完成后关机"
            elif end_game_opts.hibernate:
                end_action_val = "完成后休眠"
            else:
                end_action_val = "完成后什么都不做"

            return {
                self.components.quick_checkboxes[0]: gr.Checkbox(value=opts.purchase.enabled),
                self.components.quick_checkboxes[1]: gr.Checkbox(value=opts.assignment.enabled),
                self.components.quick_checkboxes[2]: gr.Checkbox(value=opts.contest.enabled),
                self.components.quick_checkboxes[3]: gr.Checkbox(value=opts.produce.enabled),
                self.components.quick_checkboxes[4]: gr.Checkbox(value=opts.mission_reward.enabled),
                self.components.quick_checkboxes[5]: gr.Checkbox(value=opts.club_reward.enabled),
                self.components.quick_checkboxes[6]: gr.Checkbox(value=opts.activity_funds.enabled),
                self.components.quick_checkboxes[7]: gr.Checkbox(value=opts.presents.enabled),
                self.components.quick_checkboxes[8]: gr.Checkbox(value=opts.capsule_toys.enabled),
                self.components.quick_checkboxes[9]: gr.Checkbox(value=opts.upgrade_support_card.enabled),
                self.components.end_action_dropdown: gr.Dropdown(value=end_action_val),
            }

        gr.Timer(2.0).tick(
            fn=update_quick_checkboxes,
            outputs=self.components.quick_checkboxes + [self.components.end_action_dropdown]
        )
