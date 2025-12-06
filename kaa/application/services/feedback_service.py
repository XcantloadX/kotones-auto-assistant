import logging
import os
import re
import zipfile
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any

import cv2
from pydantic import BaseModel

from kaa.errors import ReportCreationError, UploadError

logger = logging.getLogger(__name__)


class BugReportResult(BaseModel):
    """错误报告创建结果的模型"""
    file_path: str
    upload_url: Optional[str] = None
    message: str


def _sanitize_filename(s: str) -> str:
    """过滤掉文件名中的非法字符"""
    return re.sub(r'[\\/:*?"<>|]', '_', s)


class FeedbackService:
    """处理反馈和错误报告的逻辑"""

    def report(self, title: str, description: str, version: str, upload: bool, on_progress: Optional[Callable[[Dict[str, Any]], None]] = None) -> BugReportResult:
        """
        创建并可能上传一个错误报告。

        :param title: 报告标题。
        :param description: 报告描述。
        :param version: 当前版本。
        :param upload: 是否上传报告。
        :param on_progress: 进度回调函数，用于实时回报进度。
        :return: 一个 BugReportResult 对象。
        :raises ReportCreationError: 如果报告创建失败。
        :raises UploadError: 如果报告上传失败。
        """
        from kotonebot import device
        from kotonebot.backend.context import ContextStackVars
        
        total_steps = 6 if upload else 5
        def _progress(data: Dict[str, Any]):
            if on_progress:
                on_progress(data)

        os.makedirs('logs', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        safe_title = _sanitize_filename(title)[:30] or "无标题"
        timestamp = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
        path = f'./reports/bug_{timestamp}_{safe_title}.zip'
        
        try:
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                _progress({'type': 'packing', 'item': '描述文件', 'step': 1, 'total_steps': total_steps})
                description_content = f"标题：{title}\n类型：bug\n内容：\n{description}"
                zipf.writestr('description.txt', description_content.encode('utf-8'))

                _progress({'type': 'packing', 'item': '上次截图', 'step': 2, 'total_steps': total_steps})
                try:
                    stack = ContextStackVars.current()
                    if stack and stack._screenshot is not None:
                        img = cv2.imencode('.png', stack._screenshot)[1].tobytes()
                        zipf.writestr('last_screenshot.png', img)
                except Exception as e:
                    logger.warning(f"保存上次截图失败: {e}")

                _progress({'type': 'packing', 'item': '当前截图', 'step': 3, 'total_steps': total_steps})
                try:
                    screenshot = device.screenshot()
                    img = cv2.imencode('.png', screenshot)[1].tobytes()
                    zipf.writestr('current_screenshot.png', img)
                except Exception as e:
                    logger.warning(f"保存当前截图失败: {e}")

                _progress({'type': 'packing', 'item': '配置文件', 'step': 4, 'total_steps': total_steps})
                if os.path.exists('config.json'):
                    zipf.write('config.json')

                _progress({'type': 'packing', 'item': '日志', 'step': 5, 'total_steps': total_steps})
                if os.path.exists('logs'):
                    for root, _, files in os.walk('logs'):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join('logs', os.path.relpath(file_path, 'logs'))
                            zipf.write(file_path, arcname)
                
                zipf.writestr('version.txt', version)
        except Exception as e:
            raise ReportCreationError(str(e)) from e

        file_path = os.path.abspath(path)

        if not upload:
            message = f"报告已保存至 {file_path}"
            _progress({'type': 'done', 'file_path': file_path, 'step': 5, 'total_steps': total_steps})
            return BugReportResult(file_path=file_path, message=message)

        # 上传报告
        from kotonebot.ui.file_host.sensio import upload as upload_file
        _progress({'type': 'uploading', 'item': '报告', 'step': 6, 'total_steps': total_steps})
        try:
            url = upload_file(file_path)
        except Exception as e:
            raise UploadError(str(e)) from e

        expire_time = datetime.now() + timedelta(days=7)
        final_msg = (
            f"报告导出成功：{url}\n\n"
            f"此链接将于 {expire_time.strftime('%Y-%m-%d %H:%M:%S')}（7 天后）过期\n\n"
            '**复制以上文本并发送至 QQ 群、Github issue、B站私信等**'
        )
        _progress({'type': 'done', 'url': url, 'step': 6, 'total_steps': total_steps})
        return BugReportResult(file_path=file_path, upload_url=url, message=final_msg)

