import re
from typing import Any, NamedTuple
from functools import lru_cache
from typing_extensions import deprecated

import cv2
from cv2.typing import MatLike
from kotonebot.backend.image import find
from kotonebot.primitives import Rect
from kotonebot import logging, device, Loop, Countdown

from kaa.tasks import R
from .ui import locate_cards
from ..page import eval_once

logger = logging.getLogger(__name__)
HUD_HEIGHT = 226


@lru_cache(maxsize=1)
def _dddd():
    import ddddocr
    return ddddocr.DdddOcr(show_ad=False)


def _digits_from_image(img: MatLike) -> list[int]:
    if img is None or img.size == 0:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    ok, buf = cv2.imencode(".png", bw)
    if not ok:
        return []

    text = _dddd().classification(buf.tobytes())
    nums = re.findall(r"\d+", text or "")
    return [int(n) for n in nums]


def _fetch_int(box: Rect) -> int | None:
    screen = device.screenshot()
    crop = screen[box.y1:box.y2, box.x1:box.x2]
    nums = _digits_from_image(crop)
    return nums[0] if nums else None

class HudInfo(NamedTuple):
    remaining_turns: int | None
    hp: int | None
    genki: int | None

def _screenshot_hud() -> MatLike:
    screen = device.screenshot()
    h, w, _ = screen.shape
    hud = screen[h - HUD_HEIGHT : h, 0 : w]
    return hud

class LessonBattleContext:
    """课程打牌页面"""

    @eval_once
    def fetch_remaining_turns(self) -> int | None:
        """获取剩余回合数"""
        return _fetch_int(R.InPurodyuusu.InLesson.BoxRemainingTurns)
    
    @eval_once
    def fetch_hp(self) -> int | None:
        """获取当前体力"""
        return _fetch_int(R.InPurodyuusu.InLesson.BoxHp)
    
    @eval_once
    def fetch_genki(self) -> int | None:
        """获取当前元气值"""
        return _fetch_int(R.InPurodyuusu.InLesson.BoxGenki)
    
    @eval_once
    def fetch_all(self):
        remaining_turns = _fetch_int(R.InPurodyuusu.InLesson.BoxRemainingTurns)
        hp = _fetch_int(R.InPurodyuusu.InLesson.BoxHp)
        genki = _fetch_int(R.InPurodyuusu.InLesson.BoxGenki)
        return HudInfo(remaining_turns, hp, genki)
    
    @eval_once
    def fetch_hands(self):
        """获取手牌信息"""
        img = device.screenshot()
        cards = locate_cards(img)
        return cards

    @deprecated('考试与冲刺周冲刺阶段里，背景是动态的，因此效果不佳')
    def wait_stablized(self, *, timeout: float = float('inf'), interval: float = 0.5, stable_time: float = 3) -> bool:
        """
        等待 HUD 展示稳定。用于等待下一次出牌开始。

        :param timeout: 最长等待时间，单位秒
        :param interval: 每次检查间隔时间，单位秒
        :param stable_time: HUD 稳定持续时间，单位秒。只有当 HUD 在该时间内保持不变，才认为稳定。
        :return: 如果在超时时间内 HUD 稳定则返回 True，否则返回 False。
        """
        hud = _screenshot_hud()
        stable_cd = Countdown(stable_time)
        for _ in Loop(timeout=timeout, interval=interval):
            new_hud = _screenshot_hud()
            if find(hud, new_hud, threshold=0.9) is not None:
                stable_cd.start()
                if stable_cd.expired():
                    return True
            else:
                stable_cd.reset()
            hud = new_hud
            
        return False



if __name__ == "__main__":
    from pprint import pprint
    from time import time
    print("Fetching all HUD info...")
    while True:
        start = time()
        ctx = LessonBattleContext()
        # ctx.wait_stablized(stable_time=1)
        info = ctx.fetch_all()
        end = time()
        print(f"Fetched in {end - start:.2f} seconds:")
        pprint(info)
        pprint(ctx.fetch_hands())
    # print("Remaining Turns:", ctx.fetch_remaining_turns())
    # print("HP:", ctx.fetch_hp())
    # print("Genki:", ctx.fetch_genki())
    # print("Waiting for stabilized...")
    # if ctx.wait_stablized(timeout=30):
    #     print("Page stabilized.")
    # else:
    #     print("Timeout waiting for page to stabilize.")