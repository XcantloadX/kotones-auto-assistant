import gradio as gr
from kaa.application.ui.facade import KaaFacade, ConfigValidationError
from kaa.application.ui.common import GradioComponents

class StatusView:
    def __init__(self, facade: KaaFacade, components: GradioComponents):
        self.facade = facade
        self.components = components

    def create_ui(self):
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

        with gr.Row():
            task_runtime_text = gr.Textbox(
                label="任务运行时间",
                value="未运行",
                interactive=False,
                scale=1
            )
        self.components.task_runtime_text = task_runtime_text

        task_status_df = gr.Dataframe(headers=["任务", "状态"], label="任务状态")
        self.components.task_status_df = task_status_df

        # --- Event Handlers ---

        def on_run_click():
            if self.facade.task_service.is_running_all:
                self.facade.stop_all_tasks()
            else:
                self.facade.start_all_tasks()

        def on_pause_click():
            self.facade.toggle_pause()

        def save_quick_setting(success_msg: str, failed_msg: str):
            """保存快速设置并立即应用"""
            try:
                # 保存配置
                msg = self.facade.save_configs()
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
