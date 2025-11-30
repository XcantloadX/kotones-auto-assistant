import logging
from typing import List, Dict, Tuple, Callable, Any, Literal, cast, Optional
from functools import partial
from dataclasses import dataclass, field

import gradio as gr

from kaa.ui.facade import KaaFacade, ConfigValidationError
from kaa.config.schema import (
    BaseConfig, PurchaseConfig, AssignmentConfig, ContestConfig, ProduceConfig
)
from kaa.config.const import DailyMoneyShopItems, APShopItems, ProduceAction, RecommendCardDetectionMode
from kaa.db.idol_card import IdolCard
from kaa.config.produce import ProduceData, ProduceSolution
from kaa.errors import FeedbackServiceError

# Imports that were in gr.py and are needed for UI rendering or helpers
from kotonebot.client.host import Mumu12Host, Mumu12V5Host, LeidianHost

logger = logging.getLogger(__name__)

# Type hints from gr.py
GradioInput = gr.Textbox | gr.Number | gr.Checkbox | gr.Dropdown | gr.Radio | gr.Slider | gr.State
ConfigKey = Literal[
    # backend
    'backend_type', 'adb_ip', 'adb_port',
    'screenshot_method', 'keep_screenshots',
    'check_emulator', 'emulator_path',
    'adb_emulator_name', 'emulator_args',
    '_mumu_index', '_mumu12v5_index', '_leidian_index',
    'mumu_background_mode_v4', 'mumu_background_mode_v5', 'target_screenshot_interval',

    # purchase
    'purchase_enabled',
    'money_enabled', 'ap_enabled',
    'ap_items', 'money_items', 'money_refresh',
    
    # assignment
    'assignment_enabled',
    'mini_live_reassign', 'mini_live_duration',
    'online_live_reassign', 'online_live_duration',
    'contest_enabled',
    'select_which_contestant', 'when_no_set',
    
    # produce
    'produce_enabled', 'selected_solution_id', 'produce_count', 'produce_timeout_cd', 'interrupt_timeout', 'enable_fever_month',
    'mission_reward_enabled',
    
    # club reward
    'club_reward_enabled',
    'selected_note',
    
    # upgrade support card
    'upgrade_support_card_enabled',
    
    # capsule toys
    'capsule_toys_enabled', 'friend_capsule_toys_count',
    'sense_capsule_toys_count', 'logic_capsule_toys_count',
    'anomaly_capsule_toys_count',
    
    # start game
    'start_game_enabled', 'start_through_kuyo',
    'game_package_name', 'kuyo_package_name',
    'disable_gakumas_localify', 'dmm_game_path', 'dmm_bypass',

    # end game
    'exit_kaa', 'kill_game', 'kill_dmm',
    'kill_emulator', 'shutdown', 'hibernate',
    'restore_gakumas_localify',
    
    'activity_funds',
    'presents',
    'mission_reward',
    'activity_funds_enabled',
    'presents_enabled',
    'trace_recommend_card_detection',
    
    # misc
    'check_update', 'auto_install_update', 'expose_to_lan', 'update_channel', 'log_level',

    # idle
    'idle_enabled', 'idle_seconds', 'idle_minimize_on_pause',

    '_selected_backend_index'
    
]
ConfigSetFunction = Callable[[BaseConfig, Dict[ConfigKey, Any]], None]
ConfigBuilderReturnValue = Tuple[ConfigSetFunction, Dict[ConfigKey, GradioInput]]


@dataclass
class GradioComponents:
    """Dataclass to hold all Gradio UI components that need to be accessed across methods."""
    
    # Main tabs
    tabs: Optional[gr.Tabs] = None
    
    # Status tab components
    run_btn: Optional[gr.Button] = None
    pause_btn: Optional[gr.Button] = None
    end_action_dropdown: Optional[gr.Dropdown] = None
    quick_checkboxes: List[gr.Checkbox] = field(default_factory=list)
    task_status_df: Optional[gr.Dataframe] = None
    
    # Update tab components
    update_info_md: Optional[gr.Markdown] = None
    
    # Produce tab components
    produce_tab_solution_dropdown: Optional[gr.Dropdown] = None
    produce_solution_settings_group: Optional[gr.Group] = None
    produce_solution_name: Optional[gr.Textbox] = None
    produce_solution_description: Optional[gr.Textbox] = None
    produce_mode: Optional[gr.Dropdown] = None
    produce_idols: Optional[gr.Dropdown] = None
    produce_auto_set_memory: Optional[gr.Checkbox] = None
    produce_memory_sets_group: Optional[gr.Group] = None
    produce_memory_sets: Optional[gr.Dropdown] = None
    produce_auto_set_support: Optional[gr.Checkbox] = None
    produce_support_card_sets_group: Optional[gr.Group] = None
    produce_support_card_sets: Optional[gr.Dropdown] = None
    produce_use_pt_boost: Optional[gr.Checkbox] = None
    produce_use_note_boost: Optional[gr.Checkbox] = None
    produce_follow_producer: Optional[gr.Checkbox] = None
    produce_self_study_lesson: Optional[gr.Dropdown] = None
    produce_prefer_lesson_ap: Optional[gr.Checkbox] = None
    produce_actions_order: Optional[gr.Dropdown] = None
    produce_recommend_card_detection_mode: Optional[gr.Dropdown] = None
    produce_use_ap_drink: Optional[gr.Checkbox] = None
    produce_skip_commu: Optional[gr.Checkbox] = None
    produce_all_detail_components: List[Any] = field(default_factory=list)
    
    # Settings tab components
    settings_solution_dropdown: Optional[gr.Dropdown] = None
    save_settings_btn: Optional[gr.Button] = None


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
                    self._create_status_tab()
                with gr.Tab("任务", id="tasks"):
                    self._create_task_tab()
                with gr.Tab("培育", id="produce"):
                    self._create_produce_tab()
                with gr.Tab("设置", id="settings"):
                    self._create_settings_tab()
                with gr.Tab("反馈", id="feedback"):
                    self._create_feedback_tab()
                with gr.Tab("更新", id="update"):
                    self._create_update_tab()

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
        update_msg = self._initial_update_check_handler()

        # 2. Handle produce solution details
        initial_solution_id = self.components.produce_tab_solution_dropdown.value
        produce_updates_dict = self._update_produce_solution_details(initial_solution_id)
        
        # 3. Order the produce updates correctly according to the component list
        produce_updates_tuple = tuple(
            produce_updates_dict[comp] for comp in self.components.produce_all_detail_components
        )
        
        # 4. Return combined tuple of all updates
        return (update_msg,) + produce_updates_tuple
    
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

    def _initial_update_check_handler(self):
        if self.facade.config_service.get_options().misc.check_update == 'startup':
            # gr.Info is a UI component, not a direct function. We will just return the message
            # and let the blocks.load event update the markdown component.
            return self._get_update_message()
        return "" # Return empty string if no check is needed

    def _update_produce_solution_details(self, solution_id: str):
        """Updates the produce solution detail view when the selected solution changes."""
        if not solution_id:
            # Return a default/empty state for all components in the form
            return {
                self.components.produce_solution_settings_group: gr.Group(visible=False),
                self.components.produce_solution_name: gr.Textbox(value=""),
                self.components.produce_solution_description: gr.Textbox(value=""),
                self.components.produce_mode: gr.Dropdown(value=None),
                self.components.produce_idols: gr.Dropdown(value=None),
                self.components.produce_auto_set_memory: gr.Checkbox(value=False),
                self.components.produce_memory_sets_group: gr.Group(visible=True),
                self.components.produce_memory_sets: gr.Dropdown(value=None),
                self.components.produce_auto_set_support: gr.Checkbox(value=False),
                self.components.produce_support_card_sets_group: gr.Group(visible=True),
                self.components.produce_support_card_sets: gr.Dropdown(value=None),
                self.components.produce_use_pt_boost: gr.Checkbox(value=False),
                self.components.produce_use_note_boost: gr.Checkbox(value=False),
                self.components.produce_follow_producer: gr.Checkbox(value=False),
                self.components.produce_self_study_lesson: gr.Dropdown(value=None),
                self.components.produce_prefer_lesson_ap: gr.Checkbox(value=False),
                self.components.produce_actions_order: gr.Dropdown(value=[]),
                self.components.produce_recommend_card_detection_mode: gr.Dropdown(value=None),
                self.components.produce_use_ap_drink: gr.Checkbox(value=False),
                self.components.produce_skip_commu: gr.Checkbox(value=False),
            }
        try:
            solution = self.facade.get_produce_solution(solution_id)
            return {
                self.components.produce_solution_settings_group: gr.Group(visible=True),
                self.components.produce_solution_name: gr.Textbox(value=solution.name),
                self.components.produce_solution_description: gr.Textbox(value=solution.description),
                self.components.produce_mode: gr.Dropdown(value=solution.data.mode),
                self.components.produce_idols: gr.Dropdown(value=solution.data.idol),
                self.components.produce_auto_set_memory: gr.Checkbox(value=solution.data.auto_set_memory),
                self.components.produce_memory_sets_group: gr.Group(visible=not solution.data.auto_set_memory),
                self.components.produce_memory_sets: gr.Dropdown(value=str(solution.data.memory_set) if solution.data.memory_set else None),
                self.components.produce_auto_set_support: gr.Checkbox(value=solution.data.auto_set_support_card),
                self.components.produce_support_card_sets_group: gr.Group(visible=not solution.data.auto_set_support_card),
                self.components.produce_support_card_sets: gr.Dropdown(value=str(solution.data.support_card_set) if solution.data.support_card_set else None),
                self.components.produce_use_pt_boost: gr.Checkbox(value=solution.data.use_pt_boost),
                self.components.produce_use_note_boost: gr.Checkbox(value=solution.data.use_note_boost),
                self.components.produce_follow_producer: gr.Checkbox(value=solution.data.follow_producer),
                self.components.produce_self_study_lesson: gr.Dropdown(value=solution.data.self_study_lesson),
                self.components.produce_prefer_lesson_ap: gr.Checkbox(value=solution.data.prefer_lesson_ap),
                self.components.produce_actions_order: gr.Dropdown(value=[action.value for action in solution.data.actions_order]),
                self.components.produce_recommend_card_detection_mode: gr.Dropdown(value=solution.data.recommend_card_detection_mode.value),
                self.components.produce_use_ap_drink: gr.Checkbox(value=solution.data.use_ap_drink),
                self.components.produce_skip_commu: gr.Checkbox(value=solution.data.skip_commu),
            }
        except Exception as e:
            gr.Error(f"加载培育方案失败: {e}")
            return {self.components.produce_solution_settings_group: gr.Group(visible=False)}
    
    def _create_header(self):
        gr.Markdown(f"# 琴音小助手 v{self.facade._kaa.version}")

    def _create_status_tab(self):
        """Creates the content for the 'Status' tab."""
        gr.Markdown("## 状态")

        def _get_end_action_value() -> str:
            end_game_opts = self.facade.config_service.get_options().end_game
            if end_game_opts.shutdown:
                return "完成后关机"
            if end_game_opts.hibernate:
                return "完成后休眠"
            return "完成后什么都不做"

        with gr.Row():
            run_btn = gr.Button("启动", scale=0, variant='primary', min_width=300)
            pause_btn = gr.Button("暂停", scale=0)
            with gr.Column(scale=0):
                end_action_dropdown = gr.Dropdown(
                    show_label=False,
                    choices=["完成后什么都不做", "完成后关机", "完成后休眠"],
                    value=_get_end_action_value(),
                    interactive=True,
                    elem_classes="no-padding-dropdown",
                )

        self.components.run_btn = run_btn
        self.components.pause_btn = pause_btn
        self.components.end_action_dropdown = end_action_dropdown

        gr.Markdown("### 快速设置")

        with gr.Row():
            select_all_btn = gr.Button("全选", scale=0)
            unselect_all_btn = gr.Button("清空", scale=0)
            select_produce_only_btn = gr.Button("只选培育", scale=0)
            unselect_produce_only_btn = gr.Button("只不选培育", scale=0)

        with gr.Row(elem_classes=["quick-controls-row"]):
            opts = self.facade.config_service.get_options()
            purchase_quick = gr.Checkbox(label="商店", value=opts.purchase.enabled, interactive=True)
            assignment_quick = gr.Checkbox(label="工作", value=opts.assignment.enabled, interactive=True)
            contest_quick = gr.Checkbox(label="竞赛", value=opts.contest.enabled, interactive=True)
            produce_quick = gr.Checkbox(label="培育", value=opts.produce.enabled, interactive=True)
            mission_reward_quick = gr.Checkbox(label="任务", value=opts.mission_reward.enabled, interactive=True)
            club_reward_quick = gr.Checkbox(label="社团", value=opts.club_reward.enabled, interactive=True)
            activity_funds_quick = gr.Checkbox(label="活动费", value=opts.activity_funds.enabled, interactive=True)
            presents_quick = gr.Checkbox(label="礼物", value=opts.presents.enabled, interactive=True)
            capsule_toys_quick = gr.Checkbox(label="扭蛋", value=opts.capsule_toys.enabled, interactive=True)
            upgrade_support_card_quick = gr.Checkbox(label="支援卡", value=opts.upgrade_support_card.enabled, interactive=True)

        self.components.quick_checkboxes = [
            purchase_quick, assignment_quick, contest_quick, produce_quick,
            mission_reward_quick, club_reward_quick, activity_funds_quick, presents_quick,
            capsule_toys_quick, upgrade_support_card_quick
        ]

        if self.facade._kaa.upgrade_msg:
            gr.Markdown('### 配置升级报告')
            gr.Markdown(self.facade._kaa.upgrade_msg)
        gr.Markdown('脚本报错或者卡住？前往"反馈"选项卡可以快速导出报告！')

        if self.facade.config_service.get_current_user_config().keep_screenshots:
            gr.Markdown(
                '<div style="color: red; font-size: larger;">当前启用了调试功能「保留截图数据」，调试结束后正常使用时建议关闭此选项！</div>'
            )

        task_status_df = gr.Dataframe(headers=["任务", "状态"], label="任务状态")
        self.components.task_status_df = task_status_df

        # --- Event Handlers ---

        def on_run_click():
            if self.facade.task_control_service.is_running_all:
                self.facade.stop_all_tasks()
            else:
                self.facade.start_all_tasks()

        def on_pause_click():
            self.facade.toggle_pause()

        def save_quick_setting(success_msg: str, failed_msg: str):
            """保存快速设置并立即应用"""
            try:
                # 保存配置
                msg = self.facade.save_and_reload_configs()
                # 尝试热重载配置
                gr.Success(success_msg)
            except (ConfigValidationError, RuntimeError) as e:
                gr.Warning(str(e))
            except Exception as e:
                gr.Error(f"保存失败: {e}")

        def update_and_save_quick_setting(field_name: str, value: bool, display_name: str):
            """更新字段，并保存快速设置并立即应用"""
            # 更新配置
            options = self.facade.config_service.get_options()
            parts = field_name.split('.')
            obj = options
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], value)
            save_quick_setting(
                f"✓ {display_name} 已{'启用' if value else '禁用'}",
                f"⚠ {display_name} 设置已保存但重载失败"
            )

        def batch_select(default: bool, produce_only: bool, success_msg: str):
            opts = self.facade.config_service.get_options()
            opts.purchase.enabled = default
            opts.assignment.enabled = default
            opts.contest.enabled = default
            opts.produce.enabled = produce_only
            opts.mission_reward.enabled = default
            opts.club_reward.enabled = default
            opts.activity_funds.enabled = default
            opts.presents.enabled = default
            opts.capsule_toys.enabled = default
            opts.upgrade_support_card.enabled = default
            save_quick_setting(success_msg, "⚠ 数据已保存，但重新加载失败")

        def save_quick_end_action(action: str):
            opts = self.facade.config_service.get_options().end_game
            if action == "完成后关机":
                opts.shutdown = True
                opts.hibernate = False
            elif action == "完成后休眠":
                opts.shutdown = False
                opts.hibernate = True
            else: # This covers "完成后什么都不做"
                opts.shutdown = False
                opts.hibernate = False
            save_quick_setting(f"✓ 完成后操作已设置为 {action}", "⚠ 设置已保存，但重新加载失败")

        # --- UI Callbacks ---
        run_btn.click(fn=on_run_click, outputs=None)
        pause_btn.click(fn=on_pause_click, outputs=None)

        select_all_btn.click(fn=lambda: batch_select(True, True, "✓ 全选成功"), outputs=None)
        unselect_all_btn.click(fn=lambda: batch_select(False, False, "✓ 清空成功"), outputs=None)
        select_produce_only_btn.click(fn=lambda: batch_select(False, True, "✓ 只选培育成功"), outputs=None)
        unselect_produce_only_btn.click(fn=lambda: batch_select(True, False, "✓ 只不选培育成功"), outputs=None)

        # .input is used to only trigger on user interaction
        purchase_quick.input(fn=lambda x: update_and_save_quick_setting('purchase.enabled', x, '商店'), inputs=[purchase_quick])
        assignment_quick.input(fn=lambda x: update_and_save_quick_setting('assignment.enabled', x, '工作'), inputs=[assignment_quick])
        contest_quick.input(fn=lambda x: update_and_save_quick_setting('contest.enabled', x, '竞赛'), inputs=[contest_quick])
        produce_quick.input(fn=lambda x: update_and_save_quick_setting('produce.enabled', x, '培育'), inputs=[produce_quick])
        mission_reward_quick.input(fn=lambda x: update_and_save_quick_setting('mission_reward.enabled', x, '任务奖励'), inputs=[mission_reward_quick])
        club_reward_quick.input(fn=lambda x: update_and_save_quick_setting('club_reward.enabled', x, '社团奖励'), inputs=[club_reward_quick])
        activity_funds_quick.input(fn=lambda x: update_and_save_quick_setting('activity_funds.enabled', x, '活动费'), inputs=[activity_funds_quick])
        presents_quick.input(fn=lambda x: update_and_save_quick_setting('presents.enabled', x, '礼物'), inputs=[presents_quick])
        capsule_toys_quick.input(fn=lambda x: update_and_save_quick_setting('capsule_toys.enabled', x, '扭蛋'), inputs=[capsule_toys_quick])
        upgrade_support_card_quick.input(fn=lambda x: update_and_save_quick_setting('upgrade_support_card.enabled', x, '支援卡升级'), inputs=[upgrade_support_card_quick])
        end_action_dropdown.change(fn=save_quick_end_action, inputs=[end_action_dropdown])


    def _create_task_tab(self):
        """Creates the content for the 'Task' tab for running single tasks."""
        gr.Markdown("## 执行任务")

        # Get all tasks from the facade
        task_names = self.facade.task_control_service.get_all_task_names()
        
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
                self.facade.task_control_service.start_single_task(task_name)
                gr.Info(f"任务 {task_name} 开始执行")
            except ValueError as e:
                gr.Warning(str(e))
            except Exception as e:
                gr.Error(f"启动任务失败: {e}")

        def stop_all_tasks():
            """Event handler to stop the running single task."""
            self.facade.task_control_service.stop_tasks()
            self.facade.idle_mgr.notify_on_stop()

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
            tcs = self.facade.task_control_service
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
            elif not tcs.run_status or not tcs.run_status.running:
                 # Task finished, find final status
                if tcs.run_status and tcs.run_status.tasks:
                    final_status = tcs.run_status.tasks[0]
                    status_map = {'finished': '已完成', 'error': '出错', 'cancelled': '已取消'}
                    status_msg = f"任务 {final_status.task.name} {status_map.get(final_status.status, '已结束')}"

            btn_updates[task_result] = gr.Markdown(value=status_msg)

            # Update pause button
            pause_status = self.facade.get_pause_button_status()
            btn_updates[pause_btn] = gr.Button(value=pause_status['text'], interactive=pause_status['interactive'])
            
            return btn_updates

        gr.Timer(1.0).tick(
            fn=update_task_ui_status,
            outputs=task_buttons + [task_result, pause_btn]
        )

    def _create_produce_tab(self):
        """Creates the content for the 'Produce' tab for managing solutions."""
        gr.Markdown("## 培育管理")

        solutions = self.facade.list_produce_solutions()
        solution_choices = [(f"{sol.name} - {sol.description or '无描述'}", sol.id) for sol in solutions]
        selected_solution_id = self.facade.config_service.get_options().produce.selected_solution_id

        solution_dropdown = gr.Dropdown(
            choices=solution_choices,
            value=selected_solution_id,
            label="选择培育方案",
            interactive=True
        )
        self.components.produce_tab_solution_dropdown = solution_dropdown

        with gr.Row():
            new_solution_btn = gr.Button("新建培育", scale=1)
            delete_solution_btn = gr.Button("删除当前培育", scale=1)

        # Solution details group
        with gr.Group() as solution_settings_group:
            self.components.produce_solution_settings_group = solution_settings_group
            
            solution_name = gr.Textbox(label="方案名称", interactive=True)
            self.components.produce_solution_name = solution_name
            
            solution_description = gr.Textbox(label="方案描述", interactive=True)
            self.components.produce_solution_description = solution_description
            
            produce_mode = gr.Dropdown(choices=["regular", "pro", "master"], label="培育模式", interactive=True)
            self.components.produce_mode = produce_mode
            
            idol_choices = [(f'{idol.name}{f" 「{idol.another_name}」" if idol.is_another and idol.another_name else ""}', idol.skin_id) for idol in IdolCard.all()]
            produce_idols = gr.Dropdown(choices=idol_choices, label="选择要培育的偶像", multiselect=False, interactive=True)
            self.components.produce_idols = produce_idols

            auto_set_memory = gr.Checkbox(label="自动编成回忆", interactive=True)
            self.components.produce_auto_set_memory = auto_set_memory
            
            with gr.Group() as memory_sets_group:
                self.components.produce_memory_sets_group = memory_sets_group
                memory_sets = gr.Dropdown(choices=[str(i) for i in range(1, 21)], label="回忆编成编号", multiselect=False, interactive=True)
                self.components.produce_memory_sets = memory_sets
            
            auto_set_support = gr.Checkbox(label="自动编成支援卡", interactive=True)
            self.components.produce_auto_set_support = auto_set_support
            
            with gr.Group() as support_card_sets_group:
                self.components.produce_support_card_sets_group = support_card_sets_group
                support_card_sets = gr.Dropdown(choices=[str(i) for i in range(1, 21)], label="支援卡编成编号", multiselect=False, interactive=True)
                self.components.produce_support_card_sets = support_card_sets

            use_pt_boost = gr.Checkbox(label="使用支援强化 Pt 提升", interactive=True)
            self.components.produce_use_pt_boost = use_pt_boost
            
            use_note_boost = gr.Checkbox(label="使用笔记数提升", interactive=True)
            self.components.produce_use_note_boost = use_note_boost
            
            follow_producer = gr.Checkbox(label="关注租借了支援卡的制作人", interactive=True)
            self.components.produce_follow_producer = follow_producer
            
            self_study_lesson = gr.Dropdown(choices=['dance', 'visual', 'vocal'], label='文化课自习时选项', interactive=True)
            self.components.produce_self_study_lesson = self_study_lesson
            
            prefer_lesson_ap = gr.Checkbox(label="SP 课程优先", interactive=True)
            self.components.produce_prefer_lesson_ap = prefer_lesson_ap
            
            actions_order = gr.Dropdown(
                choices=[(action.display_name, action.value) for action in ProduceAction],
                label="行动优先级", multiselect=True, interactive=True
            )
            self.components.produce_actions_order = actions_order
            
            recommend_card_detection_mode = gr.Dropdown(
                choices=[(mode.display_name, mode.value) for mode in RecommendCardDetectionMode],
                label="推荐卡检测模式", interactive=True
            )
            self.components.produce_recommend_card_detection_mode = recommend_card_detection_mode
            
            use_ap_drink = gr.Checkbox(label="AP 不足时自动使用 AP 饮料", interactive=True)
            self.components.produce_use_ap_drink = use_ap_drink
            
            skip_commu = gr.Checkbox(label="检测并跳过交流", interactive=True)
            self.components.produce_skip_commu = skip_commu

            save_solution_btn = gr.Button("保存培育方案", variant="primary")

        # --- Event Handlers ---
        
        all_detail_components = [
            solution_settings_group, solution_name, solution_description, produce_mode, produce_idols,
            auto_set_memory, memory_sets_group, memory_sets, auto_set_support, support_card_sets_group,
            support_card_sets, use_pt_boost, use_note_boost, follow_producer, self_study_lesson,
            prefer_lesson_ap, actions_order, recommend_card_detection_mode, use_ap_drink, skip_commu
        ]
        self.components.produce_all_detail_components = all_detail_components

        def on_new_solution():
            """Creates a new solution and refreshes the dropdowns."""
            new_solution = self.facade.create_produce_solution()
            solutions = self.facade.list_produce_solutions()
            choices = [(f"{s.name} - {s.description or '无描述'}", s.id) for s in solutions]
            gr.Success("新培育方案创建成功")
            return {
                solution_dropdown: gr.Dropdown(choices=choices, value=new_solution.id),
                self.components.settings_solution_dropdown: gr.Dropdown(choices=choices)
            }

        def on_delete_solution(solution_id):
            """Deletes the selected solution and refreshes dropdowns."""
            if not solution_id:
                gr.Warning("请先选择要删除的培育方案")
                return {}
            try:
                self.facade.delete_produce_solution(solution_id)
                solutions = self.facade.list_produce_solutions()
                choices = [(f"{s.name} - {s.description or '无描述'}", s.id) for s in solutions]
                gr.Success("培育方案删除成功")
                return {
                    solution_dropdown: gr.Dropdown(choices=choices, value=None),
                    self.components.settings_solution_dropdown: gr.Dropdown(choices=choices)
                }
            except ValueError as e:
                gr.Warning(str(e))
                return {}
            except Exception as e:
                gr.Error(f"删除失败: {e}")
                return {}
        
        def on_save_solution(solution_id, name, desc, mode, idol, auto_mem, mem_set, auto_sup, sup_set, pt_boost, note_boost, follow, study, pref_ap, actions, detect_mode, ap_drink, skip):
            if not solution_id:
                gr.Warning("没有选择要保存的方案")
                return
            try:
                produce_data = ProduceData(
                    mode=mode, idol=idol,
                    auto_set_memory=auto_mem, memory_set=int(mem_set) if mem_set else None,
                    auto_set_support_card=auto_sup, support_card_set=int(sup_set) if sup_set else None,
                    use_pt_boost=pt_boost, use_note_boost=note_boost, follow_producer=follow,
                    self_study_lesson=study, prefer_lesson_ap=pref_ap,
                    actions_order=[ProduceAction(a) for a in actions],
                    recommend_card_detection_mode=RecommendCardDetectionMode(detect_mode),
                    use_ap_drink=ap_drink, skip_commu=skip
                )
                solution = ProduceSolution(id=solution_id, name=name, description=desc, data=produce_data)
                self.facade.save_produce_solution(solution)
                gr.Success("培育方案保存成功")
                # Refresh dropdowns to reflect name/desc changes
                solutions = self.facade.list_produce_solutions()
                choices = [(f"{s.name} - {s.description or '无描述'}", s.id) for s in solutions]
                return {
                    solution_dropdown: gr.Dropdown(choices=choices, value=solution_id),
                    self.components.settings_solution_dropdown: gr.Dropdown(choices=choices)
                }
            except Exception as e:
                gr.Error(f"保存失败: {e}")
                return {}


        # --- UI Callbacks ---
        
        solution_dropdown.change(
            fn=self._update_produce_solution_details,
            inputs=[solution_dropdown],
            outputs=all_detail_components
        )

        auto_set_memory.change(fn=lambda x: gr.Group(visible=not x), inputs=[auto_set_memory], outputs=[memory_sets_group])
        auto_set_support.change(fn=lambda x: gr.Group(visible=not x), inputs=[auto_set_support], outputs=[support_card_sets_group])

        new_solution_btn.click(fn=on_new_solution)
        delete_solution_btn.click(fn=on_delete_solution, inputs=[solution_dropdown])

        save_inputs = [
            solution_dropdown, solution_name, solution_description, produce_mode, produce_idols,
            auto_set_memory, memory_sets, auto_set_support, support_card_sets,
            use_pt_boost, use_note_boost, follow_producer, self_study_lesson,
            prefer_lesson_ap, actions_order, recommend_card_detection_mode,
            use_ap_drink, skip_commu
        ]
        save_solution_btn.click(fn=on_save_solution, inputs=save_inputs)

    
    def _create_settings_tab(self):
        """Creates the content for the 'Settings' tab."""
        gr.Markdown("## 设置")
        save_button = gr.Button("保存设置", variant="primary", scale=0)
        self.components.save_settings_btn = save_button
        
        all_inputs = []

        with gr.Tabs():
            with gr.Tab("基本"):
                emulator_inputs = self._create_emulator_settings()
                all_inputs.extend(emulator_inputs)
                
                start_game_inputs = self._create_start_game_settings()
                all_inputs.extend(start_game_inputs)

            with gr.Tab("日常"):
                purchase_inputs = self._create_purchase_settings()
                all_inputs.extend(purchase_inputs)

                assignment_inputs = self._create_work_settings()
                all_inputs.extend(assignment_inputs)

                contest_inputs = self._create_contest_settings()
                all_inputs.extend(contest_inputs)

                reward_inputs = self._create_reward_settings()
                all_inputs.extend(reward_inputs)
            
            with gr.Tab("培育"):
                produce_inputs = self._create_produce_settings()
                all_inputs.extend(produce_inputs)
            
            with gr.Tab("杂项"):
                misc_inputs = self._create_misc_settings()
                all_inputs.extend(misc_inputs)
                
                idle_inputs = self._create_idle_settings()
                all_inputs.extend(idle_inputs)
            
                end_game_inputs = self._create_end_game_settings()
                all_inputs.extend(end_game_inputs)

        def on_save_click(*args):
            try:
                # This combines all the input components from all settings sections
                # with the actual values passed in *args.
                input_map = dict(zip(all_inputs, args))

                # Get copies of the current config to modify
                user_config = self.facade.config_service.get_current_user_config()
                options_copy = user_config.options.model_copy(deep=True)

                # Each set_func will modify the copies in the wrapper
                for set_func, components_dict in self.config_builders:
                    # Prepare the data dict for this specific setter
                    data_for_setter = {key: input_map[comp] for key, comp in components_dict.items()}
                    data_for_setter = cast(Dict[ConfigKey, Any], data_for_setter)
                    set_func(options_copy, data_for_setter)

                # After all setters have run, update the real config in the service
                self.facade.config_service.get_current_user_config().options = options_copy
                
                # Now, save and reload
                result_message = self.facade.save_and_reload_configs()
                gr.Success(result_message)

            except ConfigValidationError as e:
                gr.Warning(str(e))
            except (RuntimeError, Exception) as e:
                gr.Error(str(e))

        save_button.click(
            fn=on_save_click,
            inputs=all_inputs,
            outputs=None
        )

    def _create_emulator_settings(self) -> List[GradioInput]:
        """Creates the UI for emulator/backend settings."""
        gr.Markdown("### 模拟器设置")
        
        user_config = self.facade.config_service.get_current_user_config()
        backend_config = user_config.backend
        current_tab_id = backend_config.type
        
        backend_type_state = gr.State(value=current_tab_id)

        with gr.Tabs(selected=current_tab_id) as G_backend_tabs:
            with gr.Tab("MuMu 12 v4.x", id="mumu12") as tab_mumu12:
                def _get_mumu_instances_data():
                    choices = []
                    value = None
                    try:
                        instances = Mumu12Host.list()
                        choices = [(i.name, i.id) for i in instances]
                        value = backend_config.instance_id
                    except Exception as e:
                        logger.exception('Failed to list MuMu12 instances')
                        gr.Error("获取 MuMu12 模拟器列表失败，请检查模拟器版本。")
                        # Return empty choices and value on error for initial UI render
                    return choices, value

                # Initialize dropdown with choices and value if 'mumu12' is the current_tab_id
                initial_mumu_choices, initial_mumu_value = ([], None)
                if current_tab_id == 'mumu12':
                    initial_mumu_choices, initial_mumu_value = _get_mumu_instances_data()

                mumu_instance = gr.Dropdown(
                    label="选择多开实例",
                    choices=initial_mumu_choices,
                    value=initial_mumu_value,
                    interactive=True
                )
                mumu_refresh_btn = gr.Button("刷新")
                mumu_background_mode = gr.Checkbox(
                    label="MuMu12 模拟器后台保活模式",
                    value=backend_config.mumu_background_mode,
                    interactive=True
                )
                
                # The click handler can now use the helper function and return a gr.Dropdown.update
                def refresh_mumu_instances_on_click():
                    choices, value = _get_mumu_instances_data()
                    return gr.Dropdown(choices=choices, value=value, interactive=True)
                
                mumu_refresh_btn.click(fn=refresh_mumu_instances_on_click, outputs=[mumu_instance])
            
            tab_mumu12.select(fn=lambda: "mumu12", outputs=backend_type_state)

            with gr.Tab("MuMu 12 v5.x", id="mumu12v5") as tab_mumu12v5:
                def _get_mumu12v5_instances_data():
                    choices = []
                    value = None
                    try:
                        instances = Mumu12V5Host.list()
                        choices = [(i.name, i.id) for i in instances]
                        value = backend_config.instance_id
                    except Exception as e:
                        logger.exception('Failed to list MuMu12v5 instances')
                        gr.Error("获取 MuMu12 v5 模拟器列表失败，请检查模拟器版本。")
                    return choices, value

                initial_mumu12v5_choices, initial_mumu12v5_value = ([], None)
                if current_tab_id == 'mumu12v5':
                    initial_mumu12v5_choices, initial_mumu12v5_value = _get_mumu12v5_instances_data()

                mumu12v5_instance = gr.Dropdown(
                    label="选择多开实例",
                    choices=initial_mumu12v5_choices,
                    value=initial_mumu12v5_value,
                    interactive=True
                )
                mumu12v5_refresh_btn = gr.Button("刷新")
                mumu12v5_background_mode = gr.Checkbox(
                    label="MuMu12v5 模拟器后台保活模式",
                    value=backend_config.mumu_background_mode,
                    interactive=True
                )
                
                def refresh_mumu12v5_instances_on_click():
                    choices, value = _get_mumu12v5_instances_data()
                    return gr.Dropdown(choices=choices, value=value, interactive=True)
                
                mumu12v5_refresh_btn.click(fn=refresh_mumu12v5_instances_on_click, outputs=[mumu12v5_instance])
            
            tab_mumu12v5.select(fn=lambda: "mumu12v5", outputs=backend_type_state)

            with gr.Tab("雷电", id="leidian") as tab_leidian:
                def _get_leidian_instances_data():
                    choices = []
                    value = None
                    try:
                        instances = LeidianHost.list()
                        choices = [(i.name, i.id) for i in instances]
                        value = backend_config.instance_id
                    except Exception:
                        logger.exception('Failed to list Leidian instances')
                        gr.Error("获取雷电模拟器列表失败。")
                    return choices, value

                initial_leidian_choices, initial_leidian_value = ([], None)
                if current_tab_id == 'leidian':
                    initial_leidian_choices, initial_leidian_value = _get_leidian_instances_data()
                
                leidian_instance = gr.Dropdown(
                    label="选择多开实例",
                    choices=initial_leidian_choices,
                    value=initial_leidian_value,
                    interactive=True
                )
                leidian_refresh_btn = gr.Button("刷新")
                
                def refresh_leidian_instances_on_click():
                    choices, value = _get_leidian_instances_data()
                    return gr.Dropdown(choices=choices, value=value, interactive=True)
                
                leidian_refresh_btn.click(fn=refresh_leidian_instances_on_click, outputs=[leidian_instance])
            
            tab_leidian.select(fn=lambda: "leidian", outputs=backend_type_state)

            with gr.Tab("自定义", id="custom") as tab_custom:
                adb_ip = gr.Textbox(value=backend_config.adb_ip, label="ADB IP 地址", interactive=True)
                adb_port = gr.Number(value=backend_config.adb_port, label="ADB 端口", minimum=1, maximum=65535, step=1, interactive=True)
                # check_emulator settings moved to start_game_settings
            
            tab_custom.select(fn=lambda: "custom", outputs=backend_type_state)

            with gr.Tab("DMM", id="dmm") as tab_dmm:
                gr.Markdown("已选中 DMM")
                gr.Markdown("**暂停快捷键 <kbd>Ctrl</kbd> + <kbd>F4</kbd>，停止快捷键 <kbd>Ctrl</kbd> + <kbd>F3</kbd>**")
            
            tab_dmm.select(fn=lambda: "dmm", outputs=backend_type_state)

        screenshot_impl = gr.Dropdown(
            choices=['adb', 'adb_raw', 'uiautomator2', 'windows', 'remote_windows', 'nemu_ipc'],
            value=backend_config.screenshot_impl,
            label="截图方法",
            interactive=True
        )
        
        target_screenshot_interval = gr.Number(
            label="最小截图间隔（秒）",
            value=backend_config.target_screenshot_interval,
            minimum=0, step=0.1, interactive=True
        )

        keep_screenshots = gr.Checkbox(
            label="保留截图数据（调试用）",
            value=user_config.keep_screenshots,
            interactive=True
        )

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            backend = self.facade.config_service.get_current_user_config().backend
            backend.type = data['backend_type']
            
            if backend.type == 'mumu12':
                backend.instance_id = data['_mumu_index']
                backend.mumu_background_mode = data['mumu_background_mode_v4']
            elif backend.type == 'mumu12v5':
                backend.instance_id = data['_mumu12v5_index']
                backend.mumu_background_mode = data['mumu_background_mode_v5']
            elif backend.type == 'leidian':
                backend.instance_id = data['_leidian_index']
            elif backend.type == 'custom':
                backend.instance_id = None
                backend.adb_ip = data['adb_ip']
                backend.adb_port = data['adb_port']
            elif backend.type == 'dmm':
                backend.instance_id = None

            backend.screenshot_impl = data['screenshot_method']
            backend.target_screenshot_interval = data['target_screenshot_interval']
            self.facade.config_service.get_current_user_config().keep_screenshots = data['keep_screenshots']

        components: Dict[ConfigKey, GradioInput] = {
            'backend_type': backend_type_state,
            'adb_ip': adb_ip,
            'adb_port': adb_port,
            'screenshot_method': screenshot_impl,
            'target_screenshot_interval': target_screenshot_interval,
            'keep_screenshots': keep_screenshots,
            '_mumu_index': mumu_instance,
            'mumu_background_mode_v4': mumu_background_mode,
            '_mumu12v5_index': mumu12v5_instance,
            'mumu_background_mode_v5': mumu12v5_background_mode,
            '_leidian_index': leidian_instance,
        }
        self.config_builders.append((set_config, components))
        return list(components.values())
        
    def _create_purchase_settings(self) -> List[GradioInput]:
        """Creates the UI for shop purchase settings."""
        with gr.Column():
            gr.Markdown("### 商店购买设置")
            
            opts = self.facade.config_service.get_options()
            
            purchase_enabled = gr.Checkbox(
                label="启用商店购买",
                value=opts.purchase.enabled
            )
            with gr.Group(visible=opts.purchase.enabled) as purchase_group:
                money_enabled = gr.Checkbox(
                    label="启用金币购买",
                    value=opts.purchase.money_enabled
                )
                money_items = gr.Dropdown(
                    multiselect=True,
                    choices=[(DailyMoneyShopItems.to_ui_text(item), item.value) for item in DailyMoneyShopItems],
                    value=[item.value for item in opts.purchase.money_items],
                    label="金币商店购买物品"
                )
                money_refresh = gr.Checkbox(
                    label="每日一次免费刷新金币商店",
                    value=opts.purchase.money_refresh
                )
                ap_enabled = gr.Checkbox(
                    label="启用AP购买",
                    value=opts.purchase.ap_enabled
                )
                ap_items_map = {
                    APShopItems.PRODUCE_PT_UP: "支援强化点数提升",
                    APShopItems.PRODUCE_NOTE_UP: "笔记数提升",
                    APShopItems.RECHALLENGE: "重新挑战券",
                    APShopItems.REGENERATE_MEMORY: "回忆再生成券"
                }
                selected_ap_items = [ap_items_map[APShopItems(v)] for v in opts.purchase.ap_items]
                ap_items = gr.Dropdown(
                    multiselect=True,
                    choices=list(ap_items_map.values()),
                    value=selected_ap_items,
                    label="AP商店购买物品"
                )

            purchase_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=[purchase_enabled], outputs=[purchase_group])

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            purchase = config.purchase
            purchase.enabled = data['purchase_enabled']
            purchase.money_enabled = data['money_enabled']
            purchase.money_items = data['money_items']
            purchase.money_refresh = data['money_refresh']
            purchase.ap_enabled = data['ap_enabled']
            
            reverse_ap_map = {v: k for k, v in ap_items_map.items()}
            purchase.ap_items = [reverse_ap_map[item].value for item in data['ap_items']]

        components: Dict[ConfigKey, GradioInput] = {
            'purchase_enabled': purchase_enabled,
            'money_enabled': money_enabled,
            'ap_enabled': ap_enabled,
            'ap_items': ap_items,
            'money_items': money_items,
            'money_refresh': money_refresh
        }
        self.config_builders.append((set_config, components))
        return list(components.values())
        
    def _create_work_settings(self) -> List[GradioInput]:
        """Creates the UI for work/assignment settings."""
        with gr.Column():
            gr.Markdown("### 工作设置")
            
            opts = self.facade.config_service.get_options()
            
            assignment_enabled = gr.Checkbox(
                label="启用工作",
                value=opts.assignment.enabled
            )
            with gr.Group(visible=opts.assignment.enabled) as work_group:
                with gr.Row():
                    with gr.Column():
                        mini_live_reassign = gr.Checkbox(
                            label="启用重新分配 MiniLive",
                            value=opts.assignment.mini_live_reassign_enabled
                        )
                        mini_live_duration = gr.Dropdown(
                            choices=[4, 6, 12],
                            value=opts.assignment.mini_live_duration,
                            label="MiniLive 工作时长",
                            interactive=True
                        )
                    with gr.Column():
                        online_live_reassign = gr.Checkbox(
                            label="启用重新分配 OnlineLive",
                            value=opts.assignment.online_live_reassign_enabled
                        )
                        online_live_duration = gr.Dropdown(
                            choices=[4, 6, 12],
                            value=opts.assignment.online_live_duration,
                            label="OnlineLive 工作时长",
                            interactive=True
                        )

            assignment_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=[assignment_enabled], outputs=[work_group])

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            assignment = config.assignment
            assignment.enabled = data['assignment_enabled']
            assignment.mini_live_reassign_enabled = data['mini_live_reassign']
            assignment.mini_live_duration = data['mini_live_duration']
            assignment.online_live_reassign_enabled = data['online_live_reassign']
            assignment.online_live_duration = data['online_live_duration']
        
        components: Dict[ConfigKey, GradioInput] = {
            'assignment_enabled': assignment_enabled,
            'mini_live_reassign': mini_live_reassign,
            'mini_live_duration': mini_live_duration,
            'online_live_reassign': online_live_reassign,
            'online_live_duration': online_live_duration
        }
        self.config_builders.append((set_config, components))
        return list(components.values())

    def _create_contest_settings(self) -> List[GradioInput]:
        """Creates the UI for contest settings."""
        with gr.Column():
            gr.Markdown("### 竞赛设置")
            
            opts = self.facade.config_service.get_options()
            
            contest_enabled = gr.Checkbox(
                label="启用竞赛",
                value=opts.contest.enabled
            )
            with gr.Group(visible=opts.contest.enabled) as contest_group:
                select_which_contestant = gr.Dropdown(
                    choices=[1, 2, 3],
                    value=opts.contest.select_which_contestant,
                    label="选择第几个挑战者",
                    interactive=True
                )

                when_no_set_choices = [
                    ("通知我并跳过竞赛", "remind"),
                    ("提醒我并等待手动编成", "wait"),
                    ("使用自动编成并提醒我", "auto_set"),
                    ("使用自动编成", "auto_set_silent")
                ]
                when_no_set = gr.Dropdown(
                    choices=when_no_set_choices,
                    value=opts.contest.when_no_set,
                    label="竞赛队伍未编成时",
                    interactive=True,
                    info=ContestConfig.model_fields['when_no_set'].description
                )
            contest_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=[contest_enabled], outputs=[contest_group])
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            contest = config.contest
            contest.enabled = data['contest_enabled']
            contest.select_which_contestant = data['select_which_contestant']
            contest.when_no_set = data['when_no_set']

        components: Dict[ConfigKey, GradioInput] = {
            'contest_enabled': contest_enabled,
            'select_which_contestant': select_which_contestant,
            'when_no_set': when_no_set
        }
        self.config_builders.append((set_config, components))
        return list(components.values())
        
    def _create_produce_settings(self) -> List[GradioInput]:
        """Creates the UI for the main produce settings."""
        with gr.Column():
            gr.Markdown("### 培育设置")
            
            opts = self.facade.config_service.get_options()
            
            produce_enabled = gr.Checkbox(
                label="启用培育",
                value=opts.produce.enabled
            )

            with gr.Group(visible=opts.produce.enabled) as produce_group:
                solutions = self.facade.list_produce_solutions()
                solution_choices = [(f"{sol.name} - {sol.description or '无描述'}", sol.id) for sol in solutions]

                solution_dropdown = gr.Dropdown(
                    choices=solution_choices,
                    value=opts.produce.selected_solution_id,
                    label="当前使用的培育方案",
                    interactive=True
                )
                # Share this component with the produce tab
                self.components.settings_solution_dropdown = solution_dropdown

                produce_count = gr.Number(
                    minimum=1,
                    value=opts.produce.produce_count,
                    label="培育次数",
                    interactive=True
                )
                produce_timeout_cd = gr.Number(
                    minimum=20,
                    value=opts.produce.produce_timeout_cd,
                    label="推荐卡检测用时上限",
                    interactive=True,
                    info=ProduceConfig.model_fields['produce_timeout_cd'].description
                )
                interrupt_timeout = gr.Number(
                    minimum=20,
                    value=opts.produce.interrupt_timeout,
                    label="检测超时时间",
                    interactive=True,
                    info=ProduceConfig.model_fields['interrupt_timeout'].description
                )
                enable_fever_month = gr.Radio(
                    label="自动启用强化月间",
                    choices=[("不操作", "ignore"), ("自动启用", "on"), ("自动禁用", "off")],
                    value=opts.produce.enable_fever_month,
                    info=ProduceConfig.model_fields['enable_fever_month'].description,
                    interactive=True
                )

            produce_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=[produce_enabled], outputs=[produce_group])

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            produce = config.produce
            produce.enabled = data['produce_enabled']
            produce.selected_solution_id = data.get('selected_solution_id')
            produce.produce_count = data.get('produce_count', 1)
            produce.produce_timeout_cd = data.get('produce_timeout_cd', 60)
            produce.interrupt_timeout = data.get('interrupt_timeout', 180)
            produce.enable_fever_month = data.get('enable_fever_month', 'ignore')

        components: Dict[ConfigKey, GradioInput] = {
            'produce_enabled': produce_enabled,
            'selected_solution_id': solution_dropdown,
            'produce_count': produce_count,
            'produce_timeout_cd': produce_timeout_cd,
            'interrupt_timeout': interrupt_timeout,
            'enable_fever_month': enable_fever_month
        }
        self.config_builders.append((set_config, components))
        return list(components.values())

    def _create_start_game_settings(self) -> List[GradioInput]:
        """Creates the UI for game start settings."""
        with gr.Column():
            gr.Markdown("### 启动游戏设置")
            
            opts = self.facade.config_service.get_options()
            backend_opts = self.facade.config_service.get_current_user_config().backend

            start_game_enabled = gr.Checkbox(label="启用自动启动游戏", value=opts.start_game.enabled, interactive=True)
            
            with gr.Group(visible=opts.start_game.enabled) as start_game_group:
                start_through_kuyo = gr.Checkbox(label="通过Kuyo来启动游戏", value=opts.start_game.start_through_kuyo, interactive=True)
                game_package_name = gr.Textbox(label="游戏包名", value=opts.start_game.game_package_name, interactive=True)
                kuyo_package_name = gr.Textbox(label="Kuyo包名", value=opts.start_game.kuyo_package_name, interactive=True)
                
                gr.Markdown("#### DMM 设置")
                disable_gakumas_localify = gr.Checkbox(label="自动禁用 Gakumas Localify 汉化", value=opts.start_game.disable_gakumas_localify, interactive=True)
                dmm_game_path = gr.Textbox(label="DMM 版游戏路径 (可选)", value=opts.start_game.dmm_game_path, interactive=True)
                dmm_bypass = gr.Checkbox(label="绕过 DMM 启动器 (实验性)", value=opts.start_game.dmm_bypass, interactive=True)

                gr.Markdown("#### 自定义模拟器启动")
                check_emulator = gr.Checkbox(
                    label="检查并启动模拟器(仅自定义)",
                    value=backend_opts.check_emulator,
                    interactive=True
                )
                with gr.Group(visible=backend_opts.check_emulator) as check_emulator_group:
                    emulator_path = gr.Textbox(value=backend_opts.emulator_path, label="模拟器 exe 文件路径", interactive=True)
                    adb_emulator_name = gr.Textbox(value=backend_opts.adb_emulator_name, label="ADB 模拟器名称", interactive=True)
                    emulator_args = gr.Textbox(value=backend_opts.emulator_args, label="模拟器启动参数", interactive=True)
                check_emulator.change(fn=lambda x: gr.Group(visible=x), inputs=[check_emulator], outputs=[check_emulator_group])

            start_game_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=[start_game_enabled], outputs=[start_game_group])

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            start_game = config.start_game
            backend = self.facade.config_service.get_current_user_config().backend

            start_game.enabled = data['start_game_enabled']
            start_game.start_through_kuyo = data['start_through_kuyo']
            start_game.game_package_name = data['game_package_name']
            start_game.kuyo_package_name = data['kuyo_package_name']
            start_game.disable_gakumas_localify = data['disable_gakumas_localify']
            start_game.dmm_game_path = data['dmm_game_path']
            start_game.dmm_bypass = data['dmm_bypass']

            backend.check_emulator = data['check_emulator']
            backend.emulator_path = data['emulator_path']
            backend.adb_emulator_name = data['adb_emulator_name']
            backend.emulator_args = data['emulator_args']

        components: Dict[ConfigKey, GradioInput] = {
            'start_game_enabled': start_game_enabled,
            'start_through_kuyo': start_through_kuyo,
            'game_package_name': game_package_name,
            'kuyo_package_name': kuyo_package_name,
            'disable_gakumas_localify': disable_gakumas_localify,
            'dmm_game_path': dmm_game_path,
            'dmm_bypass': dmm_bypass,
            'check_emulator': check_emulator,
            'emulator_path': emulator_path,
            'adb_emulator_name': adb_emulator_name,
            'emulator_args': emulator_args
        }
        self.config_builders.append((set_config, components))
        return list(components.values())
        
    def _create_end_game_settings(self) -> List[GradioInput]:
        """Creates the UI for game end settings."""
        with gr.Column():
            gr.Markdown("### 结束游戏设置")
            
            opts = self.facade.config_service.get_options()
            
            exit_kaa = gr.Checkbox(label="退出 kaa", value=opts.end_game.exit_kaa, interactive=True)
            kill_game = gr.Checkbox(label="关闭游戏", value=opts.end_game.kill_game, interactive=True)
            kill_dmm = gr.Checkbox(label="关闭 DMMGamePlayer", value=opts.end_game.kill_dmm, interactive=True)
            kill_emulator = gr.Checkbox(label="关闭模拟器", value=opts.end_game.kill_emulator, interactive=True)
            shutdown = gr.Checkbox(label="关闭系统", value=opts.end_game.shutdown, interactive=True)
            hibernate = gr.Checkbox(label="休眠系统", value=opts.end_game.hibernate, interactive=True)
            restore_gakumas_localify = gr.Checkbox(label="恢复 Gakumas Localify 汉化状态", value=opts.end_game.restore_gakumas_localify, interactive=True)

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            end_game = config.end_game
            end_game.exit_kaa = data['exit_kaa']
            end_game.kill_game = data['kill_game']
            end_game.kill_dmm = data['kill_dmm']
            end_game.kill_emulator = data['kill_emulator']
            end_game.shutdown = data['shutdown']
            end_game.hibernate = data['hibernate']
            end_game.restore_gakumas_localify = data['restore_gakumas_localify']

        components: Dict[ConfigKey, GradioInput] = {
            'exit_kaa': exit_kaa,
            'kill_game': kill_game,
            'kill_dmm': kill_dmm,
            'kill_emulator': kill_emulator,
            'shutdown': shutdown,
            'hibernate': hibernate,
            'restore_gakumas_localify': restore_gakumas_localify,
        }
        self.config_builders.append((set_config, components))
        return list(components.values())
        
    def _create_misc_settings(self) -> List[GradioInput]:
        """Creates the UI for miscellaneous settings."""
        with gr.Column():
            gr.Markdown("### 杂项设置")
            
            opts = self.facade.config_service.get_options()
            
            check_update = gr.Radio(
                label="检查更新时机",
                choices=[("从不", "never"), ("启动时", "startup")],
                value=opts.misc.check_update,
                interactive=True
            )
            auto_install_update = gr.Checkbox(label="自动安装更新", value=opts.misc.auto_install_update, interactive=True)
            expose_to_lan = gr.Checkbox(label="允许局域网访问 Web 界面", value=opts.misc.expose_to_lan, interactive=True)
            update_channel = gr.Radio(
                label="更新通道",
                choices=[("稳定版", "release"), ("测试版", "beta")],
                value=opts.misc.update_channel,
                interactive=True
            )
            log_level = gr.Radio(
                label="日志等级",
                choices=[("普通", "debug"), ("详细", "verbose")],
                value=opts.misc.log_level,
                interactive=True
            )

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            misc = config.misc
            misc.check_update = data['check_update']
            misc.auto_install_update = data['auto_install_update']
            misc.expose_to_lan = data['expose_to_lan']
            misc.update_channel = data['update_channel']
            misc.log_level = data['log_level']

        components: Dict[ConfigKey, GradioInput] = {
            'check_update': check_update,
            'auto_install_update': auto_install_update,
            'expose_to_lan': expose_to_lan,
            'update_channel': update_channel,
            'log_level': log_level
        }
        self.config_builders.append((set_config, components))
        return list(components.values())
        
    def _create_idle_settings(self) -> List[GradioInput]:
        """Creates the UI for idle mode settings."""
        with gr.Column():
            gr.Markdown("### 闲置挂机设置")
            
            opts = self.facade.config_service.get_options()
            
            idle_enabled = gr.Checkbox(label="启用闲置挂机", value=opts.idle.enabled, interactive=True)
            idle_seconds = gr.Number(label="闲置秒数", value=opts.idle.idle_seconds, minimum=1, step=1, interactive=True)
            idle_minimize_on_pause = gr.Checkbox(label="按键暂停时最小化窗口", value=opts.idle.minimize_on_pause, interactive=True)
            
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            idle = config.idle
            idle.enabled = data['idle_enabled']
            idle.idle_seconds = data['idle_seconds']
            idle.minimize_on_pause = data['idle_minimize_on_pause']

        components: Dict[ConfigKey, GradioInput] = {
            'idle_enabled': idle_enabled,
            'idle_seconds': idle_seconds,
            'idle_minimize_on_pause': idle_minimize_on_pause
        }
        self.config_builders.append((set_config, components))
        return list(components.values())
        
    def _create_reward_settings(self) -> List[GradioInput]:
        """Creates the UI for various reward-collection settings."""
        with gr.Column():
            gr.Markdown("### 奖励与领取设置")
            
            opts = self.facade.config_service.get_options()
            
            mission_reward_enabled = gr.Checkbox(label="启用领取任务奖励", value=opts.mission_reward.enabled, interactive=True)
            club_reward_enabled = gr.Checkbox(label="启用领取社团奖励", value=opts.club_reward.enabled, interactive=True)
            presents_enabled = gr.Checkbox(label="启用收取礼物", value=opts.presents.enabled, interactive=True)
            activity_funds_enabled = gr.Checkbox(label="启用收取活动费", value=opts.activity_funds.enabled, interactive=True)
            
            with gr.Group(visible=opts.club_reward.enabled) as club_reward_group:
                selected_note = gr.Dropdown(
                    label="社团奖励笔记选择",
                    choices=[(DailyMoneyShopItems.to_ui_text(item), item.value) for item in DailyMoneyShopItems if "Note" in item.name],
                    value=opts.club_reward.selected_note.value,
                    interactive=True
                )
            club_reward_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=[club_reward_enabled], outputs=[club_reward_group])

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            options = config
            options.mission_reward.enabled = data['mission_reward_enabled']
            options.club_reward.enabled = data['club_reward_enabled']
            options.presents.enabled = data['presents_enabled']
            options.activity_funds.enabled = data['activity_funds_enabled']
            options.club_reward.selected_note = data['selected_note']

        components: Dict[ConfigKey, GradioInput] = {
            'mission_reward_enabled': mission_reward_enabled,
            'club_reward_enabled': club_reward_enabled,
            'presents_enabled': presents_enabled,
            'activity_funds_enabled': activity_funds_enabled,
            'selected_note': selected_note,
        }
        self.config_builders.append((set_config, components))
        return list(components.values())


    def _create_feedback_tab(self) -> None:
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

    def _create_update_tab(self):
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
