import os
import traceback
import zipfile
import logging
import copy
import sys
import subprocess
import json
from functools import partial
from itertools import chain
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Literal, Generator, Callable, Any, get_args, cast

import cv2
import gradio as gr

from kaa.errors import ProduceSolutionNotFoundError, UpdateServiceError, UpdateFetchListError
from kaa.main import Kaa
from kaa.db import IdolCard
from kotonebot.backend.context.context import vars
from kotonebot.errors import ContextNotInitializedError
from kotonebot.client.host import Mumu12Host, LeidianHost
from kotonebot.client.host.mumu12_host import Mumu12V5Host
from kotonebot.config.manager import load_config, save_config
from kotonebot.config.base_config import UserConfig, BackendConfig
from kotonebot.backend.context import task_registry, ContextStackVars
from kaa.config import (
    BaseConfig, APShopItems, CapsuleToysConfig, ClubRewardConfig, PurchaseConfig, ActivityFundsConfig,
    PresentsConfig, AssignmentConfig, ContestConfig, ProduceConfig,
    MissionRewardConfig, DailyMoneyShopItems, ProduceAction,
    RecommendCardDetectionMode, TraceConfig, StartGameConfig, EndGameConfig, UpgradeSupportCardConfig, MiscConfig,
    IdleModeConfig,
)
from kaa.config.produce import ProduceSolution, ProduceSolutionManager, ProduceData
from kaa.application.adapter.misc_adapter import create_desktop_shortcut
from kaa.application.core.idle_mode import IdleModeManager
from kaa.application.core.update_service import UpdateService

logger = logging.getLogger(__name__)
GradioInput = gr.Textbox | gr.Number | gr.Checkbox | gr.Dropdown | gr.Radio | gr.Slider | gr.Tabs | gr.Tab
ConfigKey = Literal[
    # backend
    'adb_ip', 'adb_port',
    'screenshot_method', 'keep_screenshots',
    'check_emulator', 'emulator_path',
    'adb_emulator_name', 'emulator_args',
    '_mumu_index', '_mumu12v5_index', '_leidian_index',
    'mumu_background_mode', 'target_screenshot_interval',

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
    'produce_enabled', 'selected_solution_id', 'produce_count', 'produce_timeout_cd', 'enable_fever_month',
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
    'check_update', 'auto_install_update', 'expose_to_lan', 'update_channel',

    # idle
    'idle_enabled', 'idle_seconds', 'idle_minimize_on_pause',

    '_selected_backend_index'
    
]
CONFIG_KEY_VALUE: tuple[str] = get_args(ConfigKey)
ConfigSetFunction = Callable[[BaseConfig, Dict[ConfigKey, Any]], None]
ConfigBuilderReturnValue = Tuple[ConfigSetFunction, Dict[ConfigKey, GradioInput]]

def _save_bug_report(
    title: str,
    description: str,
    version: str,
    upload: bool,
    path: str | None = None
) -> Generator[str, None, str]:
    """
    保存报告

    :param title: 标题
    :param description: 描述
    :param version: 版本号
    :param upload: 是否上传
    :param path: 保存的路径。若为 `None`，则保存到 `./reports/bug-YY-MM-DD HH-MM-SS_标题.zip`。
    :return: 保存的路径
    """
    from kotonebot import device
    from kotonebot.backend.context import ContextStackVars
    import re

    # 过滤标题中的非法文件名字符
    def sanitize_filename(s: str) -> str:
        # 替换 \/:*?"<>| 为空或下划线
        return re.sub(r'[\\/:*?"<>|]', '_', s)

    # 确保目录存在
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)

    error = ""
    if path is None:
        safe_title = sanitize_filename(title)[:30] or "无标题"
        timestamp = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
        path = f'./reports/bug_{timestamp}_{safe_title}.zip'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        # 打包描述文件
        yield "### 打包描述文件..."
        try:
            description_content = f"标题：{title}\n类型：bug\n内容：\n{description}"
            zipf.writestr('description.txt', description_content.encode('utf-8'))
        except Exception as e:
            error += f"保存描述文件失败：{str(e)}\n"

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

        # 打包 conf 文件夹
        if os.path.exists('conf'):
            for root, dirs, files in os.walk('conf'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('conf', os.path.relpath(file_path, 'conf'))
                    zipf.write(file_path, arcname)
                    yield f"### 打包配置文件：{arcname}"

        # 写出版本号
        zipf.writestr('version.txt', version)

    if not upload:
        yield f"### 报告已保存至 {os.path.abspath(path)}"
        return path

    # 上传报告
    from kotonebot.ui.file_host.sensio import upload as upload_file
    yield "### 上传报告..."
    url = ''
    try:
        url = upload_file(path)
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
        self.update_service = UpdateService()
        # IdleModeManager 空闲检测
        def safe_get_is_running():
            try:
                return (self.is_running or self.single_task_running) and not self.is_stopping and not self.is_single_task_stopping and not vars.flow.is_paused
            except ContextNotInitializedError:
                return False

        def safe_get_is_paused():
            try:
                return vars.flow.is_paused
            except ContextNotInitializedError:
                return False

        self.idle_mgr = IdleModeManager(
            get_is_running=safe_get_is_running,
            get_is_paused=safe_get_is_paused,
            get_config=lambda: self.current_config.options.idle,
        )
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
        # 通知 Idle 管理器进入运行态
        self.idle_mgr.notify_on_start()
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
        # 通知 Idle 管理器停止态
        self.idle_mgr.notify_on_stop()

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
        # 通知 Idle 管理器停止态
        self.idle_mgr.notify_on_stop()
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
        except ContextNotInitializedError:
            # ContextNotInitializedError: Forwarded object vars called before initialization.
            # TODO: vars.flow.is_paused 应该要可以在脚本正式启动前就能访问
            text = '未启动'
        # 如果正在停止过程中，禁用暂停按钮
        interactive = not (self.is_stopping or self.is_single_task_stopping)
        return gr.Button(value=text, interactive=interactive)
        
    def reload_config(self) -> bool:
        """
        重新加载配置并重新初始化相关组件

        :return: 是否成功重新加载
        """
        try:
            # 重新加载配置文件
            self._load_config()

            # 重新设置 kaa 的配置
            self._kaa.config_path = "config.json"
            self._kaa.config_type = BaseConfig

            # 重新初始化 kaa（这会重新创建设备和 Context）
            self._setup_kaa()

            # 重新加载 Context 中的配置数据
            from kotonebot.backend.context.context import config
            try:
                config.load()
            except ContextNotInitializedError:
                pass

            logger.info("配置已成功重新加载")
            return True
        except Exception as e:
            logger.error(f"重新加载配置失败：{str(e)}")
            return False

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

        # 先设置options
        for (set_func, _) in return_values:
            set_func(options, data)

        # 验证规则1：截图方法验证
        screenshot_method = self.current_config.backend.screenshot_impl
        backend_type = self.current_config.backend.type

        valid_screenshot_methods = {
            'mumu12': ['adb', 'adb_raw', 'uiautomator2', 'nemu_ipc'],
            'mumu12v5': ['adb', 'adb_raw', 'uiautomator2', 'nemu_ipc'],
            'leidian': ['adb', 'adb_raw', 'uiautomator2'],
            'custom': ['adb', 'adb_raw', 'uiautomator2'],
            'dmm': ['remote_windows', 'windows']
        }

        if screenshot_method not in valid_screenshot_methods.get(backend_type, []):
            gr.Warning(f"截图方法 '{screenshot_method}' 不适用于当前选择的模拟器类型，配置未保存。")
            return ""

        # 验证规则2：若启用培育，那么必须选择培育方案
        if options.produce.enabled and not options.produce.selected_solution_id:
            gr.Warning("启用培育时，必须选择培育方案，配置未保存。")
            return ""

        # 验证规则3：若启用AP/金币购买，对应的商品不能为空
        if options.purchase.ap_enabled and not options.purchase.ap_items:
            gr.Warning("启用AP购买时，AP商店购买物品不能为空，配置未保存。")
            return ""

        if options.purchase.money_enabled and not options.purchase.money_items:
            gr.Warning("启用金币购买时，金币商店购买物品不能为空，配置未保存。")
            return ""

        # 验证通过，保存配置
        self.current_config.options = options
        try:
            save_config(self.config, "config.json")

            # 尝试热重载配置
            if self.reload_config():
                gr.Success("设置已保存并应用！")
            else:
                gr.Warning("设置已保存，但重新加载失败，请重启程序。")
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

            # 快速设置控制区域
            gr.Markdown("### 快速设置")

            with gr.Row():
                select_all_btn = gr.Button("全选", scale=1)
                unselect_all_btn = gr.Button("清空", scale=1)
                select_produce_only_btn = gr.Button("只选培育", scale=1)
                unselect_produce_only_btn = gr.Button("只不选培育", scale=1)

            with gr.Row(elem_classes=["quick-controls-row"]):
                purchase_quick = gr.Checkbox(
                    label="商店",
                    value=self.current_config.options.purchase.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )
                assignment_quick = gr.Checkbox(
                    label="工作",
                    value=self.current_config.options.assignment.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )
                contest_quick = gr.Checkbox(
                    label="竞赛",
                    value=self.current_config.options.contest.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )
                produce_quick = gr.Checkbox(
                    label="培育",
                    value=self.current_config.options.produce.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )
                mission_reward_quick = gr.Checkbox(
                    label="任务",
                    value=self.current_config.options.mission_reward.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )
                club_reward_quick = gr.Checkbox(
                    label="社团",
                    value=self.current_config.options.club_reward.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )
                activity_funds_quick = gr.Checkbox(
                    label="活动费",
                    value=self.current_config.options.activity_funds.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )
                presents_quick = gr.Checkbox(
                    label="礼物",
                    value=self.current_config.options.presents.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )
                capsule_toys_quick = gr.Checkbox(
                    label="扭蛋",
                    value=self.current_config.options.capsule_toys.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )
                upgrade_support_card_quick = gr.Checkbox(
                    label="支援卡",
                    value=self.current_config.options.upgrade_support_card.enabled,
                    interactive=True,
                    elem_classes=["quick-checkbox"]
                )

            def _get_end_action_value() -> str:
                if self.current_config.options.end_game.shutdown:
                    return "关机"
                if self.current_config.options.end_game.hibernate:
                    return "休眠"
                return "什么都不做"

            end_action_dropdown = gr.Dropdown(
                label="完成后：",
                choices=["什么都不做", "关机", "休眠"],
                value=_get_end_action_value(),
                interactive=True
            )

            if self._kaa.upgrade_msg:
                gr.Markdown('### 配置升级报告')
                gr.Markdown(self._kaa.upgrade_msg)
            gr.Markdown('脚本报错或者卡住？前往"反馈"选项卡可以快速导出报告！')

            # 添加调试模式警告
            if self.current_config.keep_screenshots:
                gr.Markdown(
                    '<div style="color: red; font-size: larger;">当前启用了调试功能「保留截图数据」，调试结束后正常使用时建议关闭此选项！</div>',
                    elem_classes=["debug-warning"]
                )

            task_status = gr.Dataframe(
                headers=["任务", "状态"],
                value=self.update_task_status(),
                label="任务状态"
            )

            # MARK: 状态 - 监听函数

            def on_run_click(evt: gr.EventData) -> Tuple[gr.Button, List[List[str]]]:
                result = self.toggle_run()
                # 如果正在停止，禁用按钮
                interactive = not self.is_stopping
                button = gr.Button(value=result[0], interactive=interactive)
                return button, result[1]

            def on_pause_click(evt: gr.EventData) -> str:
                return self.toggle_pause()

            # 快速设置控制的事件处理函数
            def save_quick_setting(success_msg: str, failed_msg: str):
                """保存快速设置并立即应用"""
                try:
                    # 保存配置
                    save_config(self.config, "config.json")

                    # 尝试热重载配置
                    if self.reload_config():
                        gr.Success(success_msg)
                    else:
                        gr.Warning(failed_msg)
                except Exception as e:
                    gr.Error(f"✗ 保存失败：{str(e)}")
            
            def update_and_save_quick_setting(field_name: str, value: bool, display_name: str):
                """更新字段，并保存快速设置并立即应用"""

                # 更新配置
                if field_name == 'purchase':
                    self.current_config.options.purchase.enabled = value
                elif field_name == 'assignment':
                    self.current_config.options.assignment.enabled = value
                elif field_name == 'contest':
                    self.current_config.options.contest.enabled = value
                elif field_name == 'produce':
                    self.current_config.options.produce.enabled = value
                elif field_name == 'mission_reward':
                    self.current_config.options.mission_reward.enabled = value
                elif field_name == 'club_reward':
                    self.current_config.options.club_reward.enabled = value
                elif field_name == 'activity_funds':
                    self.current_config.options.activity_funds.enabled = value
                elif field_name == 'presents':
                    self.current_config.options.presents.enabled = value
                elif field_name == 'capsule_toys':
                    self.current_config.options.capsule_toys.enabled = value
                elif field_name == 'upgrade_support_card':
                    self.current_config.options.upgrade_support_card.enabled = value
                
                # 保存并重载配置
                save_quick_setting(
                    f"✓ {display_name} 已{'启用' if value else '禁用'}",
                    f"⚠ {display_name} 已保存，但重新加载失败"
                )

            def batch_select(default: bool, produce_only: bool, success_msg: str) -> None:
                self.current_config.options.purchase.enabled             = default
                self.current_config.options.assignment.enabled           = default
                self.current_config.options.contest.enabled              = default
                self.current_config.options.produce.enabled              = produce_only
                self.current_config.options.mission_reward.enabled       = default
                self.current_config.options.club_reward.enabled          = default
                self.current_config.options.activity_funds.enabled       = default
                self.current_config.options.presents.enabled             = default
                self.current_config.options.capsule_toys.enabled         = default
                self.current_config.options.upgrade_support_card.enabled = default

                save_quick_setting(success_msg, f"⚠ 数据已保存，但重新加载失败")

            # MARK: 状态 - UI回调函数

            run_btn.click(
                fn=on_run_click,
                outputs=[run_btn, task_status]
            )

            pause_btn.click(
                fn=on_pause_click,
                outputs=[pause_btn]
            )

            select_all_btn.click(
                fn=lambda: batch_select(True, True, f"✓ 全选成功"),
                outputs=[]
            )

            unselect_all_btn.click(
                fn=lambda: batch_select(False, False, f"✓ 清空成功"),
                outputs=[]
            )

            select_produce_only_btn.click(
                fn=lambda: batch_select(False, True, f"✓ 只选培育成功"),
                outputs=[]
            )

            unselect_produce_only_btn.click(
                fn=lambda: batch_select(True, False, f"✓ 只不选培育成功"),
                outputs=[]
            )

            # 绑定快速设置控制的事件

            # 以下回调函数均由.change修改为.input，这样回调函数就只会在用户操作时触发，避免全选功能导致反复触发
            purchase_quick.input(
                fn=lambda x: update_and_save_quick_setting('purchase', x, '商店'),
                inputs=[purchase_quick]
            )
            assignment_quick.input(
                fn=lambda x: update_and_save_quick_setting('assignment', x, '工作'),
                inputs=[assignment_quick]
            )
            contest_quick.input(
                fn=lambda x: update_and_save_quick_setting('contest', x, '竞赛'),
                inputs=[contest_quick]
            )
            produce_quick.input(
                fn=lambda x: update_and_save_quick_setting('produce', x, '培育'),
                inputs=[produce_quick]
            )
            mission_reward_quick.input(
                fn=lambda x: update_and_save_quick_setting('mission_reward', x, '任务奖励'),
                inputs=[mission_reward_quick]
            )
            club_reward_quick.input(
                fn=lambda x: update_and_save_quick_setting('club_reward', x, '社团奖励'),
                inputs=[club_reward_quick]
            )
            activity_funds_quick.input(
                fn=lambda x: update_and_save_quick_setting('activity_funds', x, '活动费'),
                inputs=[activity_funds_quick]
            )
            presents_quick.input(
                fn=lambda x: update_and_save_quick_setting('presents', x, '礼物'),
                inputs=[presents_quick]
            )
            capsule_toys_quick.input(
                fn=lambda x: update_and_save_quick_setting('capsule_toys', x, '扭蛋'),
                inputs=[capsule_toys_quick]
            )
            upgrade_support_card_quick.input(
                fn=lambda x: update_and_save_quick_setting('upgrade_support_card', x, '支援卡升级'),
                inputs=[upgrade_support_card_quick]
            )

            # 处理完成后操作下拉框
            def save_quick_end_action(action: str):
                try:
                    if action == "关机":
                        self.current_config.options.end_game.shutdown = True
                        self.current_config.options.end_game.hibernate = False
                    elif action == "休眠":
                        self.current_config.options.end_game.shutdown = False
                        self.current_config.options.end_game.hibernate = True
                    else:  # 什么都不做
                        self.current_config.options.end_game.shutdown = False
                        self.current_config.options.end_game.hibernate = False

                    save_config(self.config, "config.json")

                    # 尝试热重载配置
                    if self.reload_config():
                        gr.Success(f"✓ 完成后操作已设置为 {action}")
                    else:
                        gr.Warning("⚠ 设置已保存，但重新加载失败")
                except Exception as e:
                    gr.Error(f"✗ 保存失败：{str(e)}")

            end_action_dropdown.change(
                fn=save_quick_end_action,
                inputs=[end_action_dropdown]
            )

            # 添加定时器，分别更新按钮状态和任务状态
            def update_run_button_status():
                text, interactive = self.get_button_status()
                return gr.Button(value=text, interactive=interactive)

            def update_quick_checkboxes():
                """更新快速设置区域控件的状态，确保与设置同步"""
                end_action_val = _get_end_action_value()
                return [
                    gr.Checkbox(value=self.current_config.options.purchase.enabled),
                    gr.Checkbox(value=self.current_config.options.assignment.enabled),
                    gr.Checkbox(value=self.current_config.options.contest.enabled),
                    gr.Checkbox(value=self.current_config.options.produce.enabled),
                    gr.Checkbox(value=self.current_config.options.mission_reward.enabled),
                    gr.Checkbox(value=self.current_config.options.club_reward.enabled),
                    gr.Checkbox(value=self.current_config.options.activity_funds.enabled),
                    gr.Checkbox(value=self.current_config.options.presents.enabled),
                    gr.Checkbox(value=self.current_config.options.capsule_toys.enabled),
                    gr.Checkbox(value=self.current_config.options.upgrade_support_card.enabled),
                    gr.Dropdown(value=end_action_val),
                ]

            gr.Timer(1.0).tick(
                fn=update_run_button_status,
                outputs=[run_btn]
            )
            gr.Timer(1.0).tick(
                fn=self.get_pause_button_with_interactive,
                outputs=[pause_btn]
            )
            gr.Timer(2.0).tick(
                fn=update_quick_checkboxes,
                outputs=[
                    purchase_quick, assignment_quick, contest_quick, produce_quick,
                    mission_reward_quick, club_reward_quick, activity_funds_quick, presents_quick,
                    capsule_toys_quick, upgrade_support_card_quick, end_action_dropdown
                ]
            )
            gr.Timer(1.0).tick(
                fn=self.update_task_status,
                outputs=[task_status]
            )

    def _create_task_tab(self) -> None:
        with gr.Tab("任务"):
            gr.Markdown("## 执行任务")

            # 第一行：统一的停止和暂停按钮
            with gr.Row():
                stop_all_btn = gr.Button("停止任务", variant="stop", scale=1)
                pause_btn = gr.Button("暂停", scale=1)
            
            task_result = gr.Markdown("")

            # 获取所有任务并创建列表布局
            tasks = list(task_registry.values())
            task_buttons = []  # 存储所有任务按钮的引用
            
            # 为每个任务创建一行：左侧启动按钮，右侧任务名
            for task in tasks:
                with gr.Row():
                    with gr.Column(scale=1, min_width=50):
                        task_btn = gr.Button("启动", variant="primary", size="sm")
                        task_buttons.append((task_btn, task.name))
                    with gr.Column(scale=7):
                        gr.Markdown(f"{task.name}")

            # 事件处理函数
            def start_single_task_by_name(task_name: str):
                """启动指定任务并返回状态信息及所有按钮的更新状态"""
                if self.single_task_running:
                    return ["已有任务正在运行"] + [gr.Button(interactive=False) for _ in task_buttons]
                
                # 启动任务
                result = self.start_single_task(task_name)
                status_msg = result[1]
                
                # 如果成功启动，禁用所有任务按钮
                if self.single_task_running:
                    disabled_buttons = [gr.Button(value="运行中", interactive=False) for _ in task_buttons]
                else:
                    disabled_buttons = [gr.Button(value="启动", interactive=True) for _ in task_buttons]
                
                return [status_msg] + disabled_buttons

            def stop_all_tasks():
                """停止所有任务并重置按钮状态"""
                if not self.single_task_running:
                    return ["没有正在运行的任务"] + [gr.Button(value="启动", interactive=True) for _ in task_buttons]
                
                # 停止任务
                result = self.stop_single_task()
                status_msg = result[1]
                
                # 如果正在停止中，显示停止中状态
                if self.is_single_task_stopping:
                    disabled_buttons = [gr.Button(value="停止中", interactive=False) for _ in task_buttons]
                else:
                    disabled_buttons = [gr.Button(value="启动", interactive=True) for _ in task_buttons]
                
                return [status_msg] + disabled_buttons

            def get_task_buttons_status() -> List[gr.Button]:
                """获取所有任务按钮的状态"""
                if not hasattr(self, 'run_status') or not self.run_status.running:
                    self.single_task_running = False
                    self.is_single_task_stopping = False
                    return [gr.Button(value="启动", interactive=True) for _ in task_buttons]

                if self.is_single_task_stopping:
                    return [gr.Button(value="停止中", interactive=False) for _ in task_buttons]

                if self.single_task_running:
                    return [gr.Button(value="运行中", interactive=False) for _ in task_buttons]

                return [gr.Button(value="启动", interactive=True) for _ in task_buttons]

            def get_single_task_status() -> str:
                """获取任务状态信息"""
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

            def on_pause_click() -> str:
                return self.toggle_pause()

            # 绑定事件 - 为每个任务按钮绑定点击事件
            def create_task_handler(task_name: str):
                """创建任务处理函数，避免闭包问题"""
                def handler():
                    return start_single_task_by_name(task_name)
                return handler

            for task_btn, task_name in task_buttons:
                task_btn.click(
                    fn=create_task_handler(task_name),
                    outputs=[task_result] + [btn for btn, _ in task_buttons]
                )

            # 绑定停止按钮事件
            stop_all_btn.click(
                fn=stop_all_tasks,
                outputs=[task_result] + [btn for btn, _ in task_buttons]
            )

            # 绑定暂停按钮事件
            pause_btn.click(
                fn=on_pause_click,
                outputs=[pause_btn]
            )

            # 添加定时器更新按钮状态和任务状态
            gr.Timer(1.0).tick(
                fn=get_task_buttons_status,
                outputs=[btn for btn, _ in task_buttons]
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
        current_tab = 0

        def _update_emulator_tab_options(impl_value: str, selected_index: int):
            nonlocal current_tab
            current_tab = selected_index
            choices = ['adb', 'adb_raw', 'uiautomator2', 'windows', 'remote_windows', 'nemu_ipc']
            if impl_value not in choices:
                new_value = choices[0]
            else:
                new_value = impl_value
            return new_value

        with gr.Tabs(selected=self.current_config.backend.type):
            with gr.Tab("MuMu 12 v4.x", id="mumu12") as tab_mumu12:
                gr.Markdown("已选中 MuMu 12 v4.x 模拟器")
                mumu_refresh_message = gr.Markdown("<div style='color: red;'>点击下方「刷新」按钮载入信息</div>", visible=True)
                mumu_instance = gr.Dropdown(
                    label="选择多开实例",
                    choices=[],
                    interactive=True
                )
                mumu_refresh_btn = gr.Button("刷新")

                def refresh_mumu_instances():
                    try:
                        instances = Mumu12Host.list()
                        is_mumu12 = self.current_config.backend.type == 'mumu12'
                        current_id = self.current_config.backend.instance_id if is_mumu12 else None
                        choices = [(i.name, i.id) for i in instances]
                        return gr.Dropdown(choices=choices, value=current_id, interactive=True), gr.Markdown(visible=False)
                    except Exception as e:
                        logger.exception('Failed to list installed MuMu12')
                        gr.Error("获取 MuMu12 模拟器列表失败，请升级模拟器到最新版本。若问题依旧，前往 QQ 群、QQ 频道或 Github 反馈 bug。")
                        return gr.Dropdown(choices=[], interactive=True), gr.Markdown(visible=True)

                mumu_refresh_btn.click(
                    fn=refresh_mumu_instances,
                    outputs=[mumu_instance, mumu_refresh_message]
                )

                # 如果当前是 MuMu 模拟器且有配置的 instance_id，立即加载实例列表
                if self.current_config.backend.type == 'mumu12' and self.current_config.backend.instance_id:
                    try:
                        instances = Mumu12Host.list()
                        choices = [(i.name, i.id) for i in instances]
                        mumu_instance.choices = choices
                        mumu_instance.value = self.current_config.backend.instance_id
                        mumu_refresh_message.visible = False
                    except Exception as e:
                        logger.exception('Failed to auto-load MuMu12 instances')

                mumu_background_mode = gr.Checkbox(
                    label="MuMu12 模拟器后台保活模式",
                    value=self.current_config.backend.mumu_background_mode,
                    info=BackendConfig.model_fields['mumu_background_mode'].description,
                    interactive=True
                )

            with gr.Tab("MuMu 12 v5.x", id="mumu12v5") as tab_mumu12v5:
                gr.Markdown("已选中 MuMu 12 v5.x 模拟器")
                mumu_refresh_message = gr.Markdown("<div style='color: red;'>点击下方「刷新」按钮载入信息</div>", visible=True)
                mumu_instance12v5 = gr.Dropdown(
                    label="选择多开实例",
                    choices=[],
                    interactive=True
                )
                mumu_refresh_btn = gr.Button("刷新")

                def refresh_mumu12v5_instances():
                    try:
                        instances = Mumu12V5Host.list()
                        is_mumu12v5 = self.current_config.backend.type == 'mumu12v5'
                        current_id = self.current_config.backend.instance_id if is_mumu12v5 else None
                        choices = [(i.name, i.id) for i in instances]
                        return gr.Dropdown(choices=choices, value=current_id, interactive=True), gr.Markdown(visible=False)
                    except Exception as e:
                        logger.exception('Failed to list installed MuMu12v5')
                        gr.Error("获取 MuMu12 模拟器列表失败，请升级模拟器到最新版本。若问题依旧，前往 QQ 群、QQ 频道或 Github 反馈 bug。")
                        return gr.Dropdown(choices=[], interactive=True), gr.Markdown(visible=True)

                mumu_refresh_btn.click(
                    fn=refresh_mumu12v5_instances,
                    outputs=[mumu_instance12v5, mumu_refresh_message]
                )

                # 如果当前是 MuMu 模拟器且有配置的 instance_id，立即加载实例列表
                if self.current_config.backend.type == 'mumu12v5' and self.current_config.backend.instance_id:
                    try:
                        instances = Mumu12V5Host.list()
                        choices = [(i.name, i.id) for i in instances]
                        mumu_instance12v5.choices = choices
                        mumu_instance12v5.value = self.current_config.backend.instance_id
                        mumu_refresh_message.visible = False
                    except Exception as e:
                        logger.exception('Failed to auto-load MuMu12v5 instances')

                mumu_background_mode = gr.Checkbox(
                    label="MuMu12v5 模拟器后台保活模式",
                    value=self.current_config.backend.mumu_background_mode,
                    info=BackendConfig.model_fields['mumu_background_mode'].description,
                    interactive=True
                )

            with gr.Tab("雷电", id="leidian") as tab_leidian:
                gr.Markdown("已选中雷电模拟器")
                leidian_refresh_message = gr.Markdown("<div style='color: red;'>点击下方「刷新」按钮载入信息</div>", visible=True)
                leidian_instance = gr.Dropdown(
                    label="选择多开实例",
                    choices=[],
                    interactive=True
                )
                leidian_refresh_btn = gr.Button("刷新")

                def refresh_leidian_instances():
                    try:
                        instances = LeidianHost.list()
                        is_leidian = self.current_config.backend.type == 'leidian'
                        current_id = self.current_config.backend.instance_id if is_leidian else None
                        choices = [(i.name, i.id) for i in instances]
                        return gr.Dropdown(choices=choices, value=current_id, interactive=True), gr.Markdown(visible=False)
                    except Exception as e:
                        logger.exception('Failed to list installed Leidian')
                        gr.Error("获取雷电模拟器列表失败，请前往 QQ 群、QQ 频道或 Github 反馈 bug。")
                        return gr.Dropdown(choices=[], interactive=True), gr.Markdown(visible=True)

                leidian_refresh_btn.click(
                    fn=refresh_leidian_instances,
                    outputs=[leidian_instance, leidian_refresh_message]
                )

                # 如果当前是雷电模拟器且有配置的 instance_id，立即加载实例列表
                if self.current_config.backend.type == 'leidian' and self.current_config.backend.instance_id:
                    try:
                        instances = LeidianHost.list()
                        choices = [(i.name, i.id) for i in instances]
                        leidian_instance.choices = choices
                        leidian_instance.value = self.current_config.backend.instance_id
                        leidian_refresh_message.visible = False
                    except Exception as e:
                        logger.exception('Failed to auto-load Leidian instances')
                        # 保持显示刷新提示

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
                gr.Markdown("**暂停快捷键 <kbd>Ctrl</kbd> + <kbd>F4</kbd>，停止快捷键 <kbd>Ctrl</kbd> + <kbd>F3</kbd>**")

        choices = ['adb', 'adb_raw', 'uiautomator2', 'windows', 'remote_windows', 'nemu_ipc']
        screenshot_impl = gr.Dropdown(
            choices=choices,
            value=self.current_config.backend.screenshot_impl,
            label="截图方法",
            info=BackendConfig.model_fields['screenshot_impl'].description,
            interactive=True
        )


        target_screenshot_interval = gr.Number(
            label="最小截图间隔（秒）",
            value=self.current_config.backend.target_screenshot_interval,
            info=BackendConfig.model_fields['target_screenshot_interval'].description,
            minimum=0,
            step=0.1,
            interactive=True
        )

        tab_mumu12.select(fn=partial(_update_emulator_tab_options, selected_index=0), inputs=[screenshot_impl], outputs=[screenshot_impl])
        tab_mumu12v5.select(fn=partial(_update_emulator_tab_options, selected_index=1), inputs=[screenshot_impl], outputs=[screenshot_impl])
        tab_leidian.select(fn=partial(_update_emulator_tab_options, selected_index=2), inputs=[screenshot_impl], outputs=[screenshot_impl])
        tab_custom.select(fn=partial(_update_emulator_tab_options, selected_index=3), inputs=[screenshot_impl], outputs=[screenshot_impl])
        tab_dmm.select(fn=partial(_update_emulator_tab_options, selected_index=4), inputs=[screenshot_impl], outputs=[screenshot_impl])

        # 初值
        if self.current_config.backend.type == 'mumu12':
            _update_emulator_tab_options(
                impl_value=self.current_config.backend.screenshot_impl,
                selected_index=0
            )
        elif self.current_config.backend.type == 'mumu12v5':
            _update_emulator_tab_options(
                impl_value=self.current_config.backend.screenshot_impl,
                selected_index=1
            )
        elif self.current_config.backend.type == 'leidian':
            _update_emulator_tab_options(
                impl_value=self.current_config.backend.screenshot_impl,
                selected_index=2
            )
        elif self.current_config.backend.type == 'custom':
            _update_emulator_tab_options(
                impl_value=self.current_config.backend.screenshot_impl,
                selected_index=3
            )
        elif self.current_config.backend.type == 'dmm':
            _update_emulator_tab_options(
                impl_value=self.current_config.backend.screenshot_impl,
                selected_index=4
            )
        else:
            gr.Warning(f"未知的模拟器类型：{self.current_config.backend.type}")

        def set_config(_: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            # current_tab is updated by _update_emulator_tab_options
            if current_tab == 0:  # Mumu
                self.current_config.backend.type = 'mumu12'
                self.current_config.backend.instance_id = data['_mumu_index']
                self.current_config.backend.mumu_background_mode = data['mumu_background_mode']
            elif current_tab == 1:  # Mumu12v5
                self.current_config.backend.type = 'mumu12v5'
                self.current_config.backend.instance_id = data['_mumu12v5_index']
                self.current_config.backend.mumu_background_mode = data['mumu_background_mode']
            elif current_tab == 2:  # Leidian
                self.current_config.backend.type = 'leidian'
                self.current_config.backend.instance_id = data['_leidian_index']
            elif current_tab == 3:  # Custom
                self.current_config.backend.type = 'custom'
                self.current_config.backend.instance_id = None
                self.current_config.backend.adb_ip = data['adb_ip']
                self.current_config.backend.adb_port = data['adb_port']
                self.current_config.backend.adb_emulator_name = data['adb_emulator_name']
                self.current_config.backend.check_emulator = data['check_emulator']
                self.current_config.backend.emulator_path = data['emulator_path']
                self.current_config.backend.emulator_args = data['emulator_args']
            elif current_tab == 4:  # DMM
                self.current_config.backend.type = 'dmm'
                self.current_config.backend.instance_id = None  # DMM doesn't use instance_id here

            # Common settings for all backend types
            self.current_config.backend.screenshot_impl = data['screenshot_method']
            self.current_config.backend.target_screenshot_interval = data['target_screenshot_interval']

        return set_config, {
            'adb_ip': adb_ip,
            'adb_port': adb_port,
            'screenshot_method': screenshot_impl,
            'target_screenshot_interval': target_screenshot_interval,
            'check_emulator': check_emulator,
            'emulator_path': emulator_path,
            'adb_emulator_name': adb_emulator_name,
            'emulator_args': emulator_args,
            '_mumu_index': mumu_instance,
            '_leidian_index': leidian_instance,
            '_mumu12v5_index': mumu_instance12v5,
            'mumu_background_mode': mumu_background_mode
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

                money_refresh = gr.Checkbox(
                    label="每日一次免费刷新金币商店",
                    value=self.current_config.options.purchase.money_refresh,
                    info=PurchaseConfig.model_fields['money_refresh'].description
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
            config.purchase.money_refresh = data['money_refresh']
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
            'money_items': money_items,
            'money_refresh': money_refresh
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

                when_no_set_choices = [
                    ("通知我并跳过竞赛", "remind"),
                    ("提醒我并等待手动编成", "wait"),
                    ("使用自动编成并提醒我", "auto_set"),
                    ("使用自动编成", "auto_set_silent")
                ]
                when_no_set = gr.Dropdown(
                    choices=when_no_set_choices,
                    value=self.current_config.options.contest.when_no_set,
                    label="竞赛队伍未编成时",
                    interactive=True,
                    info=ContestConfig.model_fields['when_no_set'].description
                )
            contest_enabled.change(
                fn=lambda x: gr.Group(visible=x),
                inputs=[contest_enabled],
                outputs=[contest_group]
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.contest.enabled = data['contest_enabled']
            config.contest.select_which_contestant = data['select_which_contestant']
            config.contest.when_no_set = data['when_no_set']

        return set_config, {
            'contest_enabled': contest_enabled,
            'select_which_contestant': select_which_contestant,
            'when_no_set': when_no_set
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
                # 培育方案管理区域
                solution_manager = ProduceSolutionManager()
                solutions = solution_manager.list()
                solution_choices = [(f"{sol.name} - {sol.description or '无描述'}", sol.id) for sol in solutions]

                selected_solution_id = self.current_config.options.produce.selected_solution_id
                solution_dropdown = gr.Dropdown(
                    choices=solution_choices,
                    value=selected_solution_id,
                    label="当前使用的培育方案",
                    interactive=True
                )

                produce_count = gr.Number(
                    minimum=1,
                    value=self.current_config.options.produce.produce_count,
                    label="培育次数",
                    interactive=True,
                    info=ProduceConfig.model_fields['produce_count'].description
                )

                produce_timeout_cd = gr.Number(
                    minimum=20,
                    value=self.current_config.options.produce.produce_timeout_cd,
                    label="推荐卡检测用时上限",
                    interactive=True,
                    info=ProduceConfig.model_fields['produce_timeout_cd'].description
                )

                enable_fever_month = gr.Radio(
                    label="自动启用强化月间",
                    choices=[("不操作", "ignore"), ("自动启用", "on"), ("自动禁用", "off")],
                    value=self.current_config.options.produce.enable_fever_month,
                    info=ProduceConfig.model_fields['enable_fever_month'].description,
                    interactive=True
                )

            # 绑定启用状态变化事件
            def on_produce_enabled_change(enabled):
                return gr.Group(visible=enabled)

            produce_enabled.change(
                fn=on_produce_enabled_change,
                inputs=[produce_enabled],
                outputs=[produce_group]
            )

        # 存储设置Tab中的下拉框引用，供培育Tab使用
        self._settings_solution_dropdown = solution_dropdown

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.produce.enabled = data['produce_enabled']
            config.produce.selected_solution_id = data.get('selected_solution_id')
            config.produce.produce_count = data.get('produce_count', 1)
            config.produce.produce_timeout_cd = data.get('produce_timeout_cd', 60)
            config.produce.enable_fever_month = data.get('enable_fever_month', 'ignore')

        return set_config, {
            'produce_enabled': produce_enabled,
            'selected_solution_id': solution_dropdown,
            'produce_count': produce_count,
            'produce_timeout_cd': produce_timeout_cd,
            'enable_fever_month': enable_fever_month
        }


    def _create_produce_tab(self) -> None:
        """创建培育Tab"""
        with gr.Tab("培育"):
            gr.Markdown("## 培育管理")

            # 培育方案管理区域
            solution_manager = ProduceSolutionManager()
            solutions = solution_manager.list()
            solution_choices = [(f"{sol.name} - {sol.description or '无描述'}", sol.id) for sol in solutions]

            selected_solution_id = self.current_config.options.produce.selected_solution_id
            solution_dropdown = gr.Dropdown(
                choices=solution_choices,
                value=selected_solution_id,
                label="选择培育方案",
                interactive=True
            )

            # 获取设置Tab中的下拉框引用
            settings_dropdown = getattr(self, '_settings_solution_dropdown', None)

            with gr.Row():
                new_solution_btn = gr.Button("新建培育", scale=1)
                delete_solution_btn = gr.Button("删除当前培育", scale=1)

            # 培育方案详细设置区域
            with gr.Group() as solution_settings_group:
                # 获取当前选中的方案数据
                current_solution = None
                if selected_solution_id:
                    try:
                        current_solution = solution_manager.read(selected_solution_id)
                    except ProduceSolutionNotFoundError:
                        pass

                if current_solution is None:
                    # 如果没有选中方案，隐藏所有设置组件
                    solution_name = gr.Textbox(label="方案名称", value="", visible=False)
                    solution_description = gr.Textbox(label="方案描述", value="", visible=False)
                    # 其他设置组件都设为不可见
                    produce_mode = gr.Dropdown(
                        choices=["regular", "pro", "master"],
                        label="培育模式",
                        info="进行一次 REGULAR 培育需要 ~30min，进行一次 PRO 培育需要 ~1h（具体视设备性能而定）。",
                        visible=False
                    )

                    # 添加偶像选择
                    idol_choices = []
                    for idol in IdolCard.all():
                        if idol.is_another:
                            idol_choices.append((f'{idol.name}　「{idol.another_name}」', idol.skin_id))
                        else:
                            idol_choices.append((f'{idol.name}', idol.skin_id))

                    produce_idols = gr.Dropdown(
                        choices=idol_choices,
                        label="选择要培育的偶像",
                        multiselect=False,
                        info="要培育偶像的 IdolCardSkin.id。",
                        visible=False
                    )
                    kotone_warning = gr.Markdown(visible=False)
                    auto_set_memory = gr.Checkbox(
                        label="自动编成回忆",
                        info="是否自动编成回忆。此选项优先级高于回忆编成编号。",
                        visible=False
                    )
                    with gr.Group(visible=False) as memory_sets_group:
                        memory_sets = gr.Dropdown(
                            choices=[str(i) for i in range(1, 11)],
                            label="回忆编成编号",
                            multiselect=False,
                            info="要使用的回忆编成编号，从 1 开始。",
                            visible=False
                        )
                    auto_set_support = gr.Checkbox(
                        label="自动编成支援卡",
                        info="是否自动编成支援卡。此选项优先级高于支援卡编成编号。",
                        visible=False
                    )
                    with gr.Group(visible=False) as support_card_sets_group:
                        support_card_sets = gr.Dropdown(
                            choices=[str(i) for i in range(1, 11)],
                            label="支援卡编成编号",
                            multiselect=False,
                            info="要使用的支援卡编成编号，从 1 开始。",
                            visible=False
                        )
                    use_pt_boost = gr.Checkbox(
                        label="使用支援强化 Pt 提升",
                        info="是否使用支援强化 Pt 提升。",
                        visible=False
                    )
                    use_note_boost = gr.Checkbox(
                        label="使用笔记数提升",
                        info="是否使用笔记数提升。",
                        visible=False
                    )
                    follow_producer = gr.Checkbox(
                        label="关注租借了支援卡的制作人",
                        info="是否关注租借了支援卡的制作人。",
                        visible=False
                    )
                    self_study_lesson = gr.Dropdown(
                        choices=['dance', 'visual', 'vocal'],
                        label='文化课自习时选项',
                        info='自习课类型。',
                        visible=False
                    )
                    prefer_lesson_ap = gr.Checkbox(
                        label="SP 课程优先",
                        info="优先 SP 课程。启用后，若出现 SP 课程，则会优先执行 SP 课程，而不是推荐课程。若出现多个 SP 课程，随机选择一个。",
                        visible=False
                    )
                    actions_order = gr.Dropdown(
                        choices=[(action.display_name, action.value) for action in ProduceAction],
                        label="行动优先级",
                        info="每一周的行动将会按这里设置的优先级执行。",
                        multiselect=True,
                        visible=False
                    )
                    recommend_card_detection_mode = gr.Dropdown(
                        choices=[
                            (RecommendCardDetectionMode.NORMAL.display_name, RecommendCardDetectionMode.NORMAL.value),
                            (RecommendCardDetectionMode.STRICT.display_name, RecommendCardDetectionMode.STRICT.value)
                        ],
                        label="推荐卡检测模式",
                        info="推荐卡检测模式。严格模式下，识别速度会降低，但识别准确率会提高。推荐Kotone使用严格模式，其他角色使用正常模式。",
                        visible=False
                    )
                    use_ap_drink = gr.Checkbox(
                        label="AP 不足时自动使用 AP 饮料",
                        info="AP 不足时自动使用 AP 饮料",
                        visible=False
                    )
                    skip_commu = gr.Checkbox(
                        label="检测并跳过交流",
                        info="检测并跳过交流",
                        visible=False
                    )
                    save_solution_btn = gr.Button("保存培育方案", variant="primary", visible=False)
                else:
                    # 显示选中方案的设置
                    solution_name = gr.Textbox(
                        label="方案名称",
                        value=current_solution.name,
                        interactive=True
                    )
                    solution_description = gr.Textbox(
                        label="方案描述",
                        value=current_solution.description or "",
                        interactive=True
                    )

                    produce_mode = gr.Dropdown(
                        choices=["regular", "pro", "master"],
                        value=current_solution.data.mode,
                        label="培育模式",
                        info="进行一次 REGULAR 培育需要 ~30min，进行一次 PRO 培育需要 ~1h（具体视设备性能而定）。"
                    )

                    # 添加偶像选择
                    idol_choices = []
                    for idol in IdolCard.all():
                        if idol.is_another:
                            idol_choices.append((f'{idol.name}　「{idol.another_name}」', idol.skin_id))
                        else:
                            idol_choices.append((f'{idol.name}', idol.skin_id))

                    produce_idols = gr.Dropdown(
                        choices=idol_choices,
                        value=current_solution.data.idol,
                        label="选择要培育的偶像",
                        multiselect=False,
                        interactive=True,
                        info="要培育偶像的 IdolCardSkin.id。"
                    )

                    has_kotone = bool(current_solution.data.idol and "藤田ことね" in current_solution.data.idol)
                    is_strict_mode = current_solution.data.recommend_card_detection_mode == RecommendCardDetectionMode.STRICT
                    kotone_warning = gr.Markdown(
                        visible=has_kotone and not is_strict_mode,
                        value="使用「藤田ことね」进行培育时，确保将「推荐卡检测模式」设置为「严格模式」"
                    )

                    auto_set_memory = gr.Checkbox(
                        label="自动编成回忆",
                        value=current_solution.data.auto_set_memory,
                        info="是否自动编成回忆。此选项优先级高于回忆编成编号。"
                    )

                    with gr.Group(visible=not current_solution.data.auto_set_memory) as memory_sets_group:
                        memory_sets = gr.Dropdown(
                            choices=[str(i) for i in range(1, 21)],  # 最多20个编成位
                            value=str(current_solution.data.memory_set) if current_solution.data.memory_set else None,
                            label="回忆编成编号",
                            multiselect=False,
                            interactive=True,
                            info="要使用的回忆编成编号，从 1 开始。"
                        )

                    auto_set_support = gr.Checkbox(
                        label="自动编成支援卡",
                        value=current_solution.data.auto_set_support_card,
                        info="是否自动编成支援卡。此选项优先级高于支援卡编成编号。"
                    )

                    with gr.Group(visible=not current_solution.data.auto_set_support_card) as support_card_sets_group:
                        support_card_sets = gr.Dropdown(
                            choices=[str(i) for i in range(1, 21)],  # 最多20个编成位
                            value=str(current_solution.data.support_card_set) if current_solution.data.support_card_set else None,
                            label="支援卡编成编号",
                            multiselect=False,
                            interactive=True,
                            info="要使用的支援卡编成编号，从 1 开始。"
                        )
                    use_pt_boost = gr.Checkbox(
                        label="使用支援强化 Pt 提升",
                        value=current_solution.data.use_pt_boost,
                        info="是否使用支援强化 Pt 提升。"
                    )
                    use_note_boost = gr.Checkbox(
                        label="使用笔记数提升",
                        value=current_solution.data.use_note_boost,
                        info="是否使用笔记数提升。"
                    )
                    follow_producer = gr.Checkbox(
                        label="关注租借了支援卡的制作人",
                        value=current_solution.data.follow_producer,
                        info="是否关注租借了支援卡的制作人。"
                    )
                    self_study_lesson = gr.Dropdown(
                        choices=['dance', 'visual', 'vocal'],
                        value=current_solution.data.self_study_lesson,
                        label='文化课自习时选项',
                        info='自习课类型。'
                    )
                    prefer_lesson_ap = gr.Checkbox(
                        label="SP 课程优先",
                        value=current_solution.data.prefer_lesson_ap,
                        info="优先 SP 课程。启用后，若出现 SP 课程，则会优先执行 SP 课程，而不是推荐课程。若出现多个 SP 课程，随机选择一个。"
                    )
                    actions_order = gr.Dropdown(
                        choices=[(action.display_name, action.value) for action in ProduceAction],
                        value=[action.value for action in current_solution.data.actions_order],
                        label="行动优先级",
                        info="每一周的行动将会按这里设置的优先级执行。",
                        multiselect=True
                    )
                    recommend_card_detection_mode = gr.Dropdown(
                        choices=[
                            (RecommendCardDetectionMode.NORMAL.display_name, RecommendCardDetectionMode.NORMAL.value),
                            (RecommendCardDetectionMode.STRICT.display_name, RecommendCardDetectionMode.STRICT.value)
                        ],
                        value=current_solution.data.recommend_card_detection_mode.value,
                        label="推荐卡检测模式",
                        info="推荐卡检测模式。严格模式下，识别速度会降低，但识别准确率会提高。推荐Kotone使用严格模式，其他角色使用正常模式。"
                    )
                    use_ap_drink = gr.Checkbox(
                        label="AP 不足时自动使用 AP 饮料",
                        value=current_solution.data.use_ap_drink,
                        info="AP 不足时自动使用 AP 饮料"
                    )
                    skip_commu = gr.Checkbox(
                        label="检测并跳过交流",
                        value=current_solution.data.skip_commu,
                        info="检测并跳过交流"
                    )

                    # 添加保存按钮
                    save_solution_btn = gr.Button("保存培育方案", variant="primary")

            # 添加事件处理
            def update_kotone_warning(selected_idol, recommend_card_detection_mode):
                # Handle case where selected_idol is None (no selection)
                # selected_idol is a single string (skin_id), not a list
                if selected_idol is None:
                    has_kotone = False
                else:
                    has_kotone = "藤田ことね" in selected_idol
                is_strict_mode = recommend_card_detection_mode == RecommendCardDetectionMode.STRICT.value
                return gr.Markdown(visible=has_kotone and not is_strict_mode)

            def on_solution_change(solution_id):
                """当选择的培育方案改变时，更新所有设置组件"""
                if not solution_id:
                    return [
                        gr.Textbox(value="", visible=False),  # solution_name
                        gr.Textbox(value="", visible=False),  # solution_description
                        gr.Dropdown(visible=False),  # produce_mode
                        gr.Dropdown(visible=False),  # produce_idols
                        gr.Markdown(visible=False),  # kotone_warning
                        gr.Checkbox(visible=False),  # auto_set_memory
                        gr.Group(visible=False),  # memory_sets_group
                        gr.Dropdown(visible=False),  # memory_sets
                        gr.Checkbox(visible=False),  # auto_set_support
                        gr.Group(visible=False),  # support_card_sets_group
                        gr.Dropdown(visible=False),  # support_card_sets
                        gr.Checkbox(visible=False),  # use_pt_boost
                        gr.Checkbox(visible=False),  # use_note_boost
                        gr.Checkbox(visible=False),  # follow_producer
                        gr.Dropdown(visible=False),  # self_study_lesson
                        gr.Checkbox(visible=False),  # prefer_lesson_ap
                        gr.Dropdown(visible=False),  # actions_order
                        gr.Dropdown(visible=False),  # recommend_card_detection_mode
                        gr.Checkbox(visible=False),  # use_ap_drink
                        gr.Checkbox(visible=False),  # skip_commu
                        gr.Button(visible=False),  # save_solution_btn
                    ]

                try:
                    solution = solution_manager.read(solution_id)
                    has_kotone = bool(solution.data.idol and "藤田ことね" in solution.data.idol)
                    is_strict_mode = solution.data.recommend_card_detection_mode == RecommendCardDetectionMode.STRICT

                    return [
                        gr.Textbox(value=solution.name, visible=True),
                        gr.Textbox(value=solution.description or "", visible=True),
                        gr.Dropdown(value=solution.data.mode, visible=True),
                        gr.Dropdown(value=solution.data.idol, visible=True),
                        gr.Markdown(visible=has_kotone and not is_strict_mode),
                        gr.Checkbox(value=solution.data.auto_set_memory, visible=True),
                        gr.Group(visible=not solution.data.auto_set_memory),
                        gr.Dropdown(value=str(solution.data.memory_set) if solution.data.memory_set else None, visible=True),
                        gr.Checkbox(value=solution.data.auto_set_support_card, visible=True),
                        gr.Group(visible=not solution.data.auto_set_support_card),
                        gr.Dropdown(value=str(solution.data.support_card_set) if solution.data.support_card_set else None, visible=True),
                        gr.Checkbox(value=solution.data.use_pt_boost, visible=True),
                        gr.Checkbox(value=solution.data.use_note_boost, visible=True),
                        gr.Checkbox(value=solution.data.follow_producer, visible=True),
                        gr.Dropdown(value=solution.data.self_study_lesson, visible=True),
                        gr.Checkbox(value=solution.data.prefer_lesson_ap, visible=True),
                        gr.Dropdown(value=[action.value for action in solution.data.actions_order], visible=True),
                        gr.Dropdown(value=solution.data.recommend_card_detection_mode.value, visible=True),
                        gr.Checkbox(value=solution.data.use_ap_drink, visible=True),
                        gr.Checkbox(value=solution.data.skip_commu, visible=True),
                        gr.Button(visible=True),  # save_solution_btn
                    ]
                except ProduceSolutionNotFoundError:
                    gr.Warning(f"培育方案 {solution_id} 不存在")
                    return on_solution_change(None)
                except Exception as e:
                    gr.Error(f"加载培育方案失败：{str(e)}")
                    return on_solution_change(None)

            def on_new_solution():
                """创建新的培育方案"""
                try:
                    new_solution = solution_manager.new("新培育方案")
                    solution_manager.save(new_solution.id, new_solution)

                    # 重新列出所有方案
                    solutions = solution_manager.list()
                    solution_choices = [(f"{sol.name} - {sol.description or '无描述'}", sol.id) for sol in solutions]

                    gr.Success("新培育方案创建成功")

                    # 更新培育 Tab 下拉框并保持设置 Tab 当前选中值
                    updated_dropdown_produce = gr.Dropdown(choices=solution_choices, value=new_solution.id)
                    if settings_dropdown is not None:
                        current_selected = self.current_config.options.produce.selected_solution_id
                        updated_dropdown_settings = gr.Dropdown(choices=solution_choices, value=current_selected)
                        return [updated_dropdown_produce, updated_dropdown_settings]
                    else:
                        return updated_dropdown_produce
                except Exception as e:
                    gr.Error(f"创建培育方案失败：{str(e)}")
                    if settings_dropdown is not None:
                        return [gr.Dropdown(), gr.Dropdown()]
                    else:
                        return gr.Dropdown()

            def on_delete_solution(solution_id):
                """删除当前培育方案"""
                if not solution_id:
                    gr.Warning("请先选择要删除的培育方案")
                    if settings_dropdown is not None:
                        return [gr.Dropdown(), gr.Dropdown()]
                    else:
                        return gr.Dropdown()

                # 若尝试删除当前正在使用的培育方案，则拒绝并提示
                if solution_id == self.current_config.options.produce.selected_solution_id:
                    gr.Warning("不可删除选中方案。请先在设置中选择其他方案，保存后再删除此方案。")
                    if settings_dropdown is not None:
                        return [gr.Dropdown(), gr.Dropdown()]
                    else:
                        return gr.Dropdown()

                try:
                    solution_manager.delete(solution_id)

                    # 重新列出所有方案
                    solutions = solution_manager.list()
                    solution_choices = [(f"{sol.name} - {sol.description or '无描述'}", sol.id) for sol in solutions]

                    gr.Success("培育方案删除成功")
                    # 删除方案后，保持当前培育方案的选择不变
                    current_selected = self.current_config.options.produce.selected_solution_id
                    if current_selected not in [sol.id for sol in solutions]:
                        current_selected = None  # 已不存在

                    updated_dropdown = gr.Dropdown(choices=solution_choices, value=current_selected)
                    if settings_dropdown is not None:
                        return [updated_dropdown, updated_dropdown]
                    else:
                        return updated_dropdown
                except Exception as e:
                    gr.Error(f"删除培育方案失败：{str(e)}")
                    if settings_dropdown is not None:
                        return [gr.Dropdown(), gr.Dropdown()]
                    else:
                        return gr.Dropdown()

            def on_save_solution(solution_id, name, description, mode, idols, auto_memory, memory_sets,
                               auto_support, support_card_sets, pt_boost, note_boost, follow_producer, study_lesson, prefer_ap,
                               actions, detection_mode, ap_drink, skip_commu_val):
                """保存培育方案"""
                if not solution_id:
                    gr.Warning("请先选择要保存的培育方案")
                    if settings_dropdown is not None:
                        return [gr.Dropdown(), gr.Dropdown()]
                    else:
                        return gr.Dropdown()

                try:
                    # 构建培育数据
                    produce_data = ProduceData(
                        mode=mode,
                        idol=idols if idols else None,
                        memory_set=int(memory_sets) if memory_sets else None,
                        support_card_set=int(support_card_sets) if support_card_sets else None,
                        auto_set_memory=auto_memory,
                        auto_set_support_card=auto_support,
                        use_pt_boost=pt_boost,
                        use_note_boost=note_boost,
                        follow_producer=follow_producer,
                        self_study_lesson=study_lesson,
                        prefer_lesson_ap=prefer_ap,
                        actions_order=[ProduceAction(action) for action in actions] if actions else [],
                        recommend_card_detection_mode=RecommendCardDetectionMode(detection_mode),
                        use_ap_drink=ap_drink,
                        skip_commu=skip_commu_val
                    )

                    # 构建方案对象
                    solution = ProduceSolution(
                        id=solution_id,
                        name=name or "未命名方案",
                        description=description,
                        data=produce_data
                    )

                    # 保存方案
                    solution_manager.save(solution_id, solution)

                    # 重新列出所有方案（确保没有重复项）
                    solutions = solution_manager.list()
                    solution_choices = [(f"{sol.name} - {sol.description or '无描述'}", sol.id) for sol in solutions]

                    gr.Success("培育方案保存成功")
                    # 根据是否有设置Tab的下拉框来决定返回值
                    updated_dropdown = gr.Dropdown(choices=solution_choices, value=solution_id)
                    if settings_dropdown is not None:
                        return [updated_dropdown, updated_dropdown]
                    else:
                        return updated_dropdown
                except Exception as e:
                    gr.Error(f"保存培育方案失败：{str(e)}")
                    if settings_dropdown is not None:
                        return [gr.Dropdown(), gr.Dropdown()]
                    else:
                        return gr.Dropdown()

            # 绑定事件
            # 为所有控件绑定change事件，无论是否有选中方案
            auto_set_memory.change(
                fn=lambda x: gr.Group(visible=not x),
                inputs=[auto_set_memory],
                outputs=[memory_sets_group]
            )

            auto_set_support.change(
                fn=lambda x: gr.Group(visible=not x),
                inputs=[auto_set_support],
                outputs=[support_card_sets_group]
            )

            if current_solution is not None:
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

            # 绑定方案管理事件
            solution_dropdown.change(
                fn=on_solution_change,
                inputs=[solution_dropdown],
                outputs=[
                    solution_name, solution_description,
                    produce_mode, produce_idols, kotone_warning,
                    auto_set_memory, memory_sets_group, memory_sets,
                    auto_set_support, support_card_sets_group, support_card_sets,
                    use_pt_boost, use_note_boost, follow_producer,
                    self_study_lesson, prefer_lesson_ap, actions_order,
                    recommend_card_detection_mode, use_ap_drink, skip_commu,
                    save_solution_btn
                ]
            )

            # 准备输出列表，如果设置Tab的下拉框存在，则同时更新
            outputs_for_new = [solution_dropdown]
            outputs_for_delete = [solution_dropdown]
            outputs_for_save = [solution_dropdown]

            if settings_dropdown is not None:
                outputs_for_new.append(settings_dropdown)
                outputs_for_delete.append(settings_dropdown)
                outputs_for_save.append(settings_dropdown)

            new_solution_btn.click(
                fn=on_new_solution,
                outputs=outputs_for_new
            )

            delete_solution_btn.click(
                fn=on_delete_solution,
                inputs=[solution_dropdown],
                outputs=outputs_for_delete
            )

            # 绑定保存按钮事件
            save_solution_btn.click(
                fn=on_save_solution,
                inputs=[
                    solution_dropdown, solution_name, solution_description,
                    produce_mode, produce_idols,
                    auto_set_memory, memory_sets, auto_set_support, support_card_sets,
                    use_pt_boost, use_note_boost, follow_producer,
                    self_study_lesson, prefer_lesson_ap, actions_order,
                    recommend_card_detection_mode, use_ap_drink, skip_commu
                ],
                outputs=outputs_for_save
            )

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
                dmm_bypass = gr.Checkbox(
                    label="绕过 DMM 启动器直接启动游戏（实验性）",
                    value=self.current_config.options.start_game.dmm_bypass,
                    info=StartGameConfig.model_fields['dmm_bypass'].description
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
            config.start_game.dmm_bypass = data['dmm_bypass']

        return set_config, {
            'start_game_enabled': start_game_enabled,
            'start_through_kuyo': start_through_kuyo,
            'game_package_name': game_package_name,
            'kuyo_package_name': kuyo_package_name,
            'disable_gakumas_localify': disable_gakumas_localify,
            'dmm_game_path': dmm_game_path,
            'dmm_bypass': dmm_bypass
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

    def _create_misc_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 杂项设置")
            check_update = gr.Dropdown(
                choices=[
                    ("启动时检查更新", "startup"),
                    ("从不检查更新", "never")
                ],
                value=self.current_config.options.misc.check_update,
                label="检查更新时机",
                info=MiscConfig.model_fields['check_update'].description,
                interactive=True
            )
            auto_install_update = gr.Checkbox(
                label="自动安装更新",
                value=self.current_config.options.misc.auto_install_update,
                info=MiscConfig.model_fields['auto_install_update'].description,
                interactive=True
            )
            expose_to_lan = gr.Checkbox(
                label="允许局域网访问",
                value=self.current_config.options.misc.expose_to_lan,
                info=MiscConfig.model_fields['expose_to_lan'].description,
                interactive=True
            )
            update_channel = gr.Dropdown(
                choices=[
                    ("正式版", "release"),
                    ("测试版", "beta")
                ],
                value=self.current_config.options.misc.update_channel,
                label="更新渠道",
                info=MiscConfig.model_fields['update_channel'].description,
                interactive=True
            )
            with gr.Row():
                gr.Button("创建桌面快捷方式").click(
                    fn=self._create_shortcut_button_click(False),
                    outputs=[]
                )
                gr.Button("创建一键启动快捷方式").click(
                    fn=self._create_shortcut_button_click(True),
                    outputs=[]
                )

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.misc.check_update = data['check_update']
            config.misc.auto_install_update = data['auto_install_update']
            config.misc.expose_to_lan = data['expose_to_lan']
            config.misc.update_channel = data['update_channel']
        
        return set_config, {
            'check_update': check_update,
            'auto_install_update': auto_install_update,
            'expose_to_lan': expose_to_lan,
            'update_channel': update_channel
        }

    def _create_shortcut_button_click(self, start_immediately: bool) -> Callable[[], None]:
        def _inner():
            create_desktop_shortcut(start_immediately)
            gr.Success("快捷方式创建成功")
        return _inner
    
    def _create_idle_settings(self) -> ConfigBuilderReturnValue:
        with gr.Column():
            gr.Markdown("### 闲置挂机")
            idle_enabled = gr.Checkbox(
                label="启用闲置挂机（任意键暂停、闲置自动恢复）",
                value=self.current_config.options.idle.enabled,
                info=IdleModeConfig.model_fields['enabled'].description,
                interactive=True
            )
            idle_seconds = gr.Slider(
                label="自动恢复触发时间（秒）",
                minimum=30,
                maximum=3600,
                step=10,
                value=self.current_config.options.idle.idle_seconds,
                info=IdleModeConfig.model_fields['idle_seconds'].description,
                interactive=True
            )
            idle_minimize_on_pause = gr.Checkbox(
                label="暂停时最小化游戏窗口",
                value=self.current_config.options.idle.minimize_on_pause,
                info=IdleModeConfig.model_fields['minimize_on_pause'].description,
                interactive=True
            )
        
        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            config.idle.enabled = data['idle_enabled']
            config.idle.idle_seconds = int(data['idle_seconds'])
            config.idle.minimize_on_pause = data['idle_minimize_on_pause']
        
        return set_config, {
            'idle_enabled': idle_enabled,
            'idle_seconds': idle_seconds,
            'idle_minimize_on_pause': idle_minimize_on_pause,
        }

    def _create_debug_settings(self) -> ConfigBuilderReturnValue:
        """调试设置：仅在调试时使用"""
        with gr.Column():
            gr.Markdown("### 调试设置")
            gr.Markdown('<div style="color: red;">仅供调试使用。正常运行时务必关闭下面所有的选项。</div>')

            keep_screenshots = gr.Checkbox(
                label="保留截图数据",
                value=self.current_config.keep_screenshots,
                info=UserConfig.model_fields['keep_screenshots'].description,
                interactive=True
            )

            trace_recommend_card_detection = gr.Checkbox(
                label="跟踪推荐卡检测",
                value=self.current_config.options.trace.recommend_card_detection,
                info=TraceConfig.model_fields['recommend_card_detection'].description,
                interactive=True
            )

        def set_config(config: BaseConfig, data: dict[ConfigKey, Any]) -> None:
            # 保留截图数据属于 UserConfig
            self.current_config.keep_screenshots = data['keep_screenshots']
            # 跟踪推荐卡检测属于 BaseConfig.trace
            config.trace.recommend_card_detection = data['trace_recommend_card_detection']

        return set_config, {
            'keep_screenshots': keep_screenshots,
            'trace_recommend_card_detection': trace_recommend_card_detection
        }

    def _create_settings_tab(self) -> None:
        with gr.Tab("设置"):
            gr.Markdown("## 设置 <span style='color: red; font-size: 0.8rem; font-weight: normal;'>设置修改后需要保存（网页底部）才会生效！</span>")

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

            # 扭蛋设置
            capsule_toys_settings = self._create_capsule_toys_settings()

            # 升级支援卡设置
            upgrade_support_card_settings = self._create_upgrade_support_card_settings()

            # 启动游戏设置
            start_game_settings = self._create_start_game_settings()

            # 关闭游戏设置
            end_game_settings = self._create_end_game_settings()

            # 杂项设置
            misc_settings = self._create_misc_settings()

            # 闲置挂机设置
            idle_settings = self._create_idle_settings()

            # 调试设置（放在最后）
            debug_settings = self._create_debug_settings()

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
                upgrade_support_card_settings,
                start_game_settings,
                end_game_settings,
                misc_settings,
                idle_settings,
                debug_settings
            ] # list of (set_func, { 'key': component, ... })
            all_components = [list(ret[1].values()) for ret in all_return_values] # [[c1, c2], [c3], ...]
            all_components = list(chain(*all_components)) # [c1, c2, c3, ...]
            save_btn.click(
                fn=partial(self.save_settings2, all_return_values),
                inputs=all_components,
                outputs=result
            )

    def _create_log_tab(self) -> None:
        with gr.Tab("反馈"):
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

            def on_upload_click(title: str, description: str):
                yield from _save_bug_report(title, description, self._kaa.version, upload=True)

            def on_save_local_click(title: str, description: str):
                yield from _save_bug_report(title, description, self._kaa.version, upload=False)

            upload_report_btn.click(
                fn=on_upload_click,
                inputs=[report_title, report_description],
                outputs=[result_text]
            )
            save_local_report_btn.click(
                fn=on_save_local_click,
                inputs=[report_title, report_description],
                outputs=[result_text]
            )

    def _create_whats_new_tab(self) -> None:
        """创建更新标签页"""
        with gr.Tab("更新"):
            gr.Markdown("## 版本管理")

            with gr.Accordion("更新日志", open=False):
                from kaa.metadata import WHATS_NEW
                gr.Markdown(WHATS_NEW)

            load_info_btn = gr.Button("载入信息", variant="primary")
            status_text = gr.Markdown("")
            version_dropdown = gr.Dropdown(
                label="选择要安装的版本",
                choices=[],
                value=None,
                visible=False,
                interactive=True
            )
            install_selected_btn = gr.Button("安装选定版本", visible=False)

            def on_load_info():
                """使用 UpdateService 加载版本信息。"""
                yield (
                    "正在载入版本信息...",
                    gr.Button(value="载入中...", interactive=False),
                    gr.Dropdown(visible=False),
                    gr.Button(visible=False)
                )
                try:
                    versions_data = self.update_service.list_remote_versions()
                except UpdateFetchListError as e:
                    gr.Error(str(e))
                    yield (
                        str(e),
                        gr.Button(value="载入信息", interactive=True),
                        gr.Dropdown(visible=False),
                        gr.Button(visible=False)
                    )
                    return

                status_info = [
                    f"**当前安装版本:** {versions_data.installed_version or '未知'}",
                    f"**最新版本:** {versions_data.latest or '未知'}",
                ]
                if versions_data.launcher_version:
                    if versions_data.launcher_version == "0.4.x":
                        status_info.append("**启动器版本:** < v0.5.0 (旧版本)")
                    else:
                        status_info.append(f"**启动器版本:** v{versions_data.launcher_version}")
                else:
                    status_info.append("**启动器版本:** 未知")
                
                status_info.append(f"**找到 {len(versions_data.versions)} 个可用版本**")
                status_message = "\n\n".join(status_info)

                yield (
                    status_message,
                    gr.Button(value="载入信息", interactive=True),
                    gr.Dropdown(choices=versions_data.versions, value=versions_data.versions[0] if versions_data.versions else None, visible=True),
                    gr.Button(visible=True)
                )

            def on_install_selected(selected_version: str):
                """使用 UpdateService 安装所选版本。"""
                if not selected_version:
                    gr.Warning("请先选择一个版本。")
                    return

                try:
                    self.update_service.install_version(selected_version)
                    gr.Info(f"正在启动器中安装版本 {selected_version}，程序将自动重启...")
                except UpdateServiceError as e:
                    gr.Error(str(e))

            load_info_btn.click(
                fn=on_load_info,
                outputs=[status_text, load_info_btn, version_dropdown, install_selected_btn]
            )

            install_selected_btn.click(
                fn=on_install_selected,
                inputs=[version_dropdown],
                outputs=[] 
            )

    def _create_screen_tab(self) -> None:
        with gr.Tab("画面"):
            gr.Markdown("## 当前设备画面")
            refresh_btn = gr.Button("刷新画面", variant="primary")
            WIDTH = 720 // 3
            HEIGHT = 1280 // 3
            last_update_text = gr.Markdown("上次更新时间：无数据")
            screenshot_display = gr.Image(type="numpy", width=WIDTH, height=HEIGHT)

            def update_screenshot():
                ctx = ContextStackVars.current()
                if ctx is None:
                    return [None, "上次更新时间：无上下文数据"]
                screenshot = ctx._screenshot
                if screenshot is None:
                    return [None, "上次更新时间：无截图数据"]
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
                return screenshot, f"上次更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            refresh_btn.click(
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
        custom_css = """
        #container { max-width: 800px; margin: auto; padding: 20px; }
        .quick-controls-row > div {
            display: flex !important;
            flex-wrap: nowrap !important;
            gap: 0 !important;
            overflow-x: auto !important;
        }
        .quick-controls-row > div > div {
            min-width: auto !important;
            padding: 0;
        }
        """
        with gr.Blocks(title="琴音小助手", css=custom_css) as app:
            with gr.Column(elem_id="container"):
                gr.Markdown(f"# 琴音小助手 v{self._kaa.version}")

                with gr.Tabs():
                    self._create_status_tab()
                    self._create_task_tab()
                    self._create_settings_tab()
                    self._create_produce_tab()
                    self._create_log_tab()
                    self._create_whats_new_tab()
                    self._create_screen_tab()

        # 启动 IdleModeManager 后台线程
        self.idle_mgr.start()

        return app

def main(kaa: Kaa | None = None, start_immidiately: bool = False) -> None:
    kaa = kaa or Kaa('./config.json')
    ui = KotoneBotUI(kaa)
    app = ui.create_ui()

    if start_immidiately:
        ui.start_run()

    server_name = "0.0.0.0" if ui.current_config.options.misc.expose_to_lan else "127.0.0.1"
    app.launch(inbrowser=True, show_error=True, server_name=server_name)

if __name__ == "__main__":
    main()
