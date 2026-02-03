import logging
import datetime
from typing import List, Any, Callable, Optional

import gradio as gr
from kotonebot.client.host import Mumu12Host, Mumu12V5Host, LeidianHost

from kaa.application.ui.components.alert import Alert
from kaa.application.ui.facade import KaaFacade, ConfigValidationError
from kaa.application.ui.common import GradioComponents, GradioInput
from kaa.config.const import DailyMoneyShopItems, APShopItems
from kaa.util.reactive import Ref, getter, setter, of, ref

logger = logging.getLogger(__name__)

class SettingsView:
    def __init__(self, facade: KaaFacade, components: GradioComponents, config_builders: List[Any]):
        self.facade = facade
        self.components = components
        self.config_builders = config_builders 
        self.status_text = None
        self.facade.save_configs()

    def _handle_config_update(self, update_fn: Callable[[], None], success_msg: Optional[str] = '保存成功') -> str:
        """
        统一处理配置更新、保存和错误捕获的 Helper 方法。
        :param update_fn: 执行配置修改的函数（闭包）
        :return: 状态提示文本
        """
        try:
            # 1. 执行具体的修改逻辑
            update_fn()
            
            # 2. 保存 (持久化)
            self.facade.save_configs()
            
            # 3. 反馈
            if success_msg:
                gr.Info(success_msg)
            
            time_str = datetime.datetime.now().strftime("%H:%M:%S")
            return f"*设置已保存: {time_str}*"
            
        except ConfigValidationError as e:
            # 恢复配置到修改前 (重载磁盘上的配置以覆盖内存中的无效修改)
            # self.facade.config_service.reload()
            gr.Warning(f"{str(e)}")
            return "*保存失败*"
        except Exception as e:
            # 恢复配置
            # self.facade.config_service.reload()
            logger.exception("Failed to update settings")
            gr.Warning(f"保存失败，已还原: {str(e)}")
            return "*保存失败*"

    def _bind(self, component: GradioInput, ref: Ref):
        """
        将组件绑定到配置 Ref。自动选择最佳触发事件。
        :param component: Gradio 组件
        :param ref: 绑定引用对象
        """
        def on_change(value):
            old = ref.value
            if value == old:
                return
            else:
                def update():
                    ref.value = value
                return self._handle_config_update(update)

        # 文本框和数字框使用 blur (失焦) 触发，防止输入中途频繁保存
        if isinstance(component, (gr.Textbox, gr.Number)):
            component.blur(fn=on_change, inputs=component, outputs=self.status_text)
        else:
            # Checkbox, Dropdown, Radio 使用 change 触发
            component.change(fn=on_change, inputs=component, outputs=self.status_text)

    def create_ui(self):
        """Creates the content for the 'Settings' tab."""
        gr.Markdown("## 设置")
        self.status_text = gr.Markdown("*设置修改后将自动保存并即时生效。*", elem_classes=["text-gray-500", "text-sm"])

        with gr.Tabs():
            with gr.Tab("基本"):
                self._create_emulator_settings()
                self._create_start_game_settings()
                self._create_end_game_settings()

            with gr.Tab("日常"):
                self._create_purchase_settings()
                self._create_work_settings()
                self._create_contest_settings()
                self._create_reward_settings()
            
            with gr.Tab("培育"):
                self._create_produce_settings()
            
            with gr.Tab("杂项"):
                self._create_misc_settings()
                self._create_idle_settings()
                self._create_debug_settings()

    def _create_emulator_settings(self):
        """Creates the UI for emulator/backend settings."""
        # 模拟器设置比较特殊，因为多个组件相互依赖（如 Type 决定 Instance ID）
        # 改为使用 _bind + 状态同步的方式
        gr.Markdown("### 模拟器设置")
        
        user_config = self.facade.config_service.get_current_user_config()
        backend_config = user_config.backend
        current_tab_id = backend_config.type
        
        # 状态：当前选中的模拟器类型
        backend_type_state = gr.State(value=current_tab_id)
        self._bind(backend_type_state, ref(of(backend_config).type))

        # 状态：用于在切换 Tab 时传递 instance_id
        instance_id_state = gr.State()
        self._bind(instance_id_state, ref(of(backend_config).instance_id))

        # 状态：用于记录各个 Tab 的 Dropdown 选中值，解决 Tab 切换时无法获取 hidden 组件值的问题
        mumu_init = backend_config.instance_id if backend_config.type == 'mumu12' else None
        mumu_state = gr.State(value=mumu_init)
        
        mumu5_init = backend_config.instance_id if backend_config.type == 'mumu12v5' else None
        mumu5_state = gr.State(value=mumu5_init)
        
        leidian_init = backend_config.instance_id if backend_config.type == 'leidian' else None
        leidian_state = gr.State(value=leidian_init)

        # 定义组件容器
        comps = {}

        with gr.Tabs(selected=current_tab_id):
            # --- MuMu 12 ---
            with gr.Tab("MuMu 12 v4.x", id="mumu12") as tab_mumu12:
                gr.Markdown("已选中 MuMu 12 v4.x 模拟器")
                comps['mumu_idx'] = gr.Dropdown(label="选择多开实例", choices=[], interactive=True)
                self._bind(comps['mumu_idx'], ref(of(backend_config).instance_id))
                comps['mumu_idx'].change(lambda x: x, inputs=comps['mumu_idx'], outputs=mumu_state)

                comps['mumu_bg'] = gr.Checkbox(
                    label="MuMu12 模拟器后台保活模式", value=backend_config.mumu_background_mode, interactive=True
                )
                self._bind(comps['mumu_bg'], ref(of(backend_config).mumu_background_mode))

                self._setup_mumu_refresh(tab_mumu12, comps['mumu_idx'], backend_config, 'mumu12', Mumu12Host)

            tab_mumu12.select(
                fn=lambda x: ("mumu12", x), 
                inputs=[mumu_state], 
                outputs=[backend_type_state, instance_id_state]
            )

            # --- MuMu 12 v5 ---
            with gr.Tab("MuMu 12 v5.x", id="mumu12v5") as tab_mumu12v5:
                gr.Markdown("已选中 MuMu 12 v5.x 模拟器")
                comps['mumu5_idx'] = gr.Dropdown(label="选择多开实例", choices=[], interactive=True)
                self._bind(comps['mumu5_idx'], ref(of(backend_config).instance_id))
                comps['mumu5_idx'].change(lambda x: x, inputs=comps['mumu5_idx'], outputs=mumu5_state)

                comps['mumu5_bg'] = gr.Checkbox(
                    label="MuMu12v5 模拟器后台保活模式", value=backend_config.mumu_background_mode, interactive=True
                )
                self._bind(comps['mumu5_bg'], ref(of(backend_config).mumu_background_mode))

                self._setup_mumu_refresh(tab_mumu12v5, comps['mumu5_idx'], backend_config, 'mumu12v5', Mumu12V5Host)

            tab_mumu12v5.select(
                fn=lambda x: ("mumu12v5", x), 
                inputs=[mumu5_state], 
                outputs=[backend_type_state, instance_id_state]
            )

            # --- Leidian ---
            with gr.Tab("雷电", id="leidian") as tab_leidian:
                gr.Markdown("已选中雷电模拟器")
                comps['leidian_idx'] = gr.Dropdown(label="选择多开实例", choices=[], interactive=True)
                self._bind(comps['leidian_idx'], ref(of(backend_config).instance_id))
                comps['leidian_idx'].change(lambda x: x, inputs=comps['leidian_idx'], outputs=leidian_state)

                self._setup_mumu_refresh(tab_leidian, comps['leidian_idx'], backend_config, 'leidian', LeidianHost)
            
            tab_leidian.select(
                fn=lambda x: ("leidian", x), 
                inputs=[leidian_state], 
                outputs=[backend_type_state, instance_id_state]
            )

            # --- Custom ---
            with gr.Tab("自定义", id="custom") as tab_custom:
                comps['adb_ip'] = gr.Textbox(value=backend_config.adb_ip, label="ADB IP 地址", interactive=True)
                self._bind(comps['adb_ip'], ref(of(backend_config).adb_ip))

                comps['adb_port'] = gr.Number(value=backend_config.adb_port, label="ADB 端口", minimum=1, maximum=65535, step=1, interactive=True)
                self._bind(comps['adb_port'], ref(of(backend_config).adb_port))
            
            tab_custom.select(
                fn=lambda: ("custom", None), 
                outputs=[backend_type_state, instance_id_state]
            )

            # --- DMM ---
            with gr.Tab("DMM", id="dmm") as tab_dmm:
                gr.Markdown("已选中 DMM")
                wait_cursor_speed = gr.Number(
                    value=user_config.backend.cursor_wait_speed,
                    label="后台挂机时光标最大速度（像素/秒）",
                    info="""使用 DMM 版后台挂机功能时，在点击前会尝试等待光标静止，以避免发生点击偏移。
此项规定了速度小于多少时认为光标静止，单位为像素/秒。

-1 表示使用内置默认值，0 表示禁用该功能。
值越大，等待时间越短，脚本响应越快，但点击偏移风险上升，可能导致误点击而卡住。
值越小，等待时间越长，脚本响应越慢，但点击偏移风险下降，稳定性更好。
""",
                    minimum=-1, step=0.1, interactive=True
                )
                self._bind(wait_cursor_speed, ref(of(user_config.backend).cursor_wait_speed))
                gr.Button('重置游戏窗口位置', scale=1).click(self.facade.instance_service.reset_game_window)
            
            tab_dmm.select(
                fn=lambda: ("dmm", None), 
                outputs=[backend_type_state, instance_id_state]
            )

        # 通用设置
        comps['screenshot'] = gr.Dropdown(
            choices=[
                ('adb - 模拟器通用', 'adb'),
                ('adb_raw（已废弃勿选）', 'adb_raw'),
                ('uiautomator2 - 模拟器通用', 'uiautomator2'),
                ('windows - DMM 版前台挂机', 'windows'),
                ('remote_windows（调试专用勿选）', 'remote_windows'),
                ('windows_background - DMM 版后台挂机（实验性）', 'windows_background'),
                ('nemu_ipc - MuMu 模拟器专属（推荐）', 'nemu_ipc')
            ],
            value=backend_config.screenshot_impl, label="截图方法", interactive=True
        )
        self._bind(comps['screenshot'], ref(of(backend_config).screenshot_impl))

        @gr.render(inputs=[comps['screenshot'], backend_type_state])
        def _tip(impl: str, backend_type: str):
            if not impl or not backend_type:
                return

            is_mumu = 'mumu' in backend_type
            # 1. 检查 DMM 兼容性
            if backend_type == 'dmm':
                if impl != 'windows' and impl != 'remote_windows' and impl != 'windows_background':
                    Alert(
                        title="提示", 
                        value="DMM 版本仅支持 `windows` 或 `windows_background` 截图方式",
                        variant="warning",
                        show_close=False
                    )
            
            # 2. 检查模拟器兼容性
            else:
                if impl == 'nemu_ipc' and not is_mumu:
                    Alert(
                        title="提示",
                        value="`nemu_ipc` 仅适用于 MuMu 模拟器，其他模拟器请选择 `adb` 或 `uiautomator`",
                        variant="warning",
                        show_close=False
                    )
                elif is_mumu and impl in ['adb', 'adb_raw', 'uiautomator2']:
                    Alert(
                        title="提示",
                        value="MuMu 模拟器推荐使用 `nemu_ipc` 截图方式，性能更佳且更稳定",
                        variant="info",
                        show_close=False
                    )
                elif impl in ['windows', 'remote_windows', 'windows_background']:
                    Alert(
                        title="提示",
                        value="模拟器不支持 `windows` 截图方式，建议使用 `adb` 或 `nemu_ipc`",
                        variant="warning",
                        show_close=False
                    )

        comps['interval'] = gr.Number(
            label="最小截图间隔（秒）", value=backend_config.target_screenshot_interval, minimum=0, step=0.1, interactive=True
        )
        self._bind(comps['interval'], ref(of(backend_config).target_screenshot_interval))
        
    def _setup_mumu_refresh(self, tab, dropdown, config, type_key, host_cls):
        # (辅助方法：为了简化主代码逻辑，将原本的刷新按钮逻辑抽取出来)
        refresh_msg = gr.Markdown("<div style='color: red;'>点击下方「刷新」按钮载入信息</div>", visible=True)
        refresh_btn = gr.Button("刷新")
        
        def refresh():
            try:
                instances = host_cls.list()
                is_current = config.type == type_key
                current_id = config.instance_id if is_current else None
                choices = [(i.name, i.id) for i in instances]
                return gr.Dropdown(choices=choices, value=current_id, interactive=True), gr.Markdown(visible=False)
            except Exception:
                return gr.Dropdown(choices=[], interactive=True), gr.Markdown(visible=True)

        refresh_btn.click(fn=refresh, outputs=[dropdown, refresh_msg])
        
        # 自动加载
        if config.type == type_key and config.instance_id:
            try:
                instances = host_cls.list()
                dropdown.choices = [(i.name, i.id) for i in instances]
                dropdown.value = config.instance_id
                refresh_msg.visible = False
            except:
                pass

    def _create_purchase_settings(self):
        """Creates the UI for shop purchase settings."""
        with gr.Column():
            gr.Markdown("### 商店购买设置")
            opts = self.facade.config_service.get_options()
            
            # --- 1. 启用主开关 ---
            purchase_enabled = gr.Checkbox(label="启用商店购买", value=opts.purchase.enabled)
            self._bind(purchase_enabled, ref(of(opts).purchase.enabled))

            with gr.Group(visible=opts.purchase.enabled) as purchase_group:
                # 绑定可见性
                purchase_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=purchase_enabled, outputs=purchase_group)
                
                # --- 2. 金币购买 ---
                money_enabled = gr.Checkbox(label="启用金币购买", value=opts.purchase.money_enabled)
                self._bind(money_enabled, ref(of(opts).purchase.money_enabled))

                with gr.Group(visible=opts.purchase.money_enabled) as money_group:
                    money_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=money_enabled, outputs=money_group)
                    
                    money_items = gr.Dropdown(
                        multiselect=True,
                        choices=[(DailyMoneyShopItems.to_ui_text(item), item.value) for item in DailyMoneyShopItems],
                        value=[item.value for item in opts.purchase.money_items],
                        label="金币商店购买物品"
                    )
                    self._bind(money_items, ref(of(opts).purchase.money_items))

                    money_refresh = gr.Checkbox(label="每日一次免费刷新金币商店", value=opts.purchase.money_refresh)
                    self._bind(money_refresh, ref(of(opts).purchase.money_refresh))

                # --- 3. AP 购买 ---
                ap_enabled = gr.Checkbox(label="启用AP购买", value=opts.purchase.ap_enabled)
                self._bind(ap_enabled, ref(of(opts).purchase.ap_enabled))

                ap_items_map = {
                    APShopItems.PRODUCE_PT_UP: "支援强化点数提升",
                    APShopItems.PRODUCE_NOTE_UP: "笔记数提升",
                    APShopItems.RECHALLENGE: "重新挑战券",
                    APShopItems.REGENERATE_MEMORY: "回忆再生成券"
                }

                with gr.Group(visible=opts.purchase.ap_enabled) as ap_group:
                    ap_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=ap_enabled, outputs=ap_group)

                    # 直接使用 (label, value) 的 choices，避免文本到枚举的二次转换
                    ap_choices = [(label, item.value) for item, label in ap_items_map.items()]
                    ap_values = [v for v in opts.purchase.ap_items]
                    ap_items = gr.Dropdown(
                        multiselect=True,
                        choices=ap_choices,
                        value=ap_values,
                        label="AP商店购买物品",
                        interactive=True
                    )

                    # 直接保存选中的值列表（Dropdown 返回的是 value 列表）
                    self._bind(ap_items, ref(of(opts).purchase.ap_items))

                # --- 4. 每周免费礼包 ---
                weekly_enabled = gr.Checkbox(label="启用每周免费礼包购买", value=opts.purchase.weekly_enabled)
                self._bind(weekly_enabled, ref(of(opts).purchase.weekly_enabled))

    def _create_work_settings(self):
        """Creates the UI for work/assignment settings."""
        with gr.Column():
            gr.Markdown("### 工作设置")
            opts = self.facade.config_service.get_options()
            
            assignment_enabled = gr.Checkbox(label="启用工作", value=opts.assignment.enabled)
            self._bind(assignment_enabled, ref(of(opts).assignment.enabled))

            with gr.Group(visible=opts.assignment.enabled) as work_group:
                assignment_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=assignment_enabled, outputs=work_group)
                
                with gr.Row():
                    with gr.Column():
                        mini_re = gr.Checkbox(label="启用重新分配 MiniLive", value=opts.assignment.mini_live_reassign_enabled)
                        self._bind(mini_re, ref(of(opts).assignment.mini_live_reassign_enabled))
                        
                        mini_dur = gr.Dropdown(choices=[4, 6, 12], value=opts.assignment.mini_live_duration, label="MiniLive 工作时长", interactive=True)
                        self._bind(mini_dur, ref(of(opts).assignment.mini_live_duration))

                    with gr.Column():
                        online_re = gr.Checkbox(label="启用重新分配 OnlineLive", value=opts.assignment.online_live_reassign_enabled)
                        self._bind(online_re, ref(of(opts).assignment.online_live_reassign_enabled))
                        
                        online_dur = gr.Dropdown(choices=[4, 6, 12], value=opts.assignment.online_live_duration, label="OnlineLive 工作时长", interactive=True)
                        self._bind(online_dur, ref(of(opts).assignment.online_live_duration))

    def _create_contest_settings(self):
        with gr.Column():
            gr.Markdown("### 竞赛设置")
            opts = self.facade.config_service.get_options()
            
            contest_enabled = gr.Checkbox(label="启用竞赛", value=opts.contest.enabled)
            self._bind(contest_enabled, ref(of(opts).contest.enabled))

            with gr.Group(visible=opts.contest.enabled) as contest_group:
                contest_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=contest_enabled, outputs=contest_group)

                sel = gr.Dropdown(choices=[1, 2, 3], value=opts.contest.select_which_contestant, label="选择第几个挑战者", interactive=True)
                self._bind(sel, ref(of(opts).contest.select_which_contestant))

                when_no_set_choices = [
                    ("通知我并跳过竞赛", "remind"), ("提醒我并等待手动编成", "wait"),
                    ("使用自动编成并提醒我", "auto_set"), ("使用自动编成", "auto_set_silent")
                ]
                when_no_set = gr.Dropdown(choices=when_no_set_choices, value=opts.contest.when_no_set, label="竞赛队伍未编成时", interactive=True)
                self._bind(when_no_set, ref(of(opts).contest.when_no_set))

    def _create_produce_settings(self):
        with gr.Column():
            gr.Markdown("### 培育设置")
            opts = self.facade.config_service.get_options()
            solutions = self.facade.list_produce_solutions()
            
            produce_enabled = gr.Checkbox(label="启用培育", value=opts.produce.enabled)
            self._bind(produce_enabled, ref(of(opts).produce.enabled))

            if not solutions:
                alert = Alert("你似乎还没有创建任何培育方案。你需要先到「方案」里创建一个！", "提示", action_text="去创建")
                alert.click(fn=lambda: gr.Tabs(selected="produce"), inputs=[], outputs=[self.components.tabs])

            with gr.Group(visible=opts.produce.enabled) as produce_group:
                produce_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=produce_enabled, outputs=produce_group)
                
                solution_choices = [(f"{sol.name} - {sol.description or '无描述'}", sol.id) for sol in solutions]
                sol_drop = gr.Dropdown(choices=solution_choices, value=opts.produce.selected_solution_id, label="当前使用的培育方案", interactive=True)
                self.components.settings_solution_dropdown = sol_drop
                self._bind(sol_drop, ref(of(opts).produce.selected_solution_id))

                cnt = gr.Number(minimum=1, value=opts.produce.produce_count, label="培育次数", interactive=True)
                self._bind(cnt, ref(of(opts).produce.produce_count))

                tm_cd = gr.Number(minimum=20, value=opts.produce.produce_timeout_cd, label="推荐卡检测用时上限", interactive=True)
                self._bind(tm_cd, ref(of(opts).produce.produce_timeout_cd))
                
                int_tm = gr.Number(minimum=20, value=opts.produce.interrupt_timeout, label="检测超时时间", interactive=True)
                self._bind(int_tm, ref(of(opts).produce.interrupt_timeout))

                fever = gr.Radio(label="培育前开启活动模式", choices=[("不操作", "ignore"), ("自动启用", "on"), ("自动禁用", "off")], value=opts.produce.enable_fever_month, interactive=True, info="某些活动期间，在选择培育模式/难度页面的切换活动开关")
                self._bind(fever, ref(of(opts).produce.enable_fever_month))

    def _create_start_game_settings(self):
        with gr.Column():
            gr.Markdown("### 启动游戏设置")
            opts = self.facade.config_service.get_options()
            backend_opts = self.facade.config_service.get_current_user_config().backend

            start_game_enabled = gr.Checkbox(label="启用自动启动游戏", value=opts.start_game.enabled, interactive=True)
            self._bind(start_game_enabled, ref(of(opts).start_game.enabled))

            with gr.Group(visible=opts.start_game.enabled) as sg_group:
                start_game_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=start_game_enabled, outputs=sg_group)

                # DMM Components
                d1 = gr.Checkbox(label="自动禁用 Gakumas Localify 汉化", value=opts.start_game.disable_gakumas_localify, interactive=True)
                self._bind(d1, ref(of(opts).start_game.disable_gakumas_localify))
                
                d2 = gr.Textbox(label="DMM 版游戏路径 (可选)", value=opts.start_game.dmm_game_path, interactive=True, placeholder="如：F:\\Games\\gakumas\\gakumas.exe。留空自动识别。")
                self._bind(d2, ref(of(opts).start_game.dmm_game_path))
                
                d3 = gr.Checkbox(label="绕过 DMM 启动器", value=opts.start_game.dmm_bypass, interactive=True)
                self._bind(d3, ref(of(opts).start_game.dmm_bypass))

                # Emulator Check Components
                check_emu = gr.Checkbox(label="自动启动模拟器", value=backend_opts.check_emulator, interactive=True)
                self._bind(check_emu, ref(of(backend_opts).check_emulator))
                
                kuyo = gr.Checkbox(label="通过Kuyo来启动游戏", value=opts.start_game.start_through_kuyo, interactive=True)
                self._bind(kuyo, ref(of(opts).start_game.start_through_kuyo))
                
                pkg = gr.Textbox(label="游戏包名", value=opts.start_game.game_package_name, interactive=True)
                self._bind(pkg, ref(of(opts).start_game.game_package_name))

                with gr.Group(visible=backend_opts.check_emulator) as check_emu_group:
                    check_emu.change(fn=lambda x: gr.Group(visible=x), inputs=check_emu, outputs=check_emu_group)
                    
                    e1 = gr.Textbox(value=backend_opts.emulator_path, label="模拟器 exe 文件路径", interactive=True)
                    self._bind(e1, ref(of(backend_opts).emulator_path))
                    
                    e2 = gr.Textbox(value=backend_opts.adb_emulator_name, label="ADB 模拟器名称", interactive=True)
                    self._bind(e2, ref(of(backend_opts).adb_emulator_name))
                    
                    e3 = gr.Textbox(value=backend_opts.emulator_args, label="模拟器启动参数", interactive=True)
                    self._bind(e3, ref(of(backend_opts).emulator_args))

    def _create_end_game_settings(self):
        with gr.Column():
            gr.Markdown("### 全部任务结束后")
            gr.Markdown("*注：执行单个任务不会触发下面这些，只有状态页的启动按钮才会触发*")
            opts = self.facade.config_service.get_options()
            
            items = [
                ("退出 kaa", of(opts).end_game.exit_kaa),
                ("关闭游戏", of(opts).end_game.kill_game),
                ("关闭 DMMGamePlayer", of(opts).end_game.kill_dmm),
                ("关闭模拟器", of(opts).end_game.kill_emulator),
                ("关闭系统", of(opts).end_game.shutdown),
                ("休眠系统", of(opts).end_game.hibernate),
                ("恢复 Gakumas Localify 汉化状态", of(opts).end_game.restore_gakumas_localify)
            ]
            for label, proxy in items:
                comp = gr.Checkbox(label=label, value=getter(proxy)(), interactive=True)
                self._bind(comp, ref(proxy))

    def _create_misc_settings(self):
        with gr.Column():
            gr.Markdown("### 杂项设置")
            opts = self.facade.config_service.get_options()
            
            c1 = gr.Radio(label="检查更新时机", choices=[("从不", "never"), ("启动时", "startup")], value=opts.misc.check_update, interactive=True)
            self._bind(c1, ref(of(opts).misc.check_update))
            
            c2 = gr.Checkbox(label="自动安装更新", value=opts.misc.auto_install_update, interactive=True)
            self._bind(c2, ref(of(opts).misc.auto_install_update))
            
            c3 = gr.Checkbox(label="允许局域网访问 Web 界面", value=opts.misc.expose_to_lan, interactive=True)
            self._bind(c3, ref(of(opts).misc.expose_to_lan))
            
            c4 = gr.Radio(label="更新通道", choices=[("稳定版", "release"), ("测试版", "beta")], value=opts.misc.update_channel, interactive=True)
            self._bind(c4, ref(of(opts).misc.update_channel))
            
            c5 = gr.Radio(label="日志等级", choices=[("普通", "debug"), ("详细", "verbose")], value=opts.misc.log_level, interactive=True)
            self._bind(c5, ref(of(opts).misc.log_level))

    def _create_idle_settings(self):
        with gr.Column():
            gr.Markdown("### 闲置挂机设置")
            opts = self.facade.config_service.get_options()
            
            i1 = gr.Checkbox(label="启用闲置挂机", value=opts.idle.enabled, interactive=True)
            self._bind(i1, ref(of(opts).idle.enabled))
            
            i2 = gr.Number(label="闲置秒数", value=opts.idle.idle_seconds, minimum=1, step=1, interactive=True)
            self._bind(i2, ref(of(opts).idle.idle_seconds))
            
            i3 = gr.Checkbox(label="按键暂停时最小化窗口", value=opts.idle.minimize_on_pause, interactive=True)
            self._bind(i3, ref(of(opts).idle.minimize_on_pause))

    def _create_reward_settings(self):
        with gr.Column():
            gr.Markdown("### 奖励领取设置")
            opts = self.facade.config_service.get_options()
            
            r1 = gr.Checkbox(label="领取任务奖励", value=opts.mission_reward.enabled, interactive=True)
            self._bind(r1, ref(of(opts).mission_reward.enabled))
            
            club_en = gr.Checkbox(label="领取社团奖励", value=opts.club_reward.enabled, interactive=True)
            self._bind(club_en, ref(of(opts).club_reward.enabled))
            
            r3 = gr.Checkbox(label="收取礼物", value=opts.presents.enabled, interactive=True)
            self._bind(r3, ref(of(opts).presents.enabled))
            
            r4 = gr.Checkbox(label="收取活动费", value=opts.activity_funds.enabled, interactive=True)
            self._bind(r4, ref(of(opts).activity_funds.enabled))

            with gr.Group(visible=opts.club_reward.enabled) as club_group:
                club_en.change(fn=lambda x: gr.Group(visible=x), inputs=club_en, outputs=club_group)
                
                note = gr.Dropdown(
                    label="社团奖励笔记选择",
                    choices=[(DailyMoneyShopItems.to_ui_text(item), item.value) for item in DailyMoneyShopItems if "Note" in item.name],
                    value=opts.club_reward.selected_note.value,
                    interactive=True
                )
                self._bind(note, ref(of(opts).club_reward.selected_note))

    def _create_debug_settings(self):
        with gr.Column():
            gr.Markdown("### 调试设置")
            gr.Markdown('<div style="color: red;">仅供调试使用。正常运行时务必关闭下面所有的选项。</div>')
            
            user_config = self.facade.config_service.get_current_user_config()
            opts = self.facade.config_service.get_options()

            keep_ss = gr.Checkbox(
                label="保留截图数据",
                value=user_config.keep_screenshots,
                interactive=True
            )
            self._bind(keep_ss, ref(of(user_config).keep_screenshots))

            trace_rec = gr.Checkbox(
                label="跟踪推荐卡检测",
                value=opts.trace.recommend_card_detection,
                interactive=True
            )
            self._bind(trace_rec, ref(of(opts).trace.recommend_card_detection))
