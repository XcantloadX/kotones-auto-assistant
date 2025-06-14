import logging
from typing import Any
from typing_extensions import assert_never

from kotonebot import device, image, action, sleep
from kotonebot.backend.loop import Loop
from kotonebot.kaa.game_ui import dialog
from kotonebot.kaa.game_ui.common import WhiteFilter
from kotonebot.kaa.game_ui.commu_event_buttons import CommuEventButtonUI
from kotonebot.kaa.tasks import R
from kotonebot.kaa.common import conf, NiaPromotionType
from kotonebot.kaa.tasks.produce.common import fast_acquisitions


def triple_click(result: Any | None = None):
    if result is None:
        device.click()
        sleep(0.3)
        device.click()
        sleep(0.3)
        device.click()
    else:
        device.click(result)
        sleep(0.3)
        device.click(result)
        sleep(0.3)
        device.click(result)

logger = logging.getLogger(__name__)

@action('判断営業是否可用')
def promotion_available():
    return image.find(R.InPurodyuusu.ButtonPromotion) is not None

@action('判断「差し入れ」是否可用')
def care_package_available():
    return image.find(R.InPurodyuusu.ButtonCarePackage) is not None

@action('判断「特別指導」是否可用')
def special_training_available():
    return image.find(R.InPurodyuusu.ButtonSpecialTraining) is not None

@action('处理「営業」', screenshot_mode='manual-inherit')
def handle_promotion(should_enter: bool = True):
    """
    处理「営業」事件。
    
    
    """
    logger.info('Executing 営業.')

    at_promotion: bool | None = None
    for lp in Loop():
        if should_enter:
            if result := image.find(R.InPurodyuusu.ButtonPromotion):
                logger.info('Entering 営業.')
                triple_click(result)
                sleep(4)
        if not at_promotion:
            at_promotion = image.find(R.InPurodyuusu.IconTitlePromotion) is not None

        # 选择营业类型页面
        if at_promotion:
            if image.find(R.InPurodyuusu.ButtonStartPromotion):
                logger.info('Starting 営業.')
                device.click()
                sleep(4)
                continue
            continue_outer = False
            for t in conf().produce.nia_promotion_type_order:
                template = None
                match t:
                    case NiaPromotionType.HEAL:
                        template = R.InPurodyuusu.PromotionTypeIconHeal
                    case NiaPromotionType.POINT:
                        template = R.InPurodyuusu.PromotionTypeIconPoint
                    case NiaPromotionType.DRINK:
                        template = R.InPurodyuusu.PromotionTypeIconDrink
                    case NiaPromotionType.SKILL_CARD:
                        template = R.InPurodyuusu.PromotionTypeIconSkillCard
                    case _:
                        assert_never(t)
                if template and image.find(template):
                    logger.info('Selecting 営業 type: %s', t)
                    device.click()
                    sleep(1) # 等待动画结束
                    continue_outer = True
                    break
            if continue_outer:
                continue
            # Dance、Visual、Vocal 选择页面
            if image.find(R.Common.ButtonCommuFastforward, preprocessors=[WhiteFilter()]):
                ui = CommuEventButtonUI()
                buttons = ui.all()
                if len(buttons) == 3:
                    # 数量为 3，说明是选择技能卡类型的对话
                    for i, b in enumerate(buttons):
                        if conf().produce.nia_promotion_skill_card_option.search_text in b.description:
                            logger.info('Selecting 営業 skill card option: index=%d', i)
                            device.double_click(b)
                            lp.exit()
        
        # 兜底处理
        fast_acquisitions()

@action('处理「差し入れ」')
def handle_care_package(should_enter: bool = True):
    logger.info('Executing 差し入れ.')
    if should_enter:
        triple_click(image.expect_wait(R.InPurodyuusu.ButtonCarePackage))
    # 等到「差し入れ」页面
    for _ in Loop():
        if image.find(R.InPurodyuusu.IconTitleCarePackage):
            break
        else:
            fast_acquisitions()
    # 然后什么都不需要做
    return

@action('处理「特別指導」')
def handle_special_training(should_enter: bool = True):
    logger.info('Executing 特別指導.')
    while should_enter:
        if image.find(R.InPurodyuusu.ButtonSpecialTraining):
            triple_click()
            break
        else:
            fast_acquisitions()

    # 直接退出
    # TODO: R.InPurodyuusu.ButtonEndConsult 要改个名字
    for _ in Loop():
        if image.find(R.InPurodyuusu.ButtonEndConsult):
            device.click()
        elif dialog.yes():
            break

if __name__ == '__main__':
    handle_promotion()