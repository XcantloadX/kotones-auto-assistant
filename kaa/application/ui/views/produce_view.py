import gradio as gr
from kaa.application.ui.facade import KaaFacade
from kaa.application.ui.common import GradioComponents
from kaa.config.produce import ProduceData, ProduceSolution
from kaa.config.const import ProduceAction, RecommendCardDetectionMode
from kaa.db.idol_card import IdolCard

class ProduceView:
    def __init__(self, facade: KaaFacade, components: GradioComponents):
        self.facade = facade
        self.components = components

    def create_ui(self):
        """Creates the content for the 'Produce' tab for managing solutions."""
        gr.Markdown("## 方案管理")

        solutions = self.facade.list_produce_solutions()
        solution_choices = [(f"{sol.name}{f' - {sol.description}' if sol.description else ''}", sol.id) for sol in solutions]

        solution_dropdown = gr.Dropdown(
            choices=solution_choices,
            value=None,
            label="选择培育方案",
            interactive=True
        )
        self.components.produce_tab_solution_dropdown = solution_dropdown

        with gr.Row():
            new_solution_btn = gr.Button("新建培育", scale=1)
            delete_solution_btn = gr.Button("删除当前培育", scale=1)

        # Solution details group
        with gr.Group(visible=False) as solution_settings_group:
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
            new_solution = self.facade.create_produce_solution("新培育方案")
            solutions = self.facade.list_produce_solutions()
            choices = [(f"{s.name}{f' - {s.description}' if s.description else ''}", s.id) for s in solutions]
            gr.Success("新培育方案创建成功")
            # TODO: 创建一个 state 用于记录当前选中的培育 id
            # Return an update for the solution dropdown (use gr.update for better typing)
            return gr.update(choices=choices, value=new_solution.id)

        def on_delete_solution(solution_id):
            """Deletes the selected solution and refreshes dropdowns."""
            if not solution_id:
                gr.Warning("请先选择要删除的培育方案")
                # No change to dropdown
                return gr.update()
            try:
                self.facade.delete_produce_solution(solution_id)
                solutions = self.facade.list_produce_solutions()
                choices = [(f"{s.name}{f' - {s.description}' if s.description else ''}", s.id) for s in solutions]
                gr.Success("培育方案删除成功")
                return gr.update(choices=choices, value=None)
            except ValueError as e:
                gr.Warning(str(e))
                return gr.update()
            except Exception as e:
                gr.Error(f"删除失败: {e}")
                return gr.update()
        
        def on_save_solution(solution_id, name, desc, mode, idol, auto_mem, mem_set, auto_sup, sup_set, pt_boost, note_boost, follow, study, pref_ap, actions, detect_mode, ap_drink, skip):
            if not solution_id:
                gr.Warning("没有选择要保存的方案")
                return gr.update()
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
                return gr.update(choices=choices, value=solution_id)
            except Exception as e:
                gr.Error(f"保存失败: {e}")
                return gr.update()


        # --- UI Callbacks ---
        
        solution_dropdown.change(
            fn=self.update_produce_solution_details,
            inputs=[solution_dropdown],
            outputs=all_detail_components
        )

        auto_set_memory.change(fn=lambda x: gr.update(visible=not x), inputs=[auto_set_memory], outputs=[memory_sets_group])
        auto_set_support.change(fn=lambda x: gr.update(visible=not x), inputs=[auto_set_support], outputs=[support_card_sets_group])

        new_solution_btn.click(fn=on_new_solution, outputs=[solution_dropdown])
        delete_solution_btn.click(fn=on_delete_solution, inputs=[solution_dropdown], outputs=[solution_dropdown])

        save_inputs = [
            solution_dropdown, solution_name, solution_description, produce_mode, produce_idols,
            auto_set_memory, memory_sets, auto_set_support, support_card_sets,
            use_pt_boost, use_note_boost, follow_producer, self_study_lesson,
            prefer_lesson_ap, actions_order, recommend_card_detection_mode,
            use_ap_drink, skip_commu
        ]
        save_solution_btn.click(fn=on_save_solution, inputs=save_inputs, outputs=[solution_dropdown])

    def update_produce_solution_details(self, solution_id: str):
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
