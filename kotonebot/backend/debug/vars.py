from pathlib import Path
import re
import time
import uuid
import traceback
from datetime import datetime
from dataclasses import dataclass
from typing import NamedTuple

from cv2.typing import MatLike

class Result(NamedTuple):
    title: str
    image: list[str]
    description: str

@dataclass
class _Vars:
    """调试变量类"""
    enabled: bool = False
    """是否启用调试结果显示。"""
    max_results: int = -1
    """最多保存的结果数量。-1 表示不限制。"""
    wait_for_message_sent: bool = False
    """
    是否等待消息发送完成才继续后续代码。

    启用此选项可能会降低运行速度。
    """
    hide_server_log: bool = True
    """是否隐藏服务器日志。"""

debug = _Vars()

# TODO: 需要考虑释放内存的问题。释放哪些比较合适？
_results: dict[str, Result] = {}
_images: dict[str, MatLike] = {}
"""存放临时图片的字典。"""

def _save_image(image: MatLike) -> str:
    """缓存图片数据到 _images 字典中。返回 key。"""
    key = str(uuid.uuid4())
    _images[key] = image
    return key

def _save_images(images: list[MatLike]) -> list[str]:
    """缓存图片数据到 _images 字典中。返回 key 列表。"""
    return [_save_image(image) for image in images]

def img(image: str | MatLike | None) -> str:
    """
    用于在 `result()` 函数中嵌入图片。

    :param image: 图片路径或 OpenCV 图片对象。
    :return: 图片的 HTML 代码。
    """
    if image is None:
        return 'None'
    elif isinstance(image, str):
        return f'<img src="/api/read_file?path={image}" />'
    else:
        key = str(uuid.uuid4())
        _images[key] = image
        return f'<img src="/api/read_memory?key={key}" />'

# TODO: 保存原图。原图用 PNG，结果用 JPG 压缩。
def result(
        title: str,
        image: MatLike | list[MatLike],
        text: str = ''
    ):
    """
    显示图片结果。

    例：
    ```python
    result(
        "image.find",
        image,
        f"template: {img(template)} \\n"
        f"matches: {len(matches)} \\n"
    )
    ```
    
    :param title: 标题。建议使用 `模块.方法` 格式。
    :param image: 图片。
    :param text: 详细文本。可以是 HTML 代码，空格和换行将会保留。如果需要嵌入图片，使用 `img()` 函数。
    """
    if not debug.enabled:
        return
    if not isinstance(image, list):
        image = [image]
    
    key = 'result_' + title + '_' + str(time.time())
    # 保存图片
    saved_images = _save_images(image)
    _results[key] = Result(title, saved_images, text)
    if len(_results) > debug.max_results:
        _results.pop(next(iter(_results)))
    # 拼接消息
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]
    # 获取完整堆栈
    callstack = [frame.replace(str(Path.cwd()), '.') for frame in traceback.format_stack() 
                if not re.search(r'Python\d*[\/\\]lib|debugpy', frame)]
    
    # 获取简化堆栈(只包含函数名)
    simple_callstack = []
    for frame in traceback.extract_stack():
        if not re.search(r'Python\d*[\/\\]lib|debugpy', frame.filename):
            module = Path(frame.filename).stem # 只获取文件名,不含路径和扩展名
            simple_callstack.append(f"{module}.{frame.name}")
    
    final_text = (
        f"Time: {now_time}\n" +
        f"Callstack: \n{' -> '.join(simple_callstack)}\n" +
        f"<details><summary>Full Callstack</summary>{''.join(callstack)}</details>" +
        f"<hr>{text}\n"
    )
    # 发送 WS 消息
    from .server import send_ws_message
    send_ws_message(title, saved_images, final_text, wait=debug.wait_for_message_sent)

