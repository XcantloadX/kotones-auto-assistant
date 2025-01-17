import os
import re
import json
import time
import uuid
import psutil
import traceback
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import NamedTuple, TextIO, Literal

import cv2
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
    save_to_folder: str | None = None
    """
    是否将结果保存到指定文件夹。
    
    如果为 None，则不保存。
    """

debug = _Vars()

# TODO: 需要考虑释放内存的问题。释放哪些比较合适？
_results: dict[str, Result] = {}
_images: dict[str, MatLike] = {}
"""存放临时图片的字典。"""
_result_file: TextIO | None = None

def _save_image(image: MatLike) -> str:
    """缓存图片数据到 _images 字典中。返回 key。"""
    key = str(uuid.uuid4())
    _images[key] = image
    if debug.save_to_folder:
        if not os.path.exists(debug.save_to_folder):
            os.makedirs(debug.save_to_folder)
        file_name = f"{key}.png"
        cv2.imwrite(os.path.join(debug.save_to_folder, file_name), image)
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
    if debug.save_to_folder:
        if isinstance(image, str):
            image = cv2.imread(image)
        key = _save_image(image)
        return f'[img]{key}[/img]'
    else:
        if isinstance(image, str):
            return f'<img src="/api/read_file?path={image}" />'
        else:
            key = _save_image(image)
            return f'<img src="/api/read_memory?key={key}" />'

def color(color: str | tuple[int, int, int] | None) -> str:
    """
    用于在调试结果中嵌入颜色。
    """
    if color is None:
        return 'None'
    if isinstance(color, tuple):
        color = '#{:02X}{:02X}{:02X}'.format(color[0], color[1], color[2])
        return f'<kbd-color style="display:inline-block; white-space:initial;" color="{color}"></kbd-color>'
    else:
        return f'<kbd-color style="display:inline-block; white-space:initial;" color="{color}"></kbd-color>'

def to_html(text: str) -> str:
    """将文本转换为 HTML 代码。"""
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('\n', '<br>')
    text = text.replace(' ', '&nbsp;')
    return text

IDEType = Literal['vscode', 'cursor', 'windsurf']

def get_current_ide() -> IDEType | None:
    """获取当前IDE类型"""
    me = psutil.Process()
    while True:
        parent = me.parent()
        if parent is None:
            break
        name = parent.name()
        if name.lower() == 'code.exe':
            return 'vscode'
        elif name.lower() == 'cursor.exe':
            return 'cursor'
        elif name.lower() == 'windsurf.exe':
            return 'windsurf'
        me = parent
    return None

def _make_code_file_url(
    text: str,
    full_path: str,
    line: int = 0,
) -> str:
    """
    将代码文本转换为 VSCode 的文件 URL。
    """
    ide = get_current_ide()
    if ide == 'vscode':
        prefix = 'vscode'
    elif ide == 'cursor':
        prefix = 'cursor'
    elif ide == 'windsurf':
        prefix = 'windsurf'
    else:
        return text
    url = f"{prefix}://file/{full_path}:{line}:0"
    return f'<a href="{url}">{text}</a>'

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
    global _result_file
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
    callstack = []
    for frame in traceback.format_stack():
        if not re.search(r'Python\d*[\/\\]lib|debugpy', frame):
            # 提取文件路径和行号
            match = re.search(r'File "([^"]+)", line (\d+)', frame)
            if match:
                file_path = match.group(1)
                file_path = to_html(file_path)
                line_num = match.group(2)
                # 将绝对路径转换为相对路径
                rel_path = file_path.replace(str(Path.cwd()), '.')
                # 将文件路径和行号转换为链接
                frame = frame.replace(
                    f'File "{file_path}", line {line_num}',
                    f'File "{_make_code_file_url(rel_path, file_path, int(line_num))}", line {line_num}'
                )
            callstack.append(frame)
    callstack_str = '\n'.join(callstack)

    # 获取简化堆栈(只包含函数名)
    simple_callstack = []
    for frame in traceback.extract_stack():
        if not re.search(r'Python\d*[\/\\]lib|debugpy', frame.filename):
            module = Path(frame.filename).stem # 只获取文件名,不含路径和扩展名
            simple_callstack.append(f"{module}.{frame.name}")
    simple_callstack_str = ' -> '.join(simple_callstack)
    simple_callstack_str = to_html(simple_callstack_str)

    final_text = (
        f"Time: {now_time}<br>" +
        f"Callstack: {simple_callstack_str}<br>" +
        f"<details><summary>Full Callstack</summary>{callstack_str}</details><br>" +
        f"<hr>{text}"
    )
    # 发送 WS 消息
    from .server import send_ws_message
    send_ws_message(title, saved_images, final_text, wait=debug.wait_for_message_sent)

    # 保存到文件
    # TODO: 把这个类型转换为 dataclass/namedtuple
    if debug.save_to_folder:
        if _result_file is None:
            if not os.path.exists(debug.save_to_folder):
                os.makedirs(debug.save_to_folder)
            log_file_name = f"dump_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
            _result_file = open(os.path.join(debug.save_to_folder, log_file_name), "w")
        _result_file.write(json.dumps({
            "image": {
                "type": "memory",
                "value": saved_images
            },
            "name": title,
            "details": final_text
        }))
        _result_file.write("\n")

