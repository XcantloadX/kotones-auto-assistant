import os
import json
import shutil
from importlib import resources
from typing import Literal, TypeVar, Any, Sequence
from typing_extensions import assert_never
from enum import IntEnum, Enum

from pydantic import BaseModel, ConfigDict

# TODO: from kotonebot import config (context) 会和 kotonebot.config 冲突
from kotonebot import logging
from kaa.config.schema import BaseConfig

logger = logging.getLogger(__name__)

def sprite_path(path: str) -> str:
    standalone = os.path.join('kotonebot/kaa/sprites', path)
    if os.path.exists(standalone):
        return standalone
    return str(resources.files('kaa.sprites') / path)