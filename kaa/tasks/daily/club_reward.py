"""领取社团奖励，并尽可能地给其他人送礼物"""
import logging

from kaa.tasks import R
from kaa.config import conf
from kaa.game_ui import toolbar_menu
from ..actions.scenes import at_home, goto_home
from kotonebot import task, device, image, sleep, ocr

logger = logging.getLogger(__name__)

@task('领取社团奖励并送礼物')
def club_reward():
    """
    领取社团奖励，并尽可能地给其他人送礼物
    """

    if not conf().club_reward.enabled:
        logger.info('"Club reward" is disabled.')
        return
    
    if not at_home():
        goto_home()
    
    # 进入社团UI
    logger.info('Entering club UI')
    device.click(toolbar_menu(True))
    sleep(0.5) # 避免过早点击
    device.click(image.expect_wait(R.Daily.IconMenuClub, timeout=5))
    sleep(3)

    # 如果笔记请求尚未结束，则不进行任何笔记请求有关操作（领取奖励 & 发起新的笔记请求）

    # 如果笔记请求已经结束，且存在奖励提示，学偶UI应该会直接弹出面板，那么直接点击关闭按钮即可；
    logger.info('Prepare to collect note request reward')
    if image.find(R.Common.ButtonClose):
        device.click()
        logger.info('Collected note request reward')
    sleep(1)

    # 如果笔记请求已经结束，则发起一轮新的笔记请求；
    # 注：下面这个图片要可以区分出笔记请求是否已经结束，不然会发生不幸的事情
    logger.info('Prepare to start new note request')

    texts = ocr.ocr(rect=R.Daily.Club.NoteRequestHintBox)
    logger.debug(f'OCR result: {texts}')
    # 不应该进入的情况，识别结果为：[OcrResult(text="リクエストロ", rect=(243, 298, 145, 35), confidence=0.8576575517654419)]
    # 应该进入的情况，识别结果为：[OcrResult(text="リクエスト", rect=(244, 297, 141, 35), confidence=0.9993334531784057)]
    if texts and texts[0].text == 'リクエスト':
        # 经测验，threshold=0.999时也可以正确识别，所以这里保留这个阈值
        device.click(image.expect_wait(R.Daily.ButtonClubCollectReward, threshold=0.99))
        sleep(0.5)
        # 找到配置中选择的书籍
        device.click(image.expect_wait(conf().club_reward.selected_note.to_resource(), timeout=5))
        sleep(0.5)
        # 确认键
        device.click(image.expect_wait(R.Common.ButtonConfirm, timeout=5))
        sleep(0.5)
        device.click(image.expect_wait(R.Common.ButtonConfirm, timeout=5))
        sleep(1)
        logger.info('Started new note request')
    else:
        logger.info('No need to start new note request')
    
    # 送礼物（好友硬币是重要的o(*￣▽￣*)o
    logger.info('Sending gifts')
    for _ in range(5): # 默认循环5次
        # 送礼物
        if image.find(R.Daily.ButtonClubSendGift):
            device.click()
            sleep(0.5)
        # 下个人
        if image.find(R.Daily.ButtonClubSendGiftNext):
            device.click()
            sleep(0.5)
        else:
            # 找不到下个人就break
            break

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    club_reward()

