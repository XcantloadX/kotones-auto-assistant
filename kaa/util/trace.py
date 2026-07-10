import os
import json
import uuid
from typing import Any, Literal, TextIO

import cv2
from cv2.typing import MatLike

from kotonebot.util import cv2_imwrite

TraceId = Literal['rec-card', 'commu-event-buttons']
TRACE_DIR = './traces/'
_trace_files: dict[TraceId, TextIO] = {}

if not os.path.exists(TRACE_DIR):
    os.makedirs(TRACE_DIR)

def _get_trace_file(id: TraceId) -> tuple[str, TextIO]:
    dir = os.path.join(TRACE_DIR, id)
    if id not in _trace_files:
        if not os.path.exists(dir):
            os.makedirs(dir)
        file = open(os.path.join(dir, id + '.log'), 'a+', encoding='utf-8')
        _trace_files[id] = file
    return dir, _trace_files[id]

def trace(id: TraceId, image: MatLike, message: str | dict[str, Any]):
    dir, file = _get_trace_file(id)

    image_name = uuid.uuid4().hex
    cv2_imwrite(os.path.join(dir, image_name + '.png'), image)
    if isinstance(message, dict):
        message = json.dumps(message)
    message = f'{image_name}.png\n{message}\n'
    file.write(message)
    file.flush()

def trace_named(id: TraceId, images: dict[str, MatLike], message: str | dict[str, Any]):
    dir, file = _get_trace_file(id)

    image_names: list[str] = []
    for name, image in images.items():
        filename = name if name.endswith('.png') else name + '.png'
        cv2_imwrite(os.path.join(dir, filename), image)
        image_names.append(filename)
    if isinstance(message, dict):
        message = json.dumps(message)
    message = '\n'.join(image_names) + f'\n{message}\n'
    file.write(message)
    file.flush()
