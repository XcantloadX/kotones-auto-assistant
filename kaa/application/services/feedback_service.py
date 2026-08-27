import logging
import os
import traceback
import zipfile
from typing import Optional, Callable, TYPE_CHECKING

import cv2
from pydantic import BaseModel

from kaa.errors import ReportCreationError

if TYPE_CHECKING:
    from kaa.main.kaa import Kaa

logger = logging.getLogger(__name__)


class BugReportResult(BaseModel):
    """错误报告创建结果的模型"""
    file_path: str
    message: str


class FeedbackService:
    """处理反馈和错误报告的逻辑"""

    def __init__(self, kaa_getter: Callable[[], Optional['Kaa']] | None = None) -> None:
        """
        :param kaa_getter: 返回当前 Kaa 实例的回调，用于跨线程获取真实 Device。
                           对齐 ichika 的 SchedulerService.device 持有模式，避免
                           依赖 kotonebot 的线程隔离 ContextVar。
        """
        self._kaa_getter = kaa_getter

    def capture_screenshot(self):
        """
        获取当前设备截图，优先复用调度器持有的活跃设备，失败则临时创建设备。
        """
        # 1. 优先复用活跃设备（任务运行中）
        if self._kaa_getter is not None:
            try:
                kaa = self._kaa_getter()
                if kaa is not None and getattr(kaa, '_ctx', None) is not None:
                    dev = getattr(kaa._ctx, 'device', None)
                    if dev is not None:
                        logger.info("Capturing screenshot via active scheduler device.")
                        return dev.screenshot()
            except Exception:
                logger.debug("Failed to capture via active device.", exc_info=True)

        # 2. 无活跃设备则临时创建（对齐 ichika 的临时设备分支）
        if self._kaa_getter is not None:
            try:
                kaa = self._kaa_getter()
                if kaa is not None:
                    config = getattr(kaa, '_config', None)
                    if config is not None:
                        logger.info("No active scheduler device. Creating a temporary device for screenshot capture.")
                        device = kaa.factory.create_device_for_config(config)
                        started = False
                        try:
                            device.start()
                            started = True
                            return device.screenshot()
                        finally:
                            if started:
                                try:
                                    device.stop()
                                except Exception:
                                    logger.exception("Failed to stop temporary screenshot device.")
            except Exception:
                logger.debug("Failed to capture via temporary device.", exc_info=True)

        raise RuntimeError("No screenshot available: no active device and temporary device creation failed.")

    def report(self, title: str, description: str, version: str, output_path: str) -> BugReportResult:
        """创建错误报告并保存到用户选择的本地路径。"""
        if not output_path:
            raise ReportCreationError("未选择报告保存路径")

        path = os.path.abspath(os.path.expanduser(output_path))
        if not path.lower().endswith('.zip'):
            path += '.zip'
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        try:
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                description_content = f"标题：{title}\n类型：bug\n内容：\n{description}"
                zipf.writestr('description.txt', description_content.encode('utf-8'))

                try:
                    # 优先尝试复用上次截图的内存数据（bot 线程内有效），失败则现拍
                    last_img = None
                    try:
                        from kotonebot.backend.context import ContextStackVars
                        stack = ContextStackVars.current()
                        if stack is not None:
                            # _screenshot 已废弃，实际读取 vars.screenshot_data
                            last_img = stack._screenshot  # type: ignore
                    except Exception:
                        logger.debug("Failed to read last screenshot data.", exc_info=True)
                    if last_img is not None:
                        img = cv2.imencode('.png', last_img)[1].tobytes()
                        zipf.writestr('last_screenshot.png', img)
                    else:
                        logger.debug("No last screenshot available, will capture fresh one for current.")

                    screenshot = self.capture_screenshot()
                    img = cv2.imencode('.png', screenshot)[1].tobytes()
                    zipf.writestr('current_screenshot.png', img)
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.warning(f"保存截图失败: {e}", exc_info=True)
                    # 保留错误信息而非静默丢弃，便于排查
                    try:
                        zipf.writestr('screenshot_error.txt', tb)
                    except Exception:
                        pass

                if os.path.exists('conf'):
                    for root, _, files in os.walk('conf'):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join('conf', os.path.relpath(file_path, 'conf'))
                            zipf.write(file_path, arcname)
                if os.path.exists('config.json'):
                    zipf.write('config.json')

                if os.path.exists('logs'):
                    for root, _, files in os.walk('logs'):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join('logs', os.path.relpath(file_path, 'logs'))
                            zipf.write(file_path, arcname)

                zipf.writestr('version.txt', version)
        except Exception as e:
            raise ReportCreationError(str(e)) from e

        return BugReportResult(
            file_path=path,
            message=f"报告已保存至 {path}",
        )
