from logging import getLogger
from dataclasses import dataclass

from kotonebot.kaa.db.skill_card import SkillCard
from kotonebot.kaa.tasks import R
from kotonebot import Interval, device, Countdown, ocr, action, image
from kotonebot.backend.core import HintBox
from kotonebot.kaa.skill_card.enum_constant import CardName, get_card_name
from kotonebot.kaa.skill_card.card_data import CardTemplate, card_template_dict
from kotonebot.kaa.skill_card_action.global_idol_setting_action import idol_setting
from kotonebot.primitives import Rect

# 技能卡选择页面，点击技能卡后，技能卡的名字的范围
SelectCardNameArea = HintBox(x1=70, y1=478, x2=570, y2=538, source_resolution=(720, 1280))
# 商店页面，选择商品后，商品名的范围
ShopItemNameArea = HintBox(x1=195, y1=170, x2=625, y2=215, source_resolution=(720, 1280))
# 强化或删除技能卡时，技能卡的名字的范围
EnhancementCardNameArea = HintBox(x1=180, y1=100, x2=630, y2=145, source_resolution=(720, 1280))

logger = getLogger(__name__)


@dataclass
class ActualCard:
    rect: Rect
    name: str
    skill_card: CardTemplate
    priority: int

    @staticmethod
    def create_by(rect: Rect, card: SkillCard | None) -> 'ActualCard':
        """
        :param rect: 技能卡的位置
        :param title: 读取到的技能卡的名字
        :return: cls
        """
        if card:
            name = card.name.replace(' ', '').replace('+', '')
            card_name = get_card_name(name)
        else:
            card_name = CardName.unidentified

        if card_name == CardName.unidentified:
            logger.warning(f'Unrecognized skill card：{name}, rect={rect}')
        else:
            logger.info(f'Recognized skill card：{card_name.value}')

        skill_card = card_template_dict[card_name]
        priority = idol_setting.get_card_priority(card_name)
        return ActualCard(rect, name, skill_card, priority)


# class CardReader:
#     """
#     此类用于识别技能卡。
#     """

#     def __init__(self, rect: HintBox = SelectCardNameArea):
#         """
#         :param rect: 识别文本范围
#         """
#         self.rect = rect
#         self.it = Interval()
#         self.wait_cd = Countdown(sec=5)
        
#     def click_and_read_cards(self, card_rects: list[Rect]) -> list[ActualCard]:
#         """
#         对输入的card_rects进行点击，再对点击后的图像的指定位置self.rect 读取文本，实例化为ActualCard。
        
#         :param card_rects: 技能卡点击位置
#         :return: ActualCard list
#         """
#         result = []
#         for rect in card_rects:
#             actual_card = self.read_card(rect)
#             logger.info(actual_card)
#             result.append(actual_card)
#         return result

#     @action('读取技能卡', screenshot_mode='manual-inherit')
#     def read_card(self, card_rect: Rect) -> ActualCard:
#         title = []
#         self.it.reset()
#         self.wait_cd.reset()
#         while len(title) == 0 and not self.wait_cd.expired():
#             device.click(card_rect)
#             self.it.wait()
#             img = device.screenshot()
#             title = ocr.raw().ocr(img, rect=self.rect)
#         return ActualCard.create_by(card_rect, title.squash().text)
