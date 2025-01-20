from time import sleep
import logging

from kotonebot import device, image, ocr, task, action
from . import R
from .actions.scenes import loading, at_home, goto_home
from .actions.loading import wait_loading_end
from .actions.in_purodyuusu import hajime_regular

logger = logging.getLogger(__name__)

@task('培育')
def produce():
    """进行培育流程"""
    if not at_home():
        goto_home()
    # [screenshots/produce/home.png]
    device.click(image.expect_wait(R.Produce.ButtonProduce))
    sleep(0.3)
    wait_loading_end()
    # [screenshots/produce/regular_or_pro.png]
    device.click(image.expect_wait(R.Produce.ButtonRegular))
    sleep(0.3)
    wait_loading_end()
    # 选择 PIdol [screenshots/produce/select_p_idol.png]
    device.click(image.expect_wait(R.Common.ButtonNextNoIcon))
    sleep(0.1)
    # 选择支援卡 自动编成 [screenshots/produce/select_support_card.png]
    device.click(image.expect_wait(R.Produce.ButtonAutoSet))
    sleep(0.1)
    device.click(image.expect_wait(R.Common.ButtonConfirm, colored=True))
    sleep(1.3)
    device.click(image.expect_wait(R.Common.ButtonNextNoIcon))
    # 选择回忆 自动编成 [screenshots/produce/select_memory.png]
    device.click(image.expect_wait(R.Produce.ButtonAutoSet))
    sleep(1.3)
    device.click(image.expect_wait(R.Common.ButtonConfirm, colored=True))
    sleep(0.1)
    device.click(image.expect_wait(R.Common.ButtonNextNoIcon))
    sleep(0.6)
    # 不租赁回忆提示弹窗 [screenshots/produce/no_rent_memory_dialog.png]
    with device.pinned():
        if image.find(R.Produce.TextRentAvailable):
            device.click(image.expect(R.Common.ButtonNextNoIcon))
    sleep(0.3)
    # 选择道具 [screenshots/produce/select_end.png]
    # CONFIG:
    device.click(image.expect_wait(R.Produce.CheckboxIconNoteBoost))
    sleep(0.1)
    device.click(image.expect_wait(R.Produce.CheckboxIconSupportPtBoost))
    sleep(0.1)
    device.click(image.expect_wait(R.Produce.ButtonProduceStart))
    sleep(0.5)
    while not loading():
        # 跳过交流设置 [screenshots/produce/skip_commu.png]
        with device.pinned():
            if image.find(R.Produce.RadioTextSkipCommu):
                device.click()
                sleep(0.2)
            if image.find(R.Common.ButtonConfirmNoIcon):
                device.click()
    wait_loading_end()
    hajime_regular()


if __name__ == '__main__':
    from kotonebot.backend.context import init_context
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logging.getLogger('kotonebot').setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    init_context()
    produce()


