import os
import json
import uuid
from typing import Any, Literal, TextIO

import cv2
from cv2.typing import MatLike

from kotonebot.util import cv2_imwrite

TraceId = Literal['rec-card']
TRACE_DIR = './traces/'
_trace_files: dict[TraceId, TextIO] = {}

if not os.path.exists(TRACE_DIR):
    os.makedirs(TRACE_DIR)

def trace(id: TraceId, image: MatLike, message: str | dict[str, Any]):
    file = None
    dir = os.path.join(TRACE_DIR, id)
    if id not in _trace_files:
        if not os.path.exists(dir):
            os.makedirs(dir)
        file = open(os.path.join(dir, id + '.log'), 'a+', encoding='utf-8')
        _trace_files[id] = file
    else:
        file = _trace_files[id]

    image_name = uuid.uuid4().hex
    cv2_imwrite(os.path.join(dir, image_name + '.png'), image)
    if isinstance(message, dict):
        message = json.dumps(message)
    message = f'{image_name}.png\n{message}\n'
    file.write(message)
    file.flush()
