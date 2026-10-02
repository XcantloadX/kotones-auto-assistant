"""培育结束流程。"""
import logging

from kaa.game_ui import WhiteFilter, dialog
from kaa.kaa_context import produce_solution
from kaa.tasks import R
from kaa.tasks.actions.commu import handle_unread_commu
from kaa.tasks.actions.scenes import at_home
from kaa.tasks.common import skip
from kotonebot import device, image, ocr, sleep, wait
from kotonebot.backend.loop import Loop
from kotonebot import action
from kotonebot import contains

logger = logging.getLogger(__name__)


# TODO: 将这个函数改为手动截图模式
@action('考试结束流程')
def produce_end(has_live: bool = True):
    """
    执行考试结束流程

    :param has_live: 培育结束后是否存在live；当培育在期中考时失败的话，就没有live
    """
    # 1. 考试结束交流 [screenshots/produce/in_produce/final_exam_end_commu.png]
    # 2. 然后是，考试结束对话 [screenshots\\produce_end\\step2.jpg]
    # 3. MV
    # 4. 培育结束交流
    # 上面这些全部一直点就可以

    # 等待选择封面画面 [screenshots/produce_end/select_cover.jpg]
    # 次へ
    logger.info("Waiting for select cover screen...")
    if has_live:  # 只有在合格时，才会进行演出
        for _ in Loop():
            if not R.InProduce.ButtonNextNoIcon.exists():
                # device.screenshot()
                # 未读交流
                if handle_unread_commu():
                    logger.info("Skipping unread commu")
                # 跳过演出
                # [kotonebot-resource\\sprites\\jp\\produce\\screenshot_produce_end.png]
                elif image.find(R.Produce.ButtonSkipLive.template, preprocessors=[WhiteFilter()]):
                    logger.info("Skipping live.")
                    device.click()
                # [kotonebot-resource\\sprites\\jp\\produce\\screenshot_produce_end_skip.png]
                elif R.Produce.TextSkipLiveDialogTitle.exists():
                    logger.info("Confirming skip live.")
                    R.Common.IconButtonCheck.try_click()
                elif R.InProduce.ProduceScore.TitleText.exists():
                    score = ocr.ocr(rect=R.InProduce.ProduceScore.ScoreTextArea).squash().numbers()
                    if not score:
                        logger.info('Produce score: ocr error')
                    else:
                        logger.info('Produce score: %s', score)
                skip()
            else:
                break
        # 选择封面
        logger.info("Use default cover.")
        sleep(3)
        logger.debug("Click next")
        for _ in Loop(interval=0.5):
            if (btn_next := R.InProduce.ButtonNextNoIcon.find()) is not None:
                device.click(btn_next)
                break
        sleep(1)
        # 确认对话框 [screenshots/produce_end/select_cover_confirm.jpg]
        # 決定
        logger.debug("Click Confirm")
        for _ in Loop(interval=0.5):
            if (btn_confirm := R.Common.ButtonConfirm.q(threshold=0.8).find()) is not None:
                device.click(btn_confirm)
                break
        sleep(1)
        # 上传图片，等待“生成”按钮
        # 注意网络可能会很慢，可能出现上传失败对话框
        logger.info("Waiting for cover uploading...")

    retry_count = 0
    MAX_RETRY_COUNT = 5
    for _ in Loop(interval=2):
        # 处理上传失败
        if R.InProduce.ButtonRetry.find() is not None:
            logger.info("Upload failed. Retry...")
            retry_count += 1
            if retry_count >= MAX_RETRY_COUNT:
                logger.info("Upload failed. Max retry count reached.")
                logger.info("Cancel upload.")
                R.InProduce.ButtonCancel.try_click()
                continue
            device.click()
        # 记忆封面保存失败提示
        elif R.Common.ButtonClose.find() is not None:
            logger.info("Memory cover save failed. Click to close.")
            device.click()
        elif gen_btn := ocr.find(contains("生成")):
            logger.info("Generate memory cover completed.")
            device.click(gen_btn)
            break
        else:
            device.click_center()
            skip()  # 为了兼容has_live==False的情况
    # 后续动画
    logger.info("Waiting for memory generation animation completed...")
    for _ in Loop(interval=1):
        if not R.InProduce.ButtonNextNoIcon.exists():
            device.click_center()
        else:
            break

    # 四个完成画面
    logger.info("Finalize")
    for _ in Loop():
        # [screenshots/produce_end/end_next_1.jpg]
        # [screenshots/produce_end/end_next_2.png]
        # [screenshots/produce_end/end_next_3.png]
        if R.InProduce.ButtonNextNoIcon.exists():
            logger.debug("Click next")
            device.click()
            wait(0.5, before='screenshot')
        # [screenshots/produce_end/end_complete.png]
        elif btn_complete := R.InProduce.ButtonComplete.find():
            logger.debug("Click complete")
            btn_complete.click()
            wait(0.5, before='screenshot')
            break
        # 1. P任务解锁提示
        # 2. 培育得硬币活动时，弹出的硬币获得对话框
        elif dialog.no():
            pass

    # 点击结束后可能还会弹出来：
    # 活动进度、关注提示
    for _ in Loop(interval=1):
        if not at_home():
            # 活动积分进度 奖励领取
            # [screenshots/produce_end/end_activity1.png]
            # 制作人 升级
            # [screenshots/produce_end/end_level_up.png]
            if R.Common.ButtonIconClose.try_click():
                logger.info("Activity award claim dialog found. Clicked to close.")
            # 活动积分进度
            # [screenshots/produce_end/end_activity.png]
            elif R.Common.ButtonNextNoIcon.q(enabled=True).try_click():
                logger.debug("Clicked next")
            # 关注制作人
            # [screenshots/produce_end/end_follow.png]
            elif R.InProduce.ButtonCancel.exists():
                logger.info("Follow producer dialog found. Click to close.")
                if produce_solution().data.follow_producer:
                    logger.info("Follow producer")
                    R.InProduce.ButtonFollowNoIcon.try_click()
                else:
                    logger.info("Skip follow producer")
                    device.click()
            # 偶像强化月 新纪录达成
            # [kotonebot-resource/sprites/jp/in_purodyuusu/screenshot_new_record.png]
            elif R.Common.ButtonOK.exists():
                logger.info("OK button found. Click to close.")
                device.click()
            else:
                device.click_center()
        else:
            break
    logger.info("Produce completed.")
