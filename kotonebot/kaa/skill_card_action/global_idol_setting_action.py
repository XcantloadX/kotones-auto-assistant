import json
import os
from logging import getLogger

from kotonebot import Interval, Countdown, ocr, contains, device, action
from kotonebot.backend.core import HintBox
from kotonebot.kaa.skill_card.card_deck_config import DeckConfig
from kotonebot.kaa.skill_card.enum_constant import Archetype, archetype_dict, get_archetype
from kotonebot.kaa.skill_card.global_idol_setting import GlobalIdolSetting

logger = getLogger(__name__)


# TODO: 获取默认配置
def get_default_config() -> DeckConfig:
    path = os.path.join(os.path.dirname(__file__), 'default_card_deck_config.json')
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, 'r', encoding='utf-8') as f:
        root = json.load(f)
    return DeckConfig.model_validate(root)


# TODO: 这里应该在游戏开始就初始化，在新培育、继续培育时调用new_play()待更新，在读取偶像信息后调用update_deck()完成更新
idol_setting = GlobalIdolSetting()
# TODO: 这里应该从配置文件中读取
deck_config = get_default_config()

# P手帳
PGuide = HintBox(x1=595, y1=610, x2=690, y2=735, source_resolution=(720, 1280))
# 編成
Builder = HintBox(x1=530, y1=1080, x2=610, y2=1140, source_resolution=(720, 1280))
# 流派
IdolArchetype = HintBox(x1=515, y1=455, x2=655, y2=495, source_resolution=(720, 1280))
# P手帳退出
PGuideExit = HintBox(x1=320, y1=1155, x2=400, y2=1235, source_resolution=(720, 1280))


@action('根据日程更新偶像流派', screenshot_mode='manual-inherit')
def update_archetype_by_schedule():
    """
    根据日程更新偶像流派
    :return: 
    """
    if not idol_setting.need_update:
        return
    it = Interval()
    wait_cd = Countdown(sec=5).start()
    device.screenshot()

    while not ocr.find(contains("P手帳"), rect=PGuide):
        if wait_cd.expired():
            logger.warning("not found: P手帳, update deck failed")
            return
        it.wait()
        device.screenshot()
    device.click(PGuide)
    it.wait()
    device.screenshot()

    wait_cd.reset()
    while not ocr.find(contains("編成"), rect=Builder):
        if wait_cd.expired():
            break
        it.wait()
        device.screenshot()
    device.click(Builder)
    it.wait()

    wait_cd.reset()
    while not wait_cd.expired():
        it.wait()
        img = device.screenshot()
        if text := ocr.raw().ocr(img, rect=IdolArchetype):
            archetype = get_archetype(text.squash().text)
            if archetype != Archetype.unidentified:
                idol_setting.update_deck(archetype, deck_config)
                break
    if idol_setting.need_update:
        logger.warning("Not found archetype, update deck failed")

    # 如果在手册页面，尝试退出
    it.wait()
    wait_cd.reset()
    device.screenshot()
    while ocr.find(contains("編成"), rect=Builder) and not wait_cd.expired():
        device.click(PGuideExit)
        it.wait()
        device.screenshot()
