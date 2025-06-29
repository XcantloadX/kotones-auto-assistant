import os
import traceback
import zipfile
import logging
from functools import partial
from itertools import chain
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Literal, Generator, Callable, Any, get_args, cast

import cv2
import gradio as gr

from kotonebot.kaa.main import Kaa
from kotonebot.kaa.db import IdolCard
from kotonebot.config.manager import load_config, save_config
from kotonebot.config.base_config import UserConfig, BackendConfig
from kotonebot.backend.context import task_registry, ContextStackVars
from kotonebot.backend.context.context import vars
from kotonebot.client.host import Mumu12Host, LeidianHost
from kotonebot.kaa.common import (
    BaseConfig, APShopItems, CapsuleToysConfig, ClubRewardConfig, PurchaseConfig, ActivityFundsConfig,
    PresentsConfig, AssignmentConfig, ContestConfig, ProduceConfig,
    MissionRewardConfig, DailyMoneyShopItems, ProduceAction,
    RecommendCardDetectionMode, TraceConfig, StartGameConfig, EndGameConfig, UpgradeSupportCardConfig,
)

logger = logging.getLogger(__name__)
GradioInput = gr.Textbox | gr.Number | gr.Checkbox | gr.Dropdown | gr.Radio | gr.Slider | gr.Tabs | gr.Tab
ConfigKey = Literal[
    # backend
    'adb_ip', 'adb_port',
    'screenshot_method', 'keep_screenshots',
    'check_emulator', 'emulator_path',
    'adb_emulator_name', 'emulator_args',
    '_mumu_index', '_leidian_index',

    # purchase
    'purchase_enabled',
    'money_enabled', 'ap_enabled',
    'ap_items', 'money_items',
    
    # assignment
    'assignment_enabled',
    'mini_live_reassign', 'mini_live_duration',
    'online_live_reassign', 'online_live_duration',
    'contest_enabled',
    'select_which_contestant',
    
    # produce
    'produce_enabled', 'produce_mode',
    'produce_count', 'produce_idols',
    'memory_sets', 'auto_set_memory',
    'auto_set_support', 'use_pt_boost',
    'use_note_boost', 'follow_producer',
    'self_study_lesson', 'prefer_lesson_ap',
    'actions_order', 'recommend_card_detection_mode',
    'use_ap_drink', 'skip_commu',
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
    'disable_gakumas_localify', 'dmm_game_path',

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
    
    '_selected_backend_index'
    
]
CONFIG_KEY_VALUE: tuple[str] = get_args(ConfigKey)
ConfigSetFunction = Callable[[BaseConfig, Dict[ConfigKey, Any]], None]
ConfigBuilderReturnValue = Tuple[ConfigSetFunction, Dict[ConfigKey, GradioInput]]

def _save_bug_report(
    version: str,
    path: str | None = None
) -> Generator[str, None, str]:
    """
    保存报告

    :param path: 保存的路径。若为 `None`，则保存到 `./reports/bug-{YY-MM-DD HH-MM-SS}.zip`。
    :return: 保存的路径
    """
    from kotonebot import device
    from kotonebot.backend.context import ContextStackVars

    # 确保目录存在
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)

    error = ""
    if path is None:
        path = f'./reports/bug-{datetime.now().strftime("%y-%m-%d %H-%M-%S")}.zip'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        # 打包截图
        yield "### 打包上次截图..."
        try:
            stack = ContextStackVars.current()
            screenshot = None
            if stack is not None:
                screenshot = stack._screenshot
                if screenshot is not None:
                    img = cv2.imencode('.png', screenshot)[1].tobytes()
                    zipf.writestr('last_screenshot.png', img)
            if screenshot is None:
                error += "无上次截图数据\n"
        except Exception as e:
            error += f"保存上次截图失败：{str(e)}\n"

        # 打包当前截图
        yield "### 打包当前截图..."
        try:
            screenshot = device.screenshot()
            img = cv2.imencode('.png', screenshot)[1].tobytes()
            zipf.writestr('current_screenshot.png', img)
        except Exception as e:
            error += f"保存当前截图失败：{str(e)}\n"

        # 打包配置文件
        yield "### 打包配置文件..."
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                zipf.writestr('config.json', f.read())
        except Exception as e:
            error += f"保存配置文件失败：{str(e)}\n"

        # 打包 logs 文件夹
        if os.path.exists('logs'):
            for root, dirs, files in os.walk('logs'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('logs', os.path.relpath(file_path, 'logs'))
                    zipf.write(file_path, arcname)
                    yield f"### 打包 log 文件：{arcname}"

        # 写出版本号
        zipf.writestr('version.txt', version)

    # 上传报告
    from kotonebot.ui.file_host.sensio import upload
    yield "### 上传报告..."
    url = ''
    try:
        url = upload(path)
    except Exception as e:
        yield f"### 上传报告失败：{str(e)}\n\n"
        return ''

    final_msg = f"### 报告导出成功：{url}\n\n"
    expire_time = datetime.now() + timedelta(days=7)
    if error:
        final_msg += "### 但发生了以下错误\n\n"
        final_msg += '\n* '.join(error.strip().split('\n'))
    final_msg += '\n'
    final_msg += f"### 此链接将于 {expire_time.strftime('%Y-%m-%d %H:%M:%S')}（7 天后）过期\n\n"
    final_msg += '### 复制以上文本并反馈给开发者'
    yield final_msg
    return path

class KotoneBotUI:
    def __init__(self, kaa: Kaa) -> None:
        self.is_running: bool = False
        self.single_task_running: bool = False
        self.is_stopping: bool = False  # 新增：标记是否正在停止过程中
        self.is_single_task_stopping: bool = False  # 新增：标记单个任务是否正在停止
        self._kaa = kaa
        self._load_config()
        self._setup_kaa()

    def _setup_kaa(self) -> None:
        from kotonebot.backend.debug.vars import debug, clear_saved

        self._kaa.initialize()
        if self.current_config.keep_screenshots:
            debug.auto_save_to_folder = 'dumps'
            debug.enabled = True
            clear_saved()
        else:
            debug.auto_save_to_folder = None
            debug.enabled = False

    def export_dumps(self) -> str:
        """导出 dumps 文件夹为 zip 文件"""
        if not os.path.exists('dumps'):
            return "dumps 文件夹不存在"

        timestamp = datetime.now().strftime('%y-%m-%d-%H-%M-%S')
        zip_filename = f'dumps-{timestamp}.zip'

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, dirs, files in os.walk('dumps'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, 'dumps')
                    zipf.write(file_path, arcname)

        return f"已导出到 {zip_filename}"

    def export_logs(self) -> str:
        """导出 logs 文件夹为 zip 文件"""
        if not os.path.exists('logs'):
            return "logs 文件夹不存在"

        timestamp = datetime.now().strftime('%y-%m-%d-%H-%M-%S')
        zip_filename = f'logs-{timestamp}.zip'

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, dirs, files in os.walk('logs'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, 'logs')
                    zipf.write(file_path, arcname)

        return f"已导出到 {zip_filename}"

    def get_button_status(self) -> Tuple[str, bool]:
        """获取按钮状态和交互性"""
        if not hasattr(self, 'run_status'):
            return "启动", True

        if not self.run_status.running:
            self.is_running = False
            self.is_stopping = False  # 重置停止状态
            return "启动", True

        if self.is_stopping:
            return "停止中...", False  # 停止中时禁用按钮

        return "停止", True

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

        # 如果正在停止过程中，忽略重复点击
        if self.is_stopping:
            return "停止中...", self.update_task_status()

        return self.stop_run()

    def start_run(self) -> Tuple[str, List[List[str]]]:
        self.is_running = True
        self.run_status = self._kaa.start_all()
        return "停止", self.update_task_status()

    def stop_run(self) -> Tuple[str, List[List[str]]]:
        self.is_stopping = True  # 设置停止状态

        # 如果当前处于暂停状态，先恢复再停止
        if vars.flow.is_paused:
            gr.Info("检测到任务暂停，正在恢复后停止...")
            vars.flow.request_resume()

        self.is_running = False
        if self._kaa:
            self.run_status.interrupt()
            gr.Info("正在停止任务...")

        return "停止中...", self.update_task_status()

    def start_single_task(self, task_name: str) -> Tuple[str, str]:
        if not task_name:
            gr.Warning("请先选择一个任务")
            return "执行任务", ""
        task = None
        for name, t in task_registry.items():
            if name == task_name:
                task = t
                break
        if task is None:
            gr.Warning(f"任务 {task_name} 未找到")
            return "执行任务", ""

        gr.Info(f"任务 {task_name} 开始执行")
        self.single_task_running = True
        self.run_status = self._kaa.start([task])
        return "停止任务", f"正在执行任务: {task_name}"

    def stop_single_task(self) -> Tuple[str, str]:
        self.is_single_task_stopping = True  # 设置单个任务停止状态

        # 如果当前处于暂停状态，先恢复再停止
        if vars.flow.is_paused:
            gr.Info("检测到任务暂停，正在恢复后停止...")
            vars.flow.request_resume()

        self.single_task_running = False
        if hasattr(self, 'run_status') and self._kaa:
            self.run_status.interrupt()
            gr.Info("正在停止任务...")
        return "停止中...", "正在停止任务..."

    def toggle_pause(self) -> str:
        """切换暂停/恢复状态"""
        if vars.flow.is_paused:
            vars.flow.request_resume()
            gr.Info("任务已恢复")
            return "暂停"
        else:
            vars.flow.request_pause()
            gr.Info("任务已暂停")
            return "恢复"

    def get_pause_button_status(self) -> str:
        """获取暂停按钮的状态"""
        if vars.flow.is_paused:
            return "恢复"
        else:
            return "暂停"

    def get_pause_button_with_interactive(self) -> gr.Button:
        """获取暂停按钮的状态和交互性"""
        try:
            text = "恢复" if vars.flow.is_paused else "暂停"
        except ValueError:
            # ValueError: Forwarded object vars called before initialization.
            # TODO: vars.flow.is_paused 应该要可以在脚本正式启动前就能访问
            text = '未启动'
        # 如果正在停止过程中，禁用暂停按钮
        interactive = not (self.is_stopping or self.is_single_task_stopping)
        return gr.Button(value=text, interactive=interactive)
        
    def save_settings2(self, return_values: list[ConfigBuilderReturnValue], *args) -> str:
        options = BaseConfig()
        # return_values: (set_func, { 'key': component })
        keys = list(chain.from_iterable([list(data.keys()) for _, data in return_values]))
        # 根据 keys 与 *args 构建 data 字典
        data = dict[ConfigKey, Any]()
        assert len(keys) == len(args), "keys 与 args 长度不一致"
        for key, value in zip(keys, args):
            assert key in CONFIG_KEY_VALUE, f"未知的配置项：{key}"
            key = cast(ConfigKey, key)
            data[key] = value
        # 设置结果
        for (set_func, _) in return_values:
            set_func(options, data)
        self.current_config.options = options
        try:
            save_config(self.config, "config.json")
            gr.Success("设置已保存，请重启程序！")
            return ""
        except Exception as e:
            gr.Warning(f"保存设置失败：{str(e)}")
            return ""

    def _create_status_tab(self) -> None:
        with gr.Tab("状态"):
            gr.Markdown("## 状态")

            with gr.Row():
                run_btn = gr.Button("启动", scale=2)
                pause_btn = gr.Button("暂停", scale=1)
            if self._kaa.upgrade_msg:
                gr.Markdown('### 配置升级报告')
                gr.Markdown(self._kaa.upgrade_msg)
            gr.Markdown('脚本报错或者卡住？点击"日志"选项卡中的"一键导出报告"可以快速反馈！')

            task_status = gr.Dataframe(
                headers=["任务", "状态"],
                value=self.update_task_status(),
                label="任务状态"
            )

            def on_run_click(evt: gr.EventData) -> Tuple[gr.Button, List[List[str]]]:
                result = self.toggle_run()
                # 如果正在停止，禁用按钮
                interactive = not self.is_stopping
                button = gr.Button(value=result[0], interactive=interactive)
                return button, result[1]

            def on_pause_click(evt: gr.EventData) -> str:
                return self.toggle_pause()

            run_btn.click(
                fn=on_run_click,
                outputs=[run_btn, task_status]
            )

            pause_btn.click(
                fn=on_pause_click,
                outputs=[pause_btn]
            )

            # 添加定时器，分别更新按钮状态和任务状态
            def update_run_button_status():
                text, interactive = self.get_button_status()
                return gr.Button(value=text, interactive=interactive)

            gr.Timer(1.0).tick(
                fn=update_run_button_status,
                outputs=[run_btn]
            )
            gr.Timer(1.0).tick(
                fn=self.get_pause_button_with_interactive,
                outputs=[pause_btn]
            )
            gr.Timer(1.0).tick(
                fn=self.update_task_status,
                outputs=[task_status]
            )

    def _create_task_tab(self) -> None:
        with gr.Tab("任务"):
            gr.Markdown("## 执行任务")

            # 创建任务选择下拉框
            task_choices = [task.name for task in task_registry.values()]
            task_dropdown = gr.Dropdown(
                choices=task_choices,
                label="选择要执行的任务",
                info="选择一个要单独执行的任务",
                type="value",
                value=None
            )

            # 创建执行按钮和暂停按钮
            with gr.Row():
                execute_btn = gr.Button("执行任务", scale=2)
                pause_btn = gr.Button("暂停", scale=1)
            task_result = gr.Markdown("")

            def toggle_single_task(task_name: str) -> Tuple[gr.Button, str]:
                if self.single_task_running:
                    # 如果正在停止过程中，忽略重复点击
                    if self.is_single_task_stopping:
                        return gr.Button(value="停止中...", interactive=False), "正在停止任务..."

                    result = self.stop_single_task()
                    return gr.Button(value=result[0], interactive=False), result[1]
                else:
                    result = self.start_single_task(task_name)
                    return gr.Button(value=result[0], interactive=True), result[1]

            def get_task_button_status() -> gr.Button:
                if not hasattr(self, 'run_status') or not self.run_status.running:
                    self.single_task_running = False
                    self.is_single_task_stopping = False  # 重置停止状态
                    return gr.Button(value="执行任务", interactive=True)

                if self.is_single_task_stopping:
                    return gr.Button(value="停止中...", interactive=False)  # 停止中时禁用按钮

                return gr.Button(value="停止任务", interactive=True)

            def get_single_task_status() -> str:
                if not hasattr(self, 'run_status'):
                    return ""

                if not self.run_status.running and self.single_task_running:
                    # 任务已结束但状态未更新
                    self.single_task_running = False

                    # 检查任务状态
                    for task_status in self.run_status.tasks:
                        status = task_status.status
                        task_name = task_status.task.name

                        if status == 'finished':
                            return f"任务 {task_name} 已完成"
                        elif status == 'error':
                            return f"任务 {task_name} 出错"
                        elif status == 'cancelled':
                            return f"任务 {task_name} 已取消"

                    return "任务已结束"

                if self.single_task_running:
                    for task_status in self.run_status.tasks:
                        if task_status.status == 'running':
                            return f"正在执行任务: {task_status.task.name}"

                    return "正在准备执行任务..."

                return ""

            def on_pause_click(evt: gr.EventData) -> str:
                return self.toggle_pause()

            execute_btn.click(
                fn=toggle_single_task,
                inputs=[task_dropdown],
                outputs=[execute_btn, task_result]
            )

            pause_btn.click(
                fn=on_pause_click,
                outputs=[pause_btn]
            )

            # 添加定时器更新按钮状态和任务状态
            gr.Timer(1.0).tick(
                fn=get_task_button_status,
                outputs=[execute_btn]
            )
            gr.Timer(1.0).tick(
                fn=self.get_pause_button_with_interactive,
                outputs=[pause_btn]
            )
            gr.Timer(1.0).tick(
                fn=get_single_task_status,
                outputs=[task_result]
            )

    def _create_emulator_settings(self) -> ConfigBuilderReturnValue:
        gr.Markdown("### 模拟器设置")
        has_mumu12 = Mumu12Host.installed()
        has_leidian = LeidianHost.installed()
        current_tab = 0

        def _update_emulator_tab_options(impl_value: str, selected_index: int):
            nonlocal current_tab
            current_tab = selected_index

            # if selected_index == 3:  # DMM
            #     choices = ['windows', 'remote_windows']
            # else:  # Mumu, Leidian, Custom
            #     choices = ['adb', 'adb_raw', 'uiautomator2']
            choices = ['adb', 'adb_raw', 'uiautomator2', 'windows', 'remote_windows']
            if impl_value not in choices:
                new_value = choices[0]
            else:
                new_value = impl_value

            return gr.Dropdown(choices=choices, value=new_value)

        with gr.Tabs(selected=self.current_config.backend.type):
            with gr.Tab("MuMu 12", interactive=has_mumu12, id="mumu12") as tab_mumu12:
                gr.Markdown("已选中 MuMu 12 模拟器")
                if has_mumu12:
                    try:
                        instances = Mumu12Host.list()
                        is_mumu12 = self.current_config.backend.type == 'mumu12'
                        mumu_instance = gr.Dropdown(
                            label="选择多开实例",
                            value=self.current_config.backend.instance_id if is_mumu12 else None,
                            choices=[(i.name, i.id) for i in instances],
                            interactive=True
                        )
                    except:  # noqa: E722
                        logger.exception('Failed to list installed MuMu12')
                        gr.Markdown('获取 MuMu12 模拟器列表失败，请升级模拟器到最新版本。若问题依旧，前往 QQ 群、QQ 频道或 Github 反馈 bug。')
                        mumu_instance = gr.Dropdown(visible=False)
                else:
                    # 为了让 return 收集组件时不报错
                    mumu_instance = gr.Dropdown(visible=False)

            with gr.Tab("雷电", interactive=has_leidian, id="leidian") as tab_leidian:
                gr.Markdown("已选中雷电模拟器")
                if has_leidian:
                    try:
                        instances = LeidianHost.list()
                        is_leidian = self.current_config.backend.type == 'leidian'
                        leidian_instance = gr.Dropdown(
                            label="选择多开实例",
                            value=self.current_config.backend.instance_id if is_leidian else None,
                            choices=[(i.name, i.id) for i in instances],
                            interactive=True
                        )
                    except:  # noqa: E722
                        logger.exception('Failed to list installed Leidian')
                        gr.Markdown('获取雷电模拟器列表失败，请前往 QQ 群、QQ 频道或 Github 反馈 bug。')
                        leidian_instance = gr.Dropdown(visible=False)
                else:
                    leidian_instance = gr.Dropdown(visible=False)

            with gr.Tab("自定义", id="custom") as tab_custom:
                gr.Markdown("已选中自定义模拟器")
                adb_ip = gr.Textbox(
                    value=self.current_config.backend.adb_ip,
                    label="ADB IP 地址",
                    info=BackendConfig.model_fields['adb_ip'].description,
                    interactive=True
                )
                adb_port = gr.Number(
                    value=self.current_config.backend.adb_port,
                    label="ADB 端口",
                    info=BackendConfig.model_fields['adb_port'].description,
                    minimum=1,
                    maximum=65535,
                    step=1,
                    interactive=True
                )
                check_emulator = gr.Checkbox(
                    label="检查并启动模拟器",
                    value=self.current_config.backend.check_emulator,
                    info=BackendConfig.model_fields['check_emulator'].description,
                    interactive=True
                )
                with gr.Group(visible=self.current_config.backend.check_emulator) as check_emulator_group:
                    emulator_path = gr.Textbox(
                        value=self.current_config.backend.emulator_path,
                        label="模拟器 exe 文件路径",
                        info=BackendConfig.model_fields['emulator_path'].description,
                        interactive=True
                    )
                    adb_emulator_name = gr.Textbox(
                        value=self.current_config.backend.adb_emulator_name,
                        label="ADB 模拟器名称",
                        info=BackendConfig.model_fields['adb_emulator_name'].description,
                        interactive=True
                    )
                    emulator_args = gr.Textbox(
                        value=self.current_config.backend.emulator_args,
                        label="模拟器启动参数",
                        info=BackendConfig.model_fields['emulator_args'].description,
                        interactive=True
                    )
                check_emulator.change(
                    fn=lambda x: gr.Group(visible=x),
                    inputs=[check_emulator],
                    outputs=[check_emulator_group]
                )

            with gr.Tab("DMM", id="dmm") as tab_dmm:
                gr.Markdown("已选中 DMM")

        # type_in_config = self.current_config.backend.type
        # if type_in_config in ['dmm']:
        #     choices = ['windows', 'remote_windows']
        # elif type_in_config in ['mumu12', 'leidian', 'custom']:
        #     choices = ['adb', 'adb_raw', 'uiautomator2']
        # else:
        #     raise ValueError(f'Unsupported backend type: {type_in_config}')
        choices = ['adb', 'adb_raw', 'uiautomator2', 'windows', 'remote_windows']
        screenshot_impl = gr.Dropdown(
            choices=choices,
            value=self.current_config.backend.screenshot_impl,
            label="截图方法",
            info=BackendConfig.model_fields['screenshot_impl'].description,
            interactive=True
        )

        keep_screenshots = gr.Checkbox(
            label="保留截图数据",
            value=self.current_config.keep_screenshots,
            info=UserConfig.model_fields['keep_screenshots'].description,
            interactive=True
        )

        tab_mumu12.select(fn=partial(_update_emulator_tab_options, selected_index=0), inputs=[screenshot_impl], outputs=[screenshot_impl])
        tab_leidian.select(fn=partial(_update_emulator_tab_options, selected_index=1), inputs=[screenshot_impl], outputs=[screenshot_impl])
        tab_custom.select(fn=partial(_update_emulator_tab_options, selected_index=2), inputs=[screenshot_impl], outputs=[screenshot_impl])
        tab_dmm.select(fn=partial(_update_emulator_tab_options, selected_index=3), inputs=[screenshot_impl], outputs=[screenshot_impl])

        # 初值
        if self.current_config.backend.type == 'mumu12':
            _update_emulator_tab_options(
                impl_value=self.current_config.backend.screenshot_impl,
                selected_index=0
            )
        elif self.current_config.backend.type == 'leidian':
            _update_emulator_tab_options(
                impl_value=self.current_config.backend.screenshot_impl,
                selected_index=1
            )
        elif self.current_config.backend.type == 'custom':
            _update_emulator_tab_options(
                impl_value=self.current_config.backend.screenshot_impl,
                selected_index=2
            )
        elif self.current_config.backend.type == 'dmm':
            _update_emulator_tab_options(
                impl_value=self.current_config.backend.screenshot_impl,
                selected_index=3
            )
        else:
            gr.Warning(f"未知的模拟器类型：{self.current_config.backend.type}")

        def set_config(_: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            # current_tab is updated by _update_emulator_tab_options
            if current_tab == 0:  # Mumu
                self.current_config.backend.type = 'mumu12'
                self.current_config.backend.instance_id = data['_mumu_index']
            elif current_tab == 1:  # Leidian
                self.current_config.backend.type = 'leidian'
                self.current_config.backend.instance_id = data['_leidian_index']
            elif current_tab == 2:  # Custom
                self.current_config.backend.type = 'custom'
                self.current_config.backend.instance_id = None
                self.current_config.backend.adb_ip = data['adb_ip']
                self.current_config.backend.adb_port = data['adb_port']
                self.current_config.backend.adb_emulator_name = data['adb_emulator_name']
                self.current_config.backend.check_emulator = data['check_emulator']
                self.current_config.backend.emulator_path = data['emulator_path']
                self.current_config.backend.emulator_args = data['emulator_args']
            elif current_tab == 3:  # DMM
                self.current_config.backend.type = 'dmm'
                self.current_config.backend.instance_id = None  # DMM doesn't use instance_id here

            # Common settings for all backend types
            self.current_config.backend.screenshot_impl = data['screenshot_method']
            self.current_config.keep_screenshots = data['keep_screenshots']  # This is a UserConfig field

        return set_config, {
            'adb_ip': adb_ip,
            'adb_port': adb_port,
            'screenshot_method': screenshot_impl,  # screenshot_impl is the component
            'keep_screenshots': keep_screenshots,
            'check_emulator': check_emulator,
            'emulator_path': emulator_path,
            'adb_emulator_name': adb_emulator_name,
            'emulator_args': emulator_args,
            '_mumu_index': mumu_instance,
            '_leidian_index': leidian_instance
        }

    def _create_purchase_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 商店购买设置")
            purchase_enabled = gr.Checkbox(
                label="启用商店购买",
                value=self.current_config.options.purchase.enabled,
                info=PurchaseConfig.model_fields['enabled'].description
            )
            with gr.Group(visible=self.current_config.options.purchase.enabled) as purchase_group:
                money_enabled = gr.Checkbox(
                    label="启用金币购买",
                    value=self.current_config.options.purchase.money_enabled,
                    info=PurchaseConfig.model_fields['money_enabled'].description
                )

                # 添加金币商店商品选择
                money_items = gr.Dropdown(
                    multiselect=True,
                    choices=list(DailyMoneyShopItems.all()),
                    value=self.current_config.options.purchase.money_items,
                    label="金币商店购买物品",
                    info=PurchaseConfig.model_fields['money_items'].description
                )

                ap_enabled = gr.Checkbox(
                    label="启用AP购买",
                    value=self.current_config.options.purchase.ap_enabled,
                    info=PurchaseConfig.model_fields['ap_enabled'].description
                )

                # 转换枚举值为显示文本
                selected_items: List[str] = []
                ap_items_map = {
                    APShopItems.PRODUCE_PT_UP: "支援强化点数提升",
                    APShopItems.PRODUCE_NOTE_UP: "笔记数提升",
                    APShopItems.RECHALLENGE: "重新挑战券",
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
                    label="AP商店购买物品",
                    info=PurchaseConfig.model_fields['ap_items'].description
                )

            purchase_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[purchase_enabled],
                outputs=[purchase_group]
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.purchase.enabled = data['purchase_enabled']
            config.purchase.money_enabled = data['money_enabled']
            config.purchase.money_items = [DailyMoneyShopItems(x) for x in data['money_items']]
            config.purchase.ap_enabled = data['ap_enabled']
            ap_items_enum: List[Literal[0, 1, 2, 3]] = []
            ap_items_map: Dict[str, APShopItems] = {
                "支援强化点数提升": APShopItems.PRODUCE_PT_UP,
                "笔记数提升": APShopItems.PRODUCE_NOTE_UP,
                "重新挑战券": APShopItems.RECHALLENGE,
                "回忆再生成券": APShopItems.REGENERATE_MEMORY
            }
            for item in data['ap_items']:
                if item in ap_items_map:
                    ap_items_enum.append(ap_items_map[item].value)  # type: ignore
            config.purchase.ap_items = ap_items_enum
        
        return set_config, {
            'purchase_enabled': purchase_enabled,
            'money_enabled': money_enabled,
            'ap_enabled': ap_enabled,
            'ap_items': ap_items,
            'money_items': money_items
        }

    def _create_work_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 工作设置")
            assignment_enabled = gr.Checkbox(
                label="启用工作",
                value=self.current_config.options.assignment.enabled,
                info=AssignmentConfig.model_fields['enabled'].description
            )
            with gr.Group(visible=self.current_config.options.assignment.enabled) as work_group:
                with gr.Row():
                    with gr.Column():
                        mini_live_reassign = gr.Checkbox(
                            label="启用重新分配 MiniLive",
                            value=self.current_config.options.assignment.mini_live_reassign_enabled,
                            info=AssignmentConfig.model_fields['mini_live_reassign_enabled'].description
                        )
                        mini_live_duration = gr.Dropdown(
                            choices=[4, 6, 12],
                            value=self.current_config.options.assignment.mini_live_duration,
                            label="MiniLive 工作时长",
                            interactive=True,
                            info=AssignmentConfig.model_fields['mini_live_duration'].description
                        )
                    with gr.Column():
                        online_live_reassign = gr.Checkbox(
                            label="启用重新分配 OnlineLive",
                            value=self.current_config.options.assignment.online_live_reassign_enabled,
                            info=AssignmentConfig.model_fields['online_live_reassign_enabled'].description
                        )
                        online_live_duration = gr.Dropdown(
                            choices=[4, 6, 12],
                            value=self.current_config.options.assignment.online_live_duration,
                            label="OnlineLive 工作时长",
                            interactive=True,
                            info=AssignmentConfig.model_fields['online_live_duration'].description
                        )

            assignment_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[assignment_enabled],
                outputs=[work_group]
            )
        # return assignment_enabled, mini_live_reassign, mini_live_duration, online_live_reassign, online_live_duration
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.assignment.enabled = data['assignment_enabled']
            config.assignment.mini_live_reassign_enabled = data['mini_live_reassign']
            config.assignment.mini_live_duration = data['mini_live_duration']
            config.assignment.online_live_reassign_enabled = data['online_live_reassign']
            config.assignment.online_live_duration = data['online_live_duration']
        
        return set_config, {
            'assignment_enabled': assignment_enabled,
            'mini_live_reassign': mini_live_reassign,
            'mini_live_duration': mini_live_duration,
            'online_live_reassign': online_live_reassign,
            'online_live_duration': online_live_duration
        }


    def _create_contest_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 竞赛设置")
            contest_enabled = gr.Checkbox(
                label="启用竞赛",
                value=self.current_config.options.contest.enabled,
                info=ContestConfig.model_fields['enabled'].description
            )
            with gr.Group(visible=self.current_config.options.contest.enabled) as contest_group:
                select_which_contestant = gr.Dropdown(
                    choices=[1, 2, 3],
                    value=self.current_config.options.contest.select_which_contestant,
                    label="选择第几位竞赛目标",
                    interactive=True,
                    info=ContestConfig.model_fields['select_which_contestant'].description
                )
            contest_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[contest_enabled],
                outputs=[contest_group]
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.contest.enabled = data['contest_enabled']
            config.contest.select_which_contestant = data['select_which_contestant']
        
        return set_config, {
            'contest_enabled': contest_enabled,
            'select_which_contestant': select_which_contestant
        }

    def _create_produce_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 培育设置")
            produce_enabled = gr.Checkbox(
                label="启用培育",
                value=self.current_config.options.produce.enabled,
                info=ProduceConfig.model_fields['enabled'].description
            )
            with gr.Group(visible=self.current_config.options.produce.enabled) as produce_group:
                produce_mode = gr.Dropdown(
                    choices=["regular", "pro", "master"],
                    value=self.current_config.options.produce.mode,
                    label="培育模式",
                    info=ProduceConfig.model_fields['mode'].description
                )
                produce_count = gr.Number(
                    minimum=1,
                    value=self.current_config.options.produce.produce_count,
                    label="培育次数",
                    interactive=True,
                    info=ProduceConfig.model_fields['produce_count'].description
                )
                # 添加偶像选择
                idol_choices = []
                for idol in IdolCard.all():
                    if idol.is_another:
                        idol_choices.append((f'{idol.name}　「{idol.another_name}」', idol.skin_id))
                    else:
                        idol_choices.append((f'{idol.name}', idol.skin_id))
                selected_idols = self.current_config.options.produce.idols
                produce_idols = gr.Dropdown(
                    choices=idol_choices,
                    value=selected_idols,
                    label="选择要培育的偶像",
                    multiselect=True,
                    interactive=True,
                    info=ProduceConfig.model_fields['idols'].description
                )
                has_kotone = any("藤田ことね" in idol for idol in selected_idols)
                is_strict_mode = self.current_config.options.produce.recommend_card_detection_mode == RecommendCardDetectionMode.STRICT
                kotone_warning = gr.Markdown(
                    visible=has_kotone and not is_strict_mode,
                    value="使用「藤田ことね」进行培育时，确保将「推荐卡检测模式」设置为「严格模式」"
                )
                auto_set_memory = gr.Checkbox(
                    label="自动编成回忆",
                    value=self.current_config.options.produce.auto_set_memory,
                    info=ProduceConfig.model_fields['auto_set_memory'].description
                )
                with gr.Group(visible=not self.current_config.options.produce.auto_set_memory) as memory_sets_group:
                    memory_sets = gr.Dropdown(
                        choices=[str(i) for i in range(1, 11)],  # 假设最多10个编成位
                        value=[str(i) for i in self.current_config.options.produce.memory_sets],
                        label="回忆编成编号",
                        multiselect=True,
                        interactive=True,
                        info=ProduceConfig.model_fields['memory_sets'].description
                    )

                # 添加偶像选择变化时的回调
                def update_kotone_warning(selected_idols, recommend_card_detection_mode):
                    has_kotone = any("藤田ことね" in idol for idol in selected_idols)
                    is_strict_mode = recommend_card_detection_mode == RecommendCardDetectionMode.STRICT.value
                    return gr.Markdown(visible=has_kotone and not is_strict_mode)

                auto_set_support = gr.Checkbox(
                    label="自动编成支援卡",
                    value=self.current_config.options.produce.auto_set_support_card,
                    info=ProduceConfig.model_fields['auto_set_support_card'].description
                )
                use_pt_boost = gr.Checkbox(
                    label="使用支援强化 Pt 提升",
                    value=self.current_config.options.produce.use_pt_boost,
                    info=ProduceConfig.model_fields['use_pt_boost'].description
                )
                use_note_boost = gr.Checkbox(
                    label="使用笔记数提升",
                    value=self.current_config.options.produce.use_note_boost,
                    info=ProduceConfig.model_fields['use_note_boost'].description
                )
                follow_producer = gr.Checkbox(
                    label="关注租借了支援卡的制作人",
                    value=self.current_config.options.produce.follow_producer,
                    info=ProduceConfig.model_fields['follow_producer'].description
                )
                self_study_lesson = gr.Dropdown(
                    choices=['dance', 'visual', 'vocal'],
                    value=self.current_config.options.produce.self_study_lesson,
                    label='文化课自习时选项',
                    info='选择自习课类型'
                )
                prefer_lesson_ap = gr.Checkbox(
                    label="SP 课程优先",
                    value=self.current_config.options.produce.prefer_lesson_ap,
                    info=ProduceConfig.model_fields['prefer_lesson_ap'].description
                )
                actions_order = gr.Dropdown(
                    choices=[(action.display_name, action.value) for action in ProduceAction],
                    value=[action.value for action in self.current_config.options.produce.actions_order],
                    label="行动优先级",
                    info="设置每周行动的优先级顺序",
                    multiselect=True
                )
                recommend_card_detection_mode = gr.Dropdown(
                    choices=[
                        (RecommendCardDetectionMode.NORMAL.display_name, RecommendCardDetectionMode.NORMAL.value),
                        (RecommendCardDetectionMode.STRICT.display_name, RecommendCardDetectionMode.STRICT.value)
                    ],
                    value=self.current_config.options.produce.recommend_card_detection_mode.value,
                    label="推荐卡检测模式",
                    info=ProduceConfig.model_fields['recommend_card_detection_mode'].description
                )
                use_ap_drink = gr.Checkbox(
                    label="AP 不足时自动使用 AP 饮料",
                    value=self.current_config.options.produce.use_ap_drink,
                    info=ProduceConfig.model_fields['use_ap_drink'].description
                )
                skip_commu = gr.Checkbox(
                    label="检测并跳过交流",
                    value=self.current_config.options.produce.skip_commu,
                    info=ProduceConfig.model_fields['skip_commu'].description
                )
                recommend_card_detection_mode.change(
                    fn=update_kotone_warning,
                    inputs=[produce_idols, recommend_card_detection_mode],
                    outputs=kotone_warning
                )
                produce_idols.change(
                    fn=update_kotone_warning,
                    inputs=[produce_idols, recommend_card_detection_mode],
                    outputs=kotone_warning
                )

            produce_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[produce_enabled],
                outputs=[produce_group]
            )

            auto_set_memory.change(
                fn=lambda x: gr.Group(visible=not x),
                inputs=[auto_set_memory],
                outputs=[memory_sets_group]
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.produce.enabled = data['produce_enabled']
            config.produce.mode = data['produce_mode']
            config.produce.produce_count = data['produce_count']
            config.produce.idols = data['produce_idols']
            config.produce.memory_sets = [int(i) for i in data['memory_sets']]
            config.produce.auto_set_memory = data['auto_set_memory']
            config.produce.auto_set_support_card = data['auto_set_support']
            config.produce.use_pt_boost = data['use_pt_boost']
            config.produce.use_note_boost = data['use_note_boost']
            config.produce.follow_producer = data['follow_producer']
            config.produce.self_study_lesson = data['self_study_lesson']
            config.produce.prefer_lesson_ap = data['prefer_lesson_ap']
            config.produce.actions_order = [ProduceAction(action) for action in data['actions_order']]
            config.produce.recommend_card_detection_mode = RecommendCardDetectionMode(data['recommend_card_detection_mode'])
            config.produce.use_ap_drink = data['use_ap_drink']
            config.produce.skip_commu = data['skip_commu']
        
        return set_config, {
            'produce_enabled': produce_enabled,
            'produce_mode': produce_mode,
            'produce_count': produce_count,
            'produce_idols': produce_idols,
            'memory_sets': memory_sets,
            'auto_set_memory': auto_set_memory,
            'auto_set_support': auto_set_support,
            'use_pt_boost': use_pt_boost,
            'use_note_boost': use_note_boost,
            'follow_producer': follow_producer,
            'self_study_lesson': self_study_lesson,
            'prefer_lesson_ap': prefer_lesson_ap,
            'actions_order': actions_order,
            'recommend_card_detection_mode': recommend_card_detection_mode,
            'use_ap_drink': use_ap_drink,
            'skip_commu': skip_commu
        }

    def _create_club_reward_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 社团奖励设置")
            club_reward_enabled = gr.Checkbox(
                label="启用社团奖励",
                value=self.current_config.options.club_reward.enabled,
                info=ClubRewardConfig.model_fields['enabled'].description
            )
            with gr.Group(visible=self.current_config.options.club_reward.enabled) as club_reward_group:
                selected_note = gr.Dropdown(
                    choices=list(DailyMoneyShopItems.note_items()),
                    value=self.current_config.options.club_reward.selected_note,
                    label="想在社团奖励中获取到的笔记",
                    interactive=True,
                    info=ClubRewardConfig.model_fields['selected_note'].description
                )
            club_reward_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[club_reward_enabled],
                outputs=[club_reward_group]
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.club_reward.enabled = data['club_reward_enabled']
            config.club_reward.selected_note = DailyMoneyShopItems(data['selected_note'])
        
        return set_config, {
            'club_reward_enabled': club_reward_enabled,
            'selected_note': selected_note
        }

    def _create_capsule_toys_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 扭蛋设置")
            capsule_toys_enabled = gr.Checkbox(
                label="是否启用自动扭蛋机",
                value=self.current_config.options.capsule_toys.enabled,
                info=CapsuleToysConfig.model_fields['enabled'].description
            )
            min_value = 0
            max_value = 10
            with gr.Group(visible=self.current_config.options.capsule_toys.enabled) as capsule_toys_group:
                friend_capsule_toys_count = gr.Number(
                    value=self.current_config.options.capsule_toys.friend_capsule_toys_count,
                    label="好友扭蛋机的扭蛋次数",
                    info=CapsuleToysConfig.model_fields['friend_capsule_toys_count'].description,
                    minimum=0,
                    maximum=5
                )
                sense_capsule_toys_count = gr.Number(
                    value=self.current_config.options.capsule_toys.sense_capsule_toys_count,
                    label="感性扭蛋机的扭蛋次数",
                    info=CapsuleToysConfig.model_fields['sense_capsule_toys_count'].description,
                    minimum=0,
                    maximum=5
                )
                logic_capsule_toys_count = gr.Number(
                    value=self.current_config.options.capsule_toys.logic_capsule_toys_count,
                    label="逻辑扭蛋机的扭蛋次数",
                    info=CapsuleToysConfig.model_fields['logic_capsule_toys_count'].description,
                    minimum=0,
                    maximum=5
                )
                anomaly_capsule_toys_count = gr.Number(
                    value=self.current_config.options.capsule_toys.anomaly_capsule_toys_count,
                    label="非凡扭蛋机的扭蛋次数",
                    info=CapsuleToysConfig.model_fields['anomaly_capsule_toys_count'].description,
                    minimum=0,
                    maximum=5
                )
            capsule_toys_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[capsule_toys_enabled],
                outputs=[capsule_toys_group]
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.capsule_toys.enabled = data['capsule_toys_enabled']
            config.capsule_toys.friend_capsule_toys_count = data['friend_capsule_toys_count']
            config.capsule_toys.sense_capsule_toys_count = data['sense_capsule_toys_count']
            config.capsule_toys.logic_capsule_toys_count = data['logic_capsule_toys_count']
            config.capsule_toys.anomaly_capsule_toys_count = data['anomaly_capsule_toys_count']
        
        return set_config, {
            'capsule_toys_enabled': capsule_toys_enabled,
            'friend_capsule_toys_count': friend_capsule_toys_count,
            'sense_capsule_toys_count': sense_capsule_toys_count,
            'logic_capsule_toys_count': logic_capsule_toys_count,
            'anomaly_capsule_toys_count': anomaly_capsule_toys_count
        }


    def _create_start_game_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 启动游戏设置")
            start_game_enabled = gr.Checkbox(
                label="是否启用 自动启动游戏",
                value=self.current_config.options.start_game.enabled,
                info=StartGameConfig.model_fields['enabled'].description
            )
            with gr.Group(visible=self.current_config.options.start_game.enabled) as start_game_group:
                start_through_kuyo = gr.Checkbox(
                    label="是否通过Kuyo启动游戏",
                    value=self.current_config.options.start_game.start_through_kuyo,
                    info=StartGameConfig.model_fields['start_through_kuyo'].description
                )
                game_package_name = gr.Textbox(
                    value=self.current_config.options.start_game.game_package_name,
                    label="游戏包名",
                    info=StartGameConfig.model_fields['game_package_name'].description
                )
                kuyo_package_name = gr.Textbox(
                    value=self.current_config.options.start_game.kuyo_package_name,
                    label="Kuyo包名",
                    info=StartGameConfig.model_fields['kuyo_package_name'].description
                )
                disable_gakumas_localify = gr.Checkbox(
                    label="禁用 Gakumas Localify 汉化插件",
                    value=self.current_config.options.start_game.disable_gakumas_localify,
                    info=StartGameConfig.model_fields['disable_gakumas_localify'].description
                )
                dmm_game_path = gr.Textbox(
                    value=self.current_config.options.start_game.dmm_game_path or "",
                    label="DMM 版游戏路径",
                    info=StartGameConfig.model_fields['dmm_game_path'].description,
                    placeholder="例：F:\\Games\\gakumas\\gakumas.exe"
                )
            start_game_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[start_game_enabled],
                outputs=[start_game_group]
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.start_game.enabled = data['start_game_enabled']
            config.start_game.start_through_kuyo = data['start_through_kuyo']
            config.start_game.game_package_name = data['game_package_name']
            config.start_game.kuyo_package_name = data['kuyo_package_name']
            config.start_game.disable_gakumas_localify = data['disable_gakumas_localify']
            config.start_game.dmm_game_path = data['dmm_game_path'] if data['dmm_game_path'] else None

        return set_config, {
            'start_game_enabled': start_game_enabled,
            'start_through_kuyo': start_through_kuyo,
            'game_package_name': game_package_name,
            'kuyo_package_name': kuyo_package_name,
            'disable_gakumas_localify': disable_gakumas_localify,
            'dmm_game_path': dmm_game_path
        }


    def _create_end_game_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 关闭游戏设置")
            gr.Markdown("在所有任务执行完毕后执行下面这些操作：\n（执行单个任务时不会触发）")
            exit_kaa = gr.Checkbox(
                label="退出 kaa",
                value=self.current_config.options.end_game.exit_kaa,
                info=EndGameConfig.model_fields['exit_kaa'].description
            )
            kill_game = gr.Checkbox(
                label="关闭游戏",
                value=self.current_config.options.end_game.kill_game,
                info=EndGameConfig.model_fields['kill_game'].description
            )
            kill_dmm = gr.Checkbox(
                label="关闭 DMM",
                value=self.current_config.options.end_game.kill_dmm,
                info=EndGameConfig.model_fields['kill_dmm'].description
            )
            kill_emulator = gr.Checkbox(
                label="关闭模拟器",
                value=self.current_config.options.end_game.kill_emulator,
                info=EndGameConfig.model_fields['kill_emulator'].description
            )
            shutdown = gr.Checkbox(
                label="关闭系统",
                value=self.current_config.options.end_game.shutdown,
                info=EndGameConfig.model_fields['shutdown'].description
            )
            hibernate = gr.Checkbox(
                label="休眠系统",
                value=self.current_config.options.end_game.hibernate,
                info=EndGameConfig.model_fields['hibernate'].description
            )
            restore_gakumas_localify = gr.Checkbox(
                label="恢复 Gakumas Localify 汉化插件状态",
                value=self.current_config.options.end_game.restore_gakumas_localify,
                info=EndGameConfig.model_fields['restore_gakumas_localify'].description
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.end_game.exit_kaa = data['exit_kaa']
            config.end_game.kill_game = data['kill_game']
            config.end_game.kill_dmm = data['kill_dmm']
            config.end_game.kill_emulator = data['kill_emulator']
            config.end_game.shutdown = data['shutdown']
            config.end_game.hibernate = data['hibernate']
            config.end_game.restore_gakumas_localify = data['restore_gakumas_localify']

        return set_config, {
            'exit_kaa': exit_kaa,
            'kill_game': kill_game,
            'kill_dmm': kill_dmm,
            'kill_emulator': kill_emulator,
            'shutdown': shutdown,
            'hibernate': hibernate,
            'restore_gakumas_localify': restore_gakumas_localify
        }

    def _create_activity_funds_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 活动费设置")
            activity_funds = gr.Checkbox(
                label="启用收取活动费",
                value=self.current_config.options.activity_funds.enabled,
                info=ActivityFundsConfig.model_fields['enabled'].description
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.activity_funds.enabled = data['activity_funds']
        
        return set_config, {
            'activity_funds': activity_funds
        }
        
    def _create_presents_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 礼物设置")
            presents = gr.Checkbox(
                label="启用收取礼物",
                value=self.current_config.options.presents.enabled,
                info=PresentsConfig.model_fields['enabled'].description
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.presents.enabled = data['presents']
            
        return set_config, {
            'presents': presents
        }
        
    def _create_mission_reward_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 任务奖励设置")
            mission_reward = gr.Checkbox(
                label="启用领取任务奖励",
                value=self.current_config.options.mission_reward.enabled,
                info=MissionRewardConfig.model_fields['enabled'].description
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.mission_reward.enabled = data['mission_reward']
        
        return set_config, {
            'mission_reward': mission_reward
        }
    
    def _create_upgrade_support_card_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 升级支援卡设置")
            upgrade_support_card_enabled = gr.Checkbox(
                label="启用升级支援卡",
                value=self.current_config.options.upgrade_support_card.enabled,
                info=UpgradeSupportCardConfig.model_fields['enabled'].description
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.upgrade_support_card.enabled = data['upgrade_support_card_enabled']
        
        return set_config, {
            'upgrade_support_card_enabled': upgrade_support_card_enabled
        }
        
    def _create_trace_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 跟踪设置")
            trace_recommend_card_detection = gr.Checkbox(
                label="跟踪推荐卡检测",
                value=self.current_config.options.trace.recommend_card_detection,
                info=TraceConfig.model_fields['recommend_card_detection'].description,
                interactive=True
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.trace.recommend_card_detection = data['trace_recommend_card_detection']
        
        return set_config, {
            'trace_recommend_card_detection': trace_recommend_card_detection
        }

    def _create_settings_tab(self) -> None:
        with gr.Tab("设置"):
            gr.Markdown("## 设置")

            # 模拟器设置
            emulator_settings = self._create_emulator_settings()

            # 商店购买设置
            purchase_settings = self._create_purchase_settings()

            # 活动费设置
            activity_funds_settings = self._create_activity_funds_settings()

            # 礼物设置
            presents_settings = self._create_presents_settings()

            # 工作设置
            work_settings = self._create_work_settings()

            # 竞赛设置
            contest_settings = self._create_contest_settings()

            # 培育设置
            produce_settings = self._create_produce_settings()

            # 任务奖励设置
            mission_reward_settings = self._create_mission_reward_settings()

            # 社团奖励设置
            club_reward_settings = self._create_club_reward_settings()

            # 升级支援卡设置
            capsule_toys_settings = self._create_capsule_toys_settings()

            # 跟踪设置
            trace_settings = self._create_trace_settings()

            # 启动游戏设置
            start_game_settings = self._create_start_game_settings()

            # 关闭游戏设置
            end_game_settings = self._create_end_game_settings()

            save_btn = gr.Button("保存设置")
            result = gr.Markdown()

            # 收集所有设置组件
            all_return_values = [
                emulator_settings,
                purchase_settings,
                activity_funds_settings,
                presents_settings,
                work_settings,
                contest_settings,
                produce_settings,
                mission_reward_settings,
                club_reward_settings,
                capsule_toys_settings,
                start_game_settings,
                end_game_settings,
                trace_settings
            ] # list of (set_func, { 'key': component, ... })
            all_components = [list(ret[1].values()) for ret in all_return_values] # [[c1, c2], [c3], ...]
            all_components = list(chain(*all_components)) # [c1, c2, c3, ...]
            save_btn.click(
                fn=partial(self.save_settings2, all_return_values),
                inputs=all_components,
                outputs=result
            )

    def _create_log_tab(self) -> None:
        with gr.Tab("日志"):
            gr.Markdown("## 日志")

            with gr.Column():
                with gr.Row():
                    export_dumps_btn = gr.Button("导出 dump")
                    export_logs_btn = gr.Button("导出日志")
                with gr.Row():
                    save_report_btn = gr.Button("一键导出报告")
                result_text = gr.Markdown("等待操作\n\n\n")

            export_dumps_btn.click(
                fn=self.export_dumps,
                outputs=[result_text]
            )
            export_logs_btn.click(
                fn=self.export_logs,
                outputs=[result_text]
            )
            save_report_btn.click(
                fn=partial(_save_bug_report, version=self._kaa.version),
                outputs=[result_text]
            )

    def _create_whats_new_tab(self) -> None:
        """创建更新日志标签页，并显示最新版本更新内容"""
        with gr.Tab("更新日志"):
            from kotonebot.kaa.metadata import WHATS_NEW
            gr.Markdown(WHATS_NEW)

    def _create_screen_tab(self) -> None:
        with gr.Tab("画面"):
            gr.Markdown("## 当前设备画面")
            WIDTH = 720 // 3
            HEIGHT = 1280 // 3
            last_update_text = gr.Markdown("上次更新时间：无数据")
            screenshot_display = gr.Image(type="numpy", width=WIDTH, height=HEIGHT)

            def update_screenshot():
                ctx = ContextStackVars.current()
                if ctx is None:
                    return [None, last_update_text.value]
                screenshot = ctx._screenshot
                if screenshot is None:
                    return [None, last_update_text.value]
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
                return screenshot, f"上次更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            gr.Timer(0.3).tick(
                fn=update_screenshot,
                outputs=[screenshot_display, last_update_text]
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
        with gr.Blocks(title="琴音小助手", css="#container { max-width: 800px; margin: auto; padding: 20px; }") as app:
            with gr.Column(elem_id="container"):
                gr.Markdown(f"# 琴音小助手 v{self._kaa.version}")

                with gr.Tabs():
                    self._create_status_tab()
                    self._create_task_tab()
                    self._create_settings_tab()
                    self._create_log_tab()
                    self._create_whats_new_tab()
                    self._create_screen_tab()

        return app

def main(kaa: Kaa | None = None) -> None:
    kaa = kaa or Kaa('./config.json')
    ui = KotoneBotUI(kaa)
    app = ui.create_ui()
    app.launch(inbrowser=True, show_error=True)

if __name__ == "__main__":
    main()
