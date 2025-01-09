from pathlib import Path
import re
import time
import uuid
import traceback
from datetime import datetime
from typing import Callable, NamedTuple

import cv2
import numpy as np
from cv2.typing import MatLike

class Result(NamedTuple):
    title: str
    image: MatLike
    text: str

class _Vars:
    def __init__(self):
        self.__enabled: bool = False

        self.__max_results: int = 200
    
    @property
    def enabled(self) -> bool:
        """是否启用调试结果显示。"""
        return self.__enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self.__enabled = value

    @property
    def max_results(self) -> int:
        """最多保存的结果数量。"""
        return self.__max_results
    
    @max_results.setter
    def max_results(self, value: int):
        self.__max_results = value

debug = _Vars()

# TODO: 需要考虑释放内存的问题。释放哪些比较合适？
_results: dict[str, Result] = {}
_images: dict[str, MatLike] = {}
"""存放临时图片的字典。"""

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
        image: MatLike,
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
    key = 'result_' + title + '_' + str(time.time())
    _results[key] = Result(title, image, text)
    if len(_results) > debug.max_results:
        _results.pop(next(iter(_results)))
    # 拼接消息
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]
    callstack = [frame.replace(str(Path.cwd()), '.') for frame in traceback.format_stack() 
                if not re.search(r'Python\d*[\/\\]lib|debugpy', frame)]
    final_text = (
        f"Time: {now_time}\n" +
        f"\n{text}\n" +
        f"<details><summary>Callstack</summary>{''.join(callstack)}</details>"
    )
    # 发送 WS 消息
    from .server import send_ws_message
    send_ws_message(title, key, final_text)

