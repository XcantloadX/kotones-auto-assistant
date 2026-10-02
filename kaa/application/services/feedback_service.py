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

# 导出报告等待崩溃录屏编码完成的最长秒数（x265 medium 压 60s 视频正常在
# 1 分钟内完成；超时后报告不再等待，改附状态说明）。
_VIDEO_WAIT_TIMEOUT = 100


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

    def _attach_crash_video(self, zipf: zipfile.ZipFile) -> None:
        """将最近一次崩溃录屏放入报告顶层。

        - 已完成编码的视频 → ``crash_video.mp4``。
        - 编码进行中 / 导出时刻刚触发后台编码 → 等待完成（最多
          ``_VIDEO_WAIT_TIMEOUT`` 秒）后附上；超时或失败则附
          ``crash_video_status.txt``。
        - 无录屏器或环为空 → 不写任何条目。
        """
        kaa = self._kaa_getter() if self._kaa_getter is not None else None
        if kaa is None:
            return
        try:
            recorder = kaa._recorder
        except AttributeError:
            return
        if recorder is None:
            return
        path = recorder.last_video_path
        if path is None:
            # 导出时刻触发一次后台 dump（如友好错等未走系统错误分支的场景）。
            path = recorder.dump_for_crash()
            if path is None:
                return
        if not os.path.exists(path):
            recorder.wait_for_video(path, timeout=_VIDEO_WAIT_TIMEOUT)
        if os.path.exists(path):
            zipf.write(path, 'crash_video.mp4')
            return
        zipf.writestr(
            'crash_video_status.txt',
            f'崩溃录屏在导出等待超时后仍未完成：{path}\n请稍后在该路径查找并手动附上。',
        )

    def report(
        self,
        title: str,
        description: str,
        version: str,
        output_path: str,
        on_progress: Callable[[str], None] | None = None,
    ) -> BugReportResult:
        """创建错误报告并保存到用户选择的本地路径。

        :param on_progress: 步骤进度回调（导出线程内调用），参数为当前步骤文案。
        """
        if not output_path:
            raise ReportCreationError("未选择报告保存路径")

        def _progress(message: str) -> None:
            if on_progress is not None:
                on_progress(message)

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
                    _progress('正在收集截图…')
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

                _progress('正在打包配置与日志…')
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

                try:
                    _progress('正在导出游戏画面录屏…')
                    self._attach_crash_video(zipf)
                except Exception:
                    logger.warning('导出录屏失败', exc_info=True)

                zipf.writestr('version.txt', version)
        except Exception as e:
            raise ReportCreationError(str(e)) from e

        return BugReportResult(
            file_path=path,
            message=f"报告已保存至 {path}",
        )
