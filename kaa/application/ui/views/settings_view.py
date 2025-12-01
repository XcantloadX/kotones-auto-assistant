import gradio as gr
from typing import List, Dict, Any, cast
from kaa.application.ui.facade import KaaFacade, ConfigValidationError
from kaa.application.ui.common import GradioComponents, GradioInput, ConfigKey, ConfigBuilderReturnValue
from kaa.config.schema import BaseConfig, ContestConfig, ProduceConfig
from kaa.config.const import DailyMoneyShopItems, APShopItems
from kotonebot.client.host import Mumu12Host, Mumu12V5Host, LeidianHost
import logging

logger = logging.getLogger(__name__)

class SettingsView:
    def __init__(self, facade: KaaFacade, components: GradioComponents, config_builders: List[ConfigBuilderReturnValue]):
        self.facade = facade
        self.components = components
        self.config_builders = config_builders

    def create_ui(self):
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
