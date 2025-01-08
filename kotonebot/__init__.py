from kotonebot.client.protocol import DeviceABC
from .backend.context import ContextOcr, ContextImage, ContextDebug, device, ocr, image, debug
from .backend.util import Rect, fuzz, regex, contains, grayscale

# device: DeviceProtocol
# ocr: ContextOcr
# image: ContextImage
# debug: ContextDebug

# def __getattr__(name: str):
#     try:
#         return getattr(_c, name)
#     except AttributeError:
#         return globals()[name]

