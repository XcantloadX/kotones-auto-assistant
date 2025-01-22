import queue
import logging
from threading import Lock
from typing import List, Dict, Tuple, Literal

import gradio as gr

from kotonebot.backend.core import task_registry
from kotonebot.config.manager import load_config, save_config
from kotonebot.tasks.common import (
    BaseConfig, APShopItems, PurchaseConfig, ActivityFundsConfig,
    PresentsConfig, AssignmentConfig, ContestConfig, ProduceConfig,
    MissionRewardConfig
)
from kotonebot.config.base_config import UserConfig, BackendConfig

logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
logging.getLogger("kotonebot").setLevel(logging.DEBUG)

class KotoneBotUI:
    def __init__(self) -> None:
        self.is_running: bool = False
        self.log_queue: queue.Queue = queue.Queue()
        self.log_lock: Lock = Lock()
        self._setup_logger()
        
    def _setup_logger(self) -> None:
        class QueueHandler(logging.Handler):
            def __init__(self, queue: queue.Queue) -> None:
                super().__init__()
                self.queue = queue

            def emit(self, record: logging.LogRecord) -> None:
                self.queue.put(self.format(record))

        # 创建日志处理器
        queue_handler = QueueHandler(self.log_queue)
        queue_handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] %(message)s'))
        
        # 获取 kotonebot 的根日志记录器
        logger = logging.getLogger("kotonebot")
        logger.addHandler(queue_handler)
        logger.setLevel(logging.DEBUG)

    def get_logs(self, log_output: str) -> str:
        logs: List[str] = []
        while not self.log_queue.empty():
            try:
                log = self.log_queue.get_nowait()
                logs.append(log)
            except queue.Empty:
                break
        return log_output + "\n" + "\n".join(logs)
    
    def get_button_status(self) -> str:
        if not hasattr(self, 'run_status'):
            return "启动"
        
        if not self.run_status.running:
            self.is_running = False
            return "启动"
        return "停止"

    def update_task_status(self) -> List[List[str]]:
        status_list: List[List[str]] = []
        if not hasattr(self, 'run_status'):
            for task_name, task in task_registry.items():
                status_list.append([task.name, "等待中"])
            return status_list
        
        for task_status in self.run_status.tasks:
            status_text = {
                'pending': '等待中',
                'running': '运行中',
                'finished': '已完成',
                'error': '出错',
                'cancelled': '已取消'
            }.get(task_status.status, '未知')
            status_list.append([task_status.task.name, status_text])
        return status_list

    def toggle_run(self) -> Tuple[str, List[List[str]]]:
        if not self.is_running:
            return self.start_run()
        return self.stop_run()
    
    def start_run(self) -> Tuple[str, List[List[str]]]:
        self.is_running = True
        from kotonebot.run.run import initialize, start
        initialize('kotonebot.tasks')
        self.run_status = start(config_type=BaseConfig)
        return "停止", self.update_task_status()

    def stop_run(self) -> Tuple[str, List[List[str]]]:
        self.is_running = False
        return "启动", self.update_task_status()

    def save_settings(
        self,
        adb_ip: str,
        adb_port: int,
        purchase_enabled: bool,
        money_enabled: bool,
        ap_enabled: bool,
        ap_items: List[str],
        activity_funds_enabled: bool,
        presents_enabled: bool,
        assignment_enabled: bool,
        mini_live_reassign: bool,
        mini_live_duration: Literal[4, 6, 12],
        online_live_reassign: bool,
        online_live_duration: Literal[4, 6, 12],
        contest_enabled: bool,
        produce_enabled: bool,
        produce_mode: Literal["regular"],
        produce_count: int,
        auto_set_memory: bool,
        auto_set_support: bool,
        use_pt_boost: bool,
        use_note_boost: bool,
        follow_producer: bool,
        mission_reward_enabled: bool
    ) -> str:
        ap_items_enum: List[Literal[0, 1, 2, 3]] = []
        ap_items_map: Dict[str, APShopItems] = {
            "获取支援强化 Pt 提升": APShopItems.PRODUCE_PT_UP,
            "获取笔记数提升": APShopItems.PRODUCE_NOTE_UP,
            "再挑战券": APShopItems.RECHALLENGE,
            "回忆再生成券": APShopItems.REGENERATE_MEMORY
        }
        for item in ap_items:
            if item in ap_items_map:
                ap_items_enum.append(ap_items_map[item].value)  # type: ignore
        
        self.current_config.backend.adb_ip = adb_ip
        self.current_config.backend.adb_port = adb_port
        
        options = BaseConfig(
            purchase=PurchaseConfig(
                enabled=purchase_enabled,
                money_enabled=money_enabled,
                ap_enabled=ap_enabled,
                ap_items=ap_items_enum
            ),
            activity_funds=ActivityFundsConfig(
                enabled=activity_funds_enabled
            ),
            presents=PresentsConfig(
                enabled=presents_enabled
            ),
            assignment=AssignmentConfig(
                enabled=assignment_enabled,
                mini_live_reassign_enabled=mini_live_reassign,
                mini_live_duration=mini_live_duration,
                online_live_reassign_enabled=online_live_reassign,
                online_live_duration=online_live_duration
            ),
            contest=ContestConfig(
                enabled=contest_enabled
            ),
            produce=ProduceConfig(
                enabled=produce_enabled,
                mode=produce_mode,
                produce_count=produce_count,
                auto_set_memory=auto_set_memory,
                auto_set_support_card=auto_set_support,
                use_pt_boost=use_pt_boost,
                use_note_boost=use_note_boost,
                follow_producer=follow_producer
            ),
            mission_reward=MissionRewardConfig(
                enabled=mission_reward_enabled
            )
        )
        
        self.current_config.options = options
        
        try:
            save_config(self.config, "config.json")
            return "设置已保存！"
        except Exception as e:
            return f"保存设置失败：{str(e)}"

    def _create_status_tab(self) -> None:
        with gr.Tab("状态"):
            gr.Markdown("## 状态")
            progress_bar = gr.Progress()
            
            with gr.Row():
                run_btn = gr.Button("启动", scale=1)
                debug_btn = gr.Button("调试", scale=1)
            
            task_status = gr.Dataframe(
                headers=["任务", "状态"],
                value=self.update_task_status(),
                label="任务状态"
            )
            
            def on_run_click(evt: gr.EventData) -> Tuple[str, List[List[str]]]:
                return self.toggle_run()
            
            run_btn.click(
                fn=on_run_click,
                outputs=[run_btn, task_status]
            )

            # 添加定时器，分别更新按钮状态和任务状态
            gr.Timer(1.0).tick(
                fn=self.get_button_status,
                outputs=[run_btn]
            )
            gr.Timer(1.0).tick(
                fn=self.update_task_status,
                outputs=[task_status]
            )

    def _create_purchase_settings(self) -> Tuple[gr.Checkbox, gr.Checkbox, gr.Checkbox, gr.Dropdown]:
        with gr.Column():
            gr.Markdown("### 商店购买设置")
            purchase_enabled = gr.Checkbox(
                label="启用商店购买",
                value=self.current_config.options.purchase.enabled
            )
            with gr.Group(visible=self.current_config.options.purchase.enabled) as purchase_group:
                money_enabled = gr.Checkbox(
                    label="启用金币购买",
                    value=self.current_config.options.purchase.money_enabled
                )
                ap_enabled = gr.Checkbox(
                    label="启用AP购买",
                    value=self.current_config.options.purchase.ap_enabled
                )
                
                # 转换枚举值为显示文本
                selected_items: List[str] = []
                ap_items_map = {
                    APShopItems.PRODUCE_PT_UP: "获取支援强化 Pt 提升",
                    APShopItems.PRODUCE_NOTE_UP: "获取笔记数提升",
                    APShopItems.RECHALLENGE: "再挑战券",
                    APShopItems.REGENERATE_MEMORY: "回忆再生成券"
                }
                for item_value in self.current_config.options.purchase.ap_items:
                    item_enum = APShopItems(item_value)
                    if item_enum in ap_items_map:
                        selected_items.append(ap_items_map[item_enum])
                
                ap_items = gr.Dropdown(
                    multiselect=True,
                    choices=list(ap_items_map.values()),
                    value=selected_items,
                    label="AP商店购买物品"
                )
            
            purchase_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[purchase_enabled],
                outputs=[purchase_group]
            )
        return purchase_enabled, money_enabled, ap_enabled, ap_items

    def _create_work_settings(self) -> Tuple[gr.Checkbox, gr.Checkbox, gr.Dropdown, gr.Checkbox, gr.Dropdown]:
        with gr.Column():
            gr.Markdown("### 工作设置")
            assignment_enabled = gr.Checkbox(
                label="启用工作",
                value=self.current_config.options.assignment.enabled
            )
            with gr.Group(visible=self.current_config.options.assignment.enabled) as work_group:
                with gr.Row():
                    with gr.Column():
                        mini_live_reassign = gr.Checkbox(
                            label="启用重新分配 MiniLive",
                            value=self.current_config.options.assignment.mini_live_reassign_enabled
                        )
                        mini_live_duration = gr.Dropdown(
                            choices=[4, 6, 12],
                            value=self.current_config.options.assignment.mini_live_duration,
                            label="MiniLive 工作时长",
                            interactive=True
                        )
                    with gr.Column():
                        online_live_reassign = gr.Checkbox(
                            label="启用重新分配 OnlineLive",
                            value=self.current_config.options.assignment.online_live_reassign_enabled
                        )
                        online_live_duration = gr.Dropdown(
                            choices=[4, 6, 12],
                            value=self.current_config.options.assignment.online_live_duration,
                            label="OnlineLive 工作时长",
                            interactive=True
                        )
            
            assignment_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[assignment_enabled],
                outputs=[work_group]
            )
        return assignment_enabled, mini_live_reassign, mini_live_duration, online_live_reassign, online_live_duration

    def _create_produce_settings(self) -> Tuple[gr.Checkbox, gr.Dropdown, gr.Number, gr.Checkbox, gr.Checkbox, gr.Checkbox, gr.Checkbox, gr.Checkbox]:
        with gr.Column():
            gr.Markdown("### 培育设置")
            produce_enabled = gr.Checkbox(
                label="启用培育",
                value=self.current_config.options.produce.enabled
            )
            with gr.Group(visible=self.current_config.options.produce.enabled) as produce_group:
                produce_mode = gr.Dropdown(
                    choices=["regular"],
                    value=self.current_config.options.produce.mode,
                    label="培育模式"
                )
                produce_count = gr.Number(
                    minimum=1,
                    value=self.current_config.options.produce.produce_count,
                    label="培育次数",
                    interactive=True
                )
                auto_set_memory = gr.Checkbox(
                    label="自动编成回忆",
                    value=self.current_config.options.produce.auto_set_memory
                )
                auto_set_support = gr.Checkbox(
                    label="自动编成支援卡",
                    value=self.current_config.options.produce.auto_set_support_card
                )
                use_pt_boost = gr.Checkbox(
                    label="使用支援强化 Pt 提升",
                    value=self.current_config.options.produce.use_pt_boost
                )
                use_note_boost = gr.Checkbox(
                    label="使用笔记数提升",
                    value=self.current_config.options.produce.use_note_boost
                )
                follow_producer = gr.Checkbox(
                    label="关注租借了支援卡的制作人",
                    value=self.current_config.options.produce.follow_producer
                )
            
            produce_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[produce_enabled],
                outputs=[produce_group]
            )
        return produce_enabled, produce_mode, produce_count, auto_set_memory, auto_set_support, use_pt_boost, use_note_boost, follow_producer

    def _create_settings_tab(self) -> None:
        with gr.Tab("设置"):
            gr.Markdown("## 设置")
            
            # 模拟器设置
            with gr.Column():
                gr.Markdown("### 模拟器设置")
                with gr.Row():
                    adb_ip = gr.Textbox(
                        value=self.current_config.backend.adb_ip,
                        label="ADB IP 地址",
                        interactive=True
                    )
                    adb_port = gr.Number(
                        value=self.current_config.backend.adb_port,
                        label="ADB 端口",
                        minimum=1,
                        maximum=65535,
                        step=1,
                        interactive=True
                    )
            
            # 商店购买设置
            purchase_settings = self._create_purchase_settings()
            
            # 活动费设置
            with gr.Column():
                gr.Markdown("### 活动费设置")
                activity_funds = gr.Checkbox(
                    label="启用收取活动费",
                    value=self.current_config.options.activity_funds.enabled
                )
            
            # 礼物设置
            with gr.Column():
                gr.Markdown("### 礼物设置")
                presents = gr.Checkbox(
                    label="启用收取礼物",
                    value=self.current_config.options.presents.enabled
                )
            
            # 工作设置
            work_settings = self._create_work_settings()
            
            # 竞赛设置
            with gr.Column():
                gr.Markdown("### 竞赛设置")
                contest = gr.Checkbox(
                    label="启用竞赛",
                    value=self.current_config.options.contest.enabled
                )
            
            # 培育设置
            produce_settings = self._create_produce_settings()
            
            # 任务奖励设置
            with gr.Column():
                gr.Markdown("### 任务奖励设置")
                mission_reward = gr.Checkbox(
                    label="启用领取任务奖励",
                    value=self.current_config.options.mission_reward.enabled
                )
            
            save_btn = gr.Button("保存设置")
            result = gr.Markdown()
            
            # 收集所有设置组件
            all_settings = [
                adb_ip, adb_port,
                *purchase_settings,
                activity_funds,
                presents,
                *work_settings,
                contest,
                *produce_settings,
                mission_reward
            ]
            
            save_btn.click(
                fn=self.save_settings,
                inputs=all_settings,
                outputs=result
            )

    def _create_log_tab(self) -> None:
        with gr.Tab("日志"):
            gr.Markdown("## 日志")
            
            # 创建日志文本区域
            log_output = gr.TextArea(
                label="日志输出",
                value="",
                lines=20,
                max_lines=20,
                interactive=False,
                autoscroll=True
            )
            
            with gr.Row():
                export_btn = gr.Button("导出日志")
                clear_btn = gr.Button("清除日志")
            
            def clear_logs() -> str:
                with self.log_lock:
                    while not self.log_queue.empty():
                        self.log_queue.get_nowait()
                return ""
            
            clear_btn.click(
                fn=clear_logs,
                outputs=[log_output]
            )
            
            # 添加自动更新定时器
            gr.Timer(1.0).tick(
                fn=self.get_logs,
                inputs=[log_output],
                outputs=[log_output]
            )

    def _load_config(self) -> None:
        # 加载配置文件
        config_path = "config.json"
        self.config = load_config(config_path, type=BaseConfig, use_default_if_not_found=True)
        if not self.config.user_configs:
            # 如果没有用户配置，创建一个默认配置
            default_config = UserConfig[BaseConfig](
                name="默认配置",
                category="default",
                description="默认配置",
                backend=BackendConfig(),
                options=BaseConfig()
            )
            self.config.user_configs.append(default_config)
        self.current_config = self.config.user_configs[0]

    def create_ui(self) -> gr.Blocks:
        # 每次创建 UI 时重新加载配置
        self._load_config()
        
        with gr.Blocks(title="KotoneBot Assistant", css="#container { max-width: 800px; margin: auto; padding: 20px; }") as app:
            with gr.Column(elem_id="container"):
                gr.Markdown("# KotoneBot Assistant")
                
                with gr.Tabs():
                    self._create_status_tab()
                    self._create_settings_tab()
                    self._create_log_tab()
            
        return app

def main() -> None:
    ui = KotoneBotUI()
    app = ui.create_ui()
    app.launch()

if __name__ == "__main__":
    main()