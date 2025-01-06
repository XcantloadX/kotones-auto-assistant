from kotonebot.client.protocol import DeviceProtocol
from .backend.context import ContextOcr, ContextImage, ContextDebug, _c
from .backend.util import Rect, fuzz, regex, contains

device: DeviceProtocol
ocr: ContextOcr
image: ContextImage
debug: ContextDebug

def __getattr__(name: str):
    try:
        return getattr(_c, name)
    except AttributeError:
        return globals()[name]

