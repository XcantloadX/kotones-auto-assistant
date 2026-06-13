import logging
import datetime
from typing import List, Any, Callable, Optional

import gradio as gr
from kotonebot.client.host import Mumu12Host, Mumu12V5Host, LeidianHost

from kaa.application.ui.components.alert import Alert
from kaa.application.ui.facade import KaaFacade, ConfigValidationError
from kaa.application.ui.common import GradioComponents, GradioInput
from kaa.config.const import DailyMoneyShopItems, APShopItems
from kaa.config.base_config import (
    MuMu12Device, MuMu12V5Device, LeidianDevice, DmmDevice, PlayCoverDevice, CustomDevice,
    AutoConnection, TcpConnection,
)
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

    def _bind_shared(self, component: GradioInput, ref: Ref, shared_getter):
        """将组件绑定到 SharedConfig 中的 Ref，保存时写入 _shared.json。"""
        def on_change(value):
            old = ref.value
            if value == old:
                return

            def update():
                ref.value = value
                self.facade.save_shared_configs(shared_getter())

            return self._handle_config_update(update, success_msg=None)

        if isinstance(component, (gr.Textbox, gr.Number)):
            component.blur(fn=on_change, inputs=component, outputs=self.status_text)
        else:
            component.change(fn=on_change, inputs=component, outputs=self.status_text)

    def _bind(self, component: GradioInput, ref: Ref):
        """
        将组件绑定到配置 Ref。自动选择最佳触发事件。
        :param component: Gradio 组件
        :param ref: 绑定引用对象
        """
        def on_change(value):
            try:
                old = ref.value
            except AttributeError:
                return
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
        gr.Markdown("### 模拟器设置")

        user_config = self.facade.config_service.get_current_user_config()
        backend_config = user_config.backend
        lc = backend_config.lifecycle
        current_tab_id = lc.type

        # ── 辅助：切换 lifecycle 类型并保存 ────────────────────────────────
        _valid_screenshot_methods = {
            'mumu12': ['adb', 'uiautomator2', 'nemu_ipc'],
            'mumu12v5': ['adb', 'uiautomator2', 'nemu_ipc'],
            'leidian': ['adb', 'uiautomator2'],
            'custom': ['adb', 'uiautomator2'],
            'dmm': ['windows', 'windows_background'],
            'playcover': ['macos'],
        }

        def _switch_lifecycle(new_lc, new_conn=None):
            backend_config.lifecycle = new_lc
            if new_conn is not None:
                backend_config.connection = new_conn
            valid = _valid_screenshot_methods.get(new_lc.type, [])
            if backend_config.screenshot_impl not in valid and valid:
                backend_config.screenshot_impl = valid[0]
            self.facade.save_configs()
            return backend_config.screenshot_impl

        # 状态：当前选中的模拟器类型（仅用于 @gr.render 的提示）
        backend_type_state = gr.State(value=current_tab_id)

        comps = {}

        # 各 Tab 记住的实例 ID 状态
        mumu_init = lc.instance_id if lc.type == 'mumu12' else None
        mumu5_init = lc.instance_id if lc.type == 'mumu12v5' else None
        leidian_init = lc.instance_id if lc.type == 'leidian' else None
        mumu_state = gr.State(value=mumu_init)
        mumu5_state = gr.State(value=mumu5_init)
        leidian_state = gr.State(value=leidian_init)

        with gr.Tabs(selected=current_tab_id):
            # --- MuMu 12 ---
            with gr.Tab("MuMu 12 v4.x", id="mumu12") as tab_mumu12:
                gr.Markdown("已选中 MuMu 12 v4.x 模拟器")
                comps['mumu_idx'] = gr.Dropdown(label="选择多开实例", choices=[], interactive=True)
                self._bind(comps['mumu_idx'], ref(of(backend_config).lifecycle.instance_id))
                comps['mumu_idx'].change(lambda x: x, inputs=comps['mumu_idx'], outputs=mumu_state)

                comps['mumu_bg'] = gr.Checkbox(
                    label="MuMu12 模拟器后台保活模式",
                    value=lc.mumu_background_mode if isinstance(lc, (MuMu12Device, MuMu12V5Device)) else False,
                    interactive=True,
                )
                self._bind(comps['mumu_bg'], ref(of(backend_config).lifecycle.mumu_background_mode))

                self._setup_mumu_refresh(tab_mumu12, comps['mumu_idx'], backend_config, 'mumu12', Mumu12Host)

            def _on_mumu12_select(instance_id):
                cur = backend_config.lifecycle
                screenshot = _switch_lifecycle(
                    MuMu12Device(
                        type='mumu12',
                        instance_id=instance_id,
                        mumu_background_mode=cur.mumu_background_mode if isinstance(cur, (MuMu12Device, MuMu12V5Device)) else False,
                        check_and_start=getattr(cur, 'check_and_start', False),
                    ),
                    AutoConnection(type='auto'),
                )
                return 'mumu12', screenshot


            # --- MuMu 12 v5 ---
            with gr.Tab("MuMu 12 v5.x", id="mumu12v5") as tab_mumu12v5:
                gr.Markdown("已选中 MuMu 12 v5.x 模拟器")
                comps['mumu5_idx'] = gr.Dropdown(label="选择多开实例", choices=[], interactive=True)
                self._bind(comps['mumu5_idx'], ref(of(backend_config).lifecycle.instance_id))
                comps['mumu5_idx'].change(lambda x: x, inputs=comps['mumu5_idx'], outputs=mumu5_state)

                comps['mumu5_bg'] = gr.Checkbox(
                    label="MuMu12v5 模拟器后台保活模式",
                    value=lc.mumu_background_mode if isinstance(lc, (MuMu12Device, MuMu12V5Device)) else False,
                    interactive=True,
                )
                self._bind(comps['mumu5_bg'], ref(of(backend_config).lifecycle.mumu_background_mode))

                self._setup_mumu_refresh(tab_mumu12v5, comps['mumu5_idx'], backend_config, 'mumu12v5', Mumu12V5Host)

            def _on_mumu12v5_select(instance_id):
                cur = backend_config.lifecycle
                screenshot = _switch_lifecycle(
                    MuMu12V5Device(
                        type='mumu12v5',
                        instance_id=instance_id,
                        mumu_background_mode=cur.mumu_background_mode if isinstance(cur, (MuMu12Device, MuMu12V5Device)) else False,
                        check_and_start=getattr(cur, 'check_and_start', False),
                    ),
                    AutoConnection(type='auto'),
                )
                return 'mumu12v5', screenshot


            # --- Leidian ---
            with gr.Tab("雷电", id="leidian") as tab_leidian:
                gr.Markdown("已选中雷电模拟器")
                comps['leidian_idx'] = gr.Dropdown(label="选择多开实例", choices=[], interactive=True)
                self._bind(comps['leidian_idx'], ref(of(backend_config).lifecycle.instance_id))
                comps['leidian_idx'].change(lambda x: x, inputs=comps['leidian_idx'], outputs=leidian_state)

                self._setup_mumu_refresh(tab_leidian, comps['leidian_idx'], backend_config, 'leidian', LeidianHost)

            def _on_leidian_select(instance_id):
                cur = backend_config.lifecycle
                conn = backend_config.connection
                screenshot = _switch_lifecycle(
                    LeidianDevice(
                        type='leidian',
                        instance_id=instance_id,
                        adb_emulator_name=cur.adb_emulator_name if isinstance(cur, LeidianDevice) else None,
                        check_and_start=getattr(cur, 'check_and_start', False),
                    ),
                    TcpConnection(
                        type='tcp',
                        ip=conn.ip if isinstance(conn, TcpConnection) else '127.0.0.1',
                        port=conn.port if isinstance(conn, TcpConnection) else 5555,
                    ),
                )
                return 'leidian', screenshot


            # --- Custom ---
            with gr.Tab("自定义", id="custom") as tab_custom:
                conn = backend_config.connection
                comps['adb_ip'] = gr.Textbox(
                    value=conn.ip if isinstance(conn, TcpConnection) else '127.0.0.1',
                    label="ADB IP 地址", interactive=True,
                )
                self._bind(comps['adb_ip'], ref(of(backend_config).connection.ip))

                comps['adb_port'] = gr.Number(
                    value=conn.port if isinstance(conn, TcpConnection) else 5555,
                    label="ADB 端口", minimum=1, maximum=65535, step=1, interactive=True,
                )
                self._bind(comps['adb_port'], ref(of(backend_config).connection.port))

            def _on_custom_select():
                cur = backend_config.lifecycle
                conn = backend_config.connection
                screenshot = _switch_lifecycle(
                    CustomDevice(
                        type='custom',
                        check_and_start=getattr(cur, 'check_and_start', False),
                        emulator_path=cur.emulator_path if isinstance(cur, (CustomDevice, DmmDevice)) else None,
                        emulator_args=cur.emulator_args if isinstance(cur, (CustomDevice, DmmDevice)) else '',
                    ),
                    TcpConnection(
                        type='tcp',
                        ip=conn.ip if isinstance(conn, TcpConnection) else '127.0.0.1',
                        port=conn.port if isinstance(conn, TcpConnection) else 5555,
                    ),
                )
                return 'custom', screenshot


            # --- DMM ---
            with gr.Tab("DMM", id="dmm") as tab_dmm:
                gr.Markdown("已选中 DMM")
                wait_cursor_speed = gr.Number(
                    value=lc.cursor_wait_speed if isinstance(lc, DmmDevice) else -1,
                    label="后台挂机时光标最大速度（像素/秒）",
                    info="""使用 DMM 版后台挂机功能时，在点击前会尝试等待光标静止，以避免发生点击偏移。
此项规定了速度小于多少时认为光标静止，单位为像素/秒。

-1 表示使用内置默认值，0 表示禁用该功能。
值越大，等待时间越短，脚本响应越快，但点击偏移风险上升，可能导致误点击而卡住。
值越小，等待时间越长，脚本响应越慢，但点击偏移风险下降，稳定性更好。
""",
                    minimum=-1, step=0.1, interactive=True,
                )
                self._bind(wait_cursor_speed, ref(of(backend_config).lifecycle.cursor_wait_speed))
                gr.Button('重置游戏窗口位置', scale=1).click(self.facade.instance_service.reset_game_window)

            def _on_dmm_select():
                cur = backend_config.lifecycle
                screenshot = _switch_lifecycle(DmmDevice(
                    type='dmm',
                    check_and_start=getattr(cur, 'check_and_start', False),
                    emulator_path=getattr(cur, 'emulator_path', None),
                    emulator_args=getattr(cur, 'emulator_args', ''),
                    cursor_wait_speed=cur.cursor_wait_speed if isinstance(cur, DmmDevice) else -1,
                    windows_window_title=cur.windows_window_title if isinstance(cur, DmmDevice) else 'gakumas',
                    windows_ahk_path=cur.windows_ahk_path if isinstance(cur, DmmDevice) else None,
                ))
                return 'dmm', screenshot


            # --- PlayCover ---
            with gr.Tab("PlayCover (macOS)", id="playcover") as tab_playcover:
                gr.Markdown("已选中 PlayCover (macOS)。将自动寻找已安装的 iOS 应用。请确保在下方截图方法中选择 `macos`。")

            def _on_playcover_select():
                screenshot = _switch_lifecycle(PlayCoverDevice(type='playcover'))
                return 'playcover', screenshot


        # 通用设置
        comps['screenshot'] = gr.Dropdown(
            choices=[
                ('adb - 模拟器通用', 'adb'),
                ('uiautomator2 - 模拟器通用', 'uiautomator2'),
                ('windows - DMM 版前台挂机', 'windows'),
                ('windows_background - DMM 版后台挂机（实验性）', 'windows_background'),
                ('nemu_ipc - MuMu 模拟器专属（推荐）', 'nemu_ipc'),
                ('macos - macOS 原生窗口控制', 'macos')
            ],
            value=backend_config.screenshot_impl, label="截图方法", interactive=True
        )
        self._bind(comps['screenshot'], ref(of(backend_config).screenshot_impl))

        # tab.select 注册放在 screenshot dropdown 定义之后，以便加入 outputs
        tab_mumu12.select(fn=_on_mumu12_select, inputs=[mumu_state], outputs=[backend_type_state, comps['screenshot']])
        tab_mumu12v5.select(fn=_on_mumu12v5_select, inputs=[mumu5_state], outputs=[backend_type_state, comps['screenshot']])
        tab_leidian.select(fn=_on_leidian_select, inputs=[leidian_state], outputs=[backend_type_state, comps['screenshot']])
        tab_custom.select(fn=_on_custom_select, outputs=[backend_type_state, comps['screenshot']])
        tab_dmm.select(fn=_on_dmm_select, outputs=[backend_type_state, comps['screenshot']])
        tab_playcover.select(fn=_on_playcover_select, outputs=[backend_type_state, comps['screenshot']])

        @gr.render(inputs=[comps['screenshot'], backend_type_state])
        def _tip(impl: str, backend_type: str):
            if not impl or not backend_type:
                return

            is_mumu = 'mumu' in backend_type

            if backend_type == 'playcover':
                if impl != 'macos':
                    Alert(
                        title="提示",
                        value="PlayCover 仅支持 `macos` 截图方式",
                        variant="warning",
                        show_close=False
                    )

            # 1. 检查 DMM 兼容性
            if backend_type == 'dmm':
                if impl != 'windows' and impl != 'windows_background':
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
                elif is_mumu and impl in ['adb', 'uiautomator2']:
                    Alert(
                        title="提示",
                        value="MuMu 模拟器推荐使用 `nemu_ipc` 截图方式，性能更佳且更稳定",
                        variant="info",
                        show_close=False
                    )
                elif impl in ['windows', 'windows_background', 'macos']:
                    Alert(
                        title="提示",
                        value="模拟器不支持 `windows` 或 `macos` 相关的原生截图方式，建议使用 `adb` 或 `nemu_ipc`",
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
                lc = config.lifecycle
                is_current = lc.type == type_key
                current_id = lc.instance_id if is_current and hasattr(lc, 'instance_id') else None
                choices = [(i.name, i.id) for i in instances]
                return gr.Dropdown(choices=choices, value=current_id, interactive=True), gr.Markdown(visible=False)
            except Exception:
                return gr.Dropdown(choices=[], interactive=True), gr.Markdown(visible=True)

        refresh_btn.click(fn=refresh, outputs=[dropdown, refresh_msg])

        # 自动加载
        lc = config.lifecycle
        if lc.type == type_key and hasattr(lc, 'instance_id') and lc.instance_id:
            try:
                instances = host_cls.list()
                dropdown.choices = [(i.name, i.id) for i in instances]
                dropdown.value = lc.instance_id
                refresh_msg.visible = False
            except:
                pass

    def _create_purchase_settings(self):
        """Creates the UI for shop purchase settings."""
        with gr.Column():
            gr.Markdown("### 商店购买设置")
            opts = self.facade.config_service.get_options()

            # --- 1. 启用主开关 ---
            purchase_enabled = gr.Checkbox(label="启用商店购买", value=opts.tasks.purchase.enabled)
            self._bind(purchase_enabled, ref(of(opts).tasks.purchase.enabled))

            with gr.Group(visible=opts.tasks.purchase.enabled) as purchase_group:
                # 绑定可见性
                purchase_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=purchase_enabled, outputs=purchase_group)

                # --- 2. 金币购买 ---
                money_enabled = gr.Checkbox(label="启用金币购买", value=opts.tasks.purchase.money_enabled)
                self._bind(money_enabled, ref(of(opts).tasks.purchase.money_enabled))

                with gr.Group(visible=opts.tasks.purchase.money_enabled) as money_group:
                    money_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=money_enabled, outputs=money_group)

                    money_items = gr.Dropdown(
                        multiselect=True,
                        choices=[(DailyMoneyShopItems.to_ui_text(item), item.value) for item in DailyMoneyShopItems],
                        value=[item.value for item in opts.tasks.purchase.money_items],
                        label="金币商店购买物品"
                    )
                    self._bind(money_items, ref(of(opts).tasks.purchase.money_items))

                    money_refresh = gr.Checkbox(label="每日一次免费刷新金币商店", value=opts.tasks.purchase.money_refresh)
                    self._bind(money_refresh, ref(of(opts).tasks.purchase.money_refresh))

                # --- 3. AP 购买 ---
                ap_enabled = gr.Checkbox(label="启用AP购买", value=opts.tasks.purchase.ap_enabled)
                self._bind(ap_enabled, ref(of(opts).tasks.purchase.ap_enabled))

                ap_items_map = {
                    APShopItems.PRODUCE_PT_UP: "支援强化点数提升",
                    APShopItems.PRODUCE_NOTE_UP: "笔记数提升",
                    APShopItems.RECHALLENGE: "重新挑战券",
                    APShopItems.REGENERATE_MEMORY: "回忆再生成券"
                }

                with gr.Group(visible=opts.tasks.purchase.ap_enabled) as ap_group:
                    ap_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=ap_enabled, outputs=ap_group)

                    # 直接使用 (label, value) 的 choices，避免文本到枚举的二次转换
                    ap_choices = [(label, item.value) for item, label in ap_items_map.items()]
                    ap_values = [v for v in opts.tasks.purchase.ap_items]
                    ap_items = gr.Dropdown(
                        multiselect=True,
                        choices=ap_choices,
                        value=ap_values,
                        label="AP商店购买物品",
                        interactive=True
                    )

                    # 直接保存选中的值列表（Dropdown 返回的是 value 列表）
                    self._bind(ap_items, ref(of(opts).tasks.purchase.ap_items))

                # --- 4. 每周免费礼包 ---
                weekly_enabled = gr.Checkbox(label="启用每周免费礼包购买", value=opts.tasks.purchase.weekly_enabled)
                self._bind(weekly_enabled, ref(of(opts).tasks.purchase.weekly_enabled))

    def _create_work_settings(self):
        """Creates the UI for work/assignment settings."""
        with gr.Column():
            gr.Markdown("### 工作设置")
            opts = self.facade.config_service.get_options()

            assignment_enabled = gr.Checkbox(label="启用工作", value=opts.tasks.assignment.enabled)
            self._bind(assignment_enabled, ref(of(opts).tasks.assignment.enabled))

            with gr.Group(visible=opts.tasks.assignment.enabled) as work_group:
                assignment_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=assignment_enabled, outputs=work_group)

                with gr.Row():
                    with gr.Column():
                        mini_re = gr.Checkbox(label="启用重新分配 MiniLive", value=opts.tasks.assignment.mini_live_reassign_enabled)
                        self._bind(mini_re, ref(of(opts).tasks.assignment.mini_live_reassign_enabled))

                        mini_dur = gr.Dropdown(choices=[4, 6, 12], value=opts.tasks.assignment.mini_live_duration, label="MiniLive 工作时长", interactive=True)
                        self._bind(mini_dur, ref(of(opts).tasks.assignment.mini_live_duration))

                    with gr.Column():
                        online_re = gr.Checkbox(label="启用重新分配 OnlineLive", value=opts.tasks.assignment.online_live_reassign_enabled)
                        self._bind(online_re, ref(of(opts).tasks.assignment.online_live_reassign_enabled))

                        online_dur = gr.Dropdown(choices=[4, 6, 12], value=opts.tasks.assignment.online_live_duration, label="OnlineLive 工作时长", interactive=True)
                        self._bind(online_dur, ref(of(opts).tasks.assignment.online_live_duration))

    def _create_contest_settings(self):
        with gr.Column():
            gr.Markdown("### 竞赛设置")
            opts = self.facade.config_service.get_options()

            contest_enabled = gr.Checkbox(label="启用竞赛", value=opts.tasks.contest.enabled)
            self._bind(contest_enabled, ref(of(opts).tasks.contest.enabled))

            with gr.Group(visible=opts.tasks.contest.enabled) as contest_group:
                contest_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=contest_enabled, outputs=contest_group)

                sel = gr.Dropdown(choices=[1, 2, 3], value=opts.tasks.contest.select_which_contestant, label="选择第几个挑战者", interactive=True)
                self._bind(sel, ref(of(opts).tasks.contest.select_which_contestant))

                when_no_set_choices = [
                    ("通知我并跳过竞赛", "remind"), ("提醒我并等待手动编成", "wait"),
                    ("使用自动编成并提醒我", "auto_set"), ("使用自动编成", "auto_set_silent")
                ]
                when_no_set = gr.Dropdown(choices=when_no_set_choices, value=opts.tasks.contest.when_no_set, label="竞赛队伍未编成时", interactive=True)
                self._bind(when_no_set, ref(of(opts).tasks.contest.when_no_set))

    def _create_produce_settings(self):
        with gr.Column():
            gr.Markdown("### 培育设置")
            opts = self.facade.config_service.get_options()
            solutions = self.facade.list_produce_solutions()

            produce_enabled = gr.Checkbox(label="启用培育", value=opts.tasks.produce.enabled)
            self._bind(produce_enabled, ref(of(opts).tasks.produce.enabled))

            if not solutions:
                alert = Alert("你似乎还没有创建任何培育方案。你需要先到「方案」里创建一个！", "提示", action_text="去创建")
                alert.click(fn=lambda: gr.Tabs(selected="produce"), inputs=[], outputs=[self.components.tabs])

            with gr.Group(visible=opts.tasks.produce.enabled) as produce_group:
                produce_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=produce_enabled, outputs=produce_group)

                solution_choices = [(f"{sol.name} - {sol.description or '无描述'}", sol.id) for sol in solutions]
                sol_drop = gr.Dropdown(choices=solution_choices, value=opts.tasks.produce.selected_solution_id, label="当前使用的培育方案", interactive=True)
                self.components.settings_solution_dropdown = sol_drop
                self._bind(sol_drop, ref(of(opts).tasks.produce.selected_solution_id))

                cnt = gr.Number(minimum=1, value=opts.tasks.produce.produce_count, label="培育次数", interactive=True)
                self._bind(cnt, ref(of(opts).tasks.produce.produce_count))

                tm_cd = gr.Number(minimum=20, value=opts.tasks.produce.produce_timeout_cd, label="推荐卡检测用时上限", interactive=True)
                self._bind(tm_cd, ref(of(opts).tasks.produce.produce_timeout_cd))

                int_tm = gr.Number(minimum=20, value=opts.tasks.produce.interrupt_timeout, label="检测超时时间", interactive=True)
                self._bind(int_tm, ref(of(opts).tasks.produce.interrupt_timeout))

                fever = gr.Radio(label="培育前开启活动模式", choices=[("不操作", "ignore"), ("自动启用", "on"), ("自动禁用", "off")], value=opts.tasks.produce.enable_fever_month, interactive=True, info="某些活动期间，在选择培育模式/难度页面的切换活动开关")
                self._bind(fever, ref(of(opts).tasks.produce.enable_fever_month))

                engine = gr.Radio(
                    label="培育引擎",
                    choices=[("新版·实验性", "new"), ("旧版培育", "legacy")],
                    value=opts.tasks.produce.produce_engine,
                    interactive=True,
                )
                self._bind(engine, ref(of(opts).tasks.produce.produce_engine))

    def _create_start_game_settings(self):
        with gr.Column():
            gr.Markdown("### 启动游戏设置")
            opts = self.facade.config_service.get_options()
            backend_opts = self.facade.config_service.get_current_user_config().backend
            lc = backend_opts.lifecycle

            start_game_enabled = gr.Checkbox(label="启用自动启动游戏", value=opts.tasks.start_game.enabled, interactive=True)
            self._bind(start_game_enabled, ref(of(opts).tasks.start_game.enabled))

            with gr.Group(visible=opts.tasks.start_game.enabled) as sg_group:
                start_game_enabled.change(fn=lambda x: gr.Group(visible=x), inputs=start_game_enabled, outputs=sg_group)

                # DMM Components
                d1 = gr.Checkbox(label="自动禁用 Gakumas Localify 汉化", value=opts.tasks.start_game.disable_gakumas_localify, interactive=True)
                self._bind(d1, ref(of(opts).tasks.start_game.disable_gakumas_localify))

                d2 = gr.Textbox(label="DMM 版游戏路径 (可选)", value=opts.tasks.start_game.dmm_game_path, interactive=True, placeholder="如：F:\\Games\\gakumas\\gakumas.exe。留空自动识别。")
                self._bind(d2, ref(of(opts).tasks.start_game.dmm_game_path))

                d3 = gr.Checkbox(label="绕过 DMM 启动器", value=opts.tasks.start_game.dmm_bypass, interactive=True)
                self._bind(d3, ref(of(opts).tasks.start_game.dmm_bypass))

                # Emulator Check Components
                check_emu = gr.Checkbox(label="自动启动模拟器", value=getattr(lc, 'check_and_start', False), interactive=True)
                self._bind(check_emu, ref(of(backend_opts).lifecycle.check_and_start))

                kuyo = gr.Checkbox(label="通过Kuyo来启动游戏", value=opts.tasks.start_game.start_through_kuyo, interactive=True)
                self._bind(kuyo, ref(of(opts).tasks.start_game.start_through_kuyo))

                pkg = gr.Textbox(label="游戏包名", value=opts.tasks.start_game.game_package_name, interactive=True)
                self._bind(pkg, ref(of(opts).tasks.start_game.game_package_name))

                with gr.Group(visible=getattr(lc, 'check_and_start', False)) as check_emu_group:
                    check_emu.change(fn=lambda x: gr.Group(visible=x), inputs=check_emu, outputs=check_emu_group)

                    # emulator_path / emulator_args 仅 Custom / DMM 支持
                    if isinstance(lc, (CustomDevice, DmmDevice)):
                        e1 = gr.Textbox(value=lc.emulator_path, label="模拟器 exe 文件路径", interactive=True)
                        self._bind(e1, ref(of(backend_opts).lifecycle.emulator_path))

                        e3 = gr.Textbox(value=lc.emulator_args, label="模拟器启动参数", interactive=True)
                        self._bind(e3, ref(of(backend_opts).lifecycle.emulator_args))
                    else:
                        gr.Markdown("*MuMu / 雷电模拟器通过 SDK 自动启动，无需配置 exe 路径。*")

                    # adb_emulator_name 仅雷电支持
                    if isinstance(lc, LeidianDevice):
                        e2 = gr.Textbox(value=lc.adb_emulator_name, label="ADB 模拟器名称（雷电专用）", interactive=True)
                        self._bind(e2, ref(of(backend_opts).lifecycle.adb_emulator_name))

    def _create_end_game_settings(self):
        with gr.Column():
            gr.Markdown("### 全部任务结束后")
            gr.Markdown("*注：执行单个任务不会触发下面这些，只有状态页的启动按钮才会触发*")
            opts = self.facade.config_service.get_options()

            items = [
                ("退出 kaa", of(opts).tasks.end_game.exit_kaa),
                ("关闭游戏", of(opts).tasks.end_game.kill_game),
                ("关闭 DMMGamePlayer", of(opts).tasks.end_game.kill_dmm),
                ("关闭模拟器", of(opts).tasks.end_game.kill_emulator),
                ("关闭系统", of(opts).tasks.end_game.shutdown),
                ("休眠系统", of(opts).tasks.end_game.hibernate),
                ("恢复 Gakumas Localify 汉化状态", of(opts).tasks.end_game.restore_gakumas_localify)
            ]
            for label, proxy in items:
                comp = gr.Checkbox(label=label, value=getter(proxy)(), interactive=True)
                self._bind(comp, ref(proxy))

    def _create_misc_settings(self):
        with gr.Column():
            gr.Markdown("### 杂项设置")
            shared = self.facade.config_service.get_shared()
            misc = shared.misc

            c1 = gr.Radio(label="检查更新时机", choices=[("从不", "never"), ("启动时", "startup")], value=misc.check_update, interactive=True)
            self._bind_shared(c1, ref(of(misc).check_update), lambda: shared)

            c2 = gr.Checkbox(label="自动安装更新", value=misc.auto_install_update, interactive=True)
            self._bind_shared(c2, ref(of(misc).auto_install_update), lambda: shared)

            c3 = gr.Checkbox(label="允许局域网访问 Web 界面", value=misc.expose_to_lan, interactive=True)
            self._bind_shared(c3, ref(of(misc).expose_to_lan), lambda: shared)

            c4 = gr.Radio(label="更新通道", choices=[("稳定版", "release"), ("测试版", "beta")], value=misc.update_channel, interactive=True)
            self._bind_shared(c4, ref(of(misc).update_channel), lambda: shared)

            c5 = gr.Radio(label="日志等级", choices=[("普通", "debug"), ("详细", "verbose")], value=misc.log_level, interactive=True)
            self._bind_shared(c5, ref(of(misc).log_level), lambda: shared)

            c7 = gr.Radio(
                label="游戏资源检查时机",
                choices=[("手动", "manual"), ("每次启动", "startup"), ("每天一次", "daily"), ("每周一次", "weekly")],
                value=misc.game_data_check,
                interactive=True,
            )
            self._bind_shared(c7, ref(of(misc).game_data_check), lambda: shared)

            game_data_output = gr.Textbox(label="游戏资源检查进度", interactive=False, lines=4, visible=False)
            def _check_game_data():
                yield from ((gr.Textbox(value=text, visible=True)) for text in self.facade.check_game_data())
            gr.Button("立即检查游戏资源").click(
                fn=_check_game_data,
                outputs=game_data_output,
            )

            gr.Markdown("#### 匿名数据收集")
            gr.Markdown("""目前收集的数据包含：
* 发生错误时的错误类型和堆栈信息

**收集的数据将仅用于分析和改进 kaa。你可以随时在下面启用或禁用数据收集**。
            """)
            c6 = gr.Checkbox(label="自动发送匿名错误报告", value=bool(shared.telemetry.sentry), interactive=True)
            self._bind_shared(c6, ref(of(shared.telemetry).sentry), lambda: shared)

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

            r1 = gr.Checkbox(label="领取任务奖励", value=opts.tasks.mission_reward.enabled, interactive=True)
            self._bind(r1, ref(of(opts).tasks.mission_reward.enabled))

            club_en = gr.Checkbox(label="领取社团奖励", value=opts.tasks.club_reward.enabled, interactive=True)
            self._bind(club_en, ref(of(opts).tasks.club_reward.enabled))

            r3 = gr.Checkbox(label="收取礼物", value=opts.tasks.presents.enabled, interactive=True)
            self._bind(r3, ref(of(opts).tasks.presents.enabled))

            r4 = gr.Checkbox(label="收取活动费", value=opts.tasks.activity_funds.enabled, interactive=True)
            self._bind(r4, ref(of(opts).tasks.activity_funds.enabled))

            with gr.Group(visible=opts.tasks.club_reward.enabled) as club_group:
                club_en.change(fn=lambda x: gr.Group(visible=x), inputs=club_en, outputs=club_group)

                note = gr.Dropdown(
                    label="社团奖励笔记选择",
                    choices=[(DailyMoneyShopItems.to_ui_text(item), item.value) for item in DailyMoneyShopItems if "Note" in item.name],
                    value=opts.tasks.club_reward.selected_note.value,
                    interactive=True
                )
                self._bind(note, ref(of(opts).tasks.club_reward.selected_note))

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
