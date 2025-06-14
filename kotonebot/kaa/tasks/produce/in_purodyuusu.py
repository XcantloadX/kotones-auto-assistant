from functools import partial
import logging
from typing_extensions import assert_never
from typing import Literal

from kotonebot.kaa.game_ui.schedule import Schedule
from kotonebot.kaa.kaa_context import ProduceSession, produce, set_produce
from kotonebot.kaa.tasks import R
from ..actions import loading
from kotonebot.kaa.game_ui import WhiteFilter, dialog
from ..actions.scenes import at_home
from .cards import do_cards, CardDetectResult
from ..actions.commu import handle_unread_commu
from kotonebot.errors import UnrecoverableError
from kotonebot.util import Countdown, Interval, cropped
from kotonebot.backend.dispatch import DispatcherContext
from kotonebot.kaa.common import ProduceAction, RecommendCardDetectionMode, conf
from ..produce.common import until_acquisition_clear, commu_event, fast_acquisitions
from kotonebot import ocr, device, contains, image, regex, action, sleep, wait
from ..produce.non_lesson_actions import (
    enter_allowance, allowance_available,
    study_available, enter_study,
    is_rest_available, rest,
    outing_available, enter_outing,
    consult_available, enter_consult
)
from kotonebot.kaa.tasks.produce.nia_actions import (
    promotion_available, handle_promotion,
    care_package_available, handle_care_package,
    special_training_available, handle_special_training,
)

logger = logging.getLogger(__name__)
ActionType = None | Literal['lesson', 'rest']

def triple_click(x: int, y: int):
    """
    三连击，点击指定坐标。

    :param x: x 坐标
    :param y: y 坐标
    """
    device.click(x, y)
    sleep(0.3)
    device.click(x, y)
    sleep(0.3)
    device.click(x, y)

@action('执行 SP 课程')
def handle_sp_lesson():
    """
    执行 SP 课程

    前置条件：行动页面\n
    结束状态：练习场景，以及中间可能出现的加载、支援卡奖励、交流等
    """
    schedule = Schedule()
    if schedule.have_lesson():
        lesson = schedule.select_lesson()
        triple_click(lesson.rect.x1, lesson.rect.y1)
        return True
    else:
        return False

@action('执行推荐行动', screenshot_mode='manual-inherit')
def handle_recommended_action(final_week: bool = False) -> ProduceAction | None:
    """
    在行动选择页面，执行推荐行动

    前置条件：位于行动选择页面\n
    结束状态：
        * `lesson`：练习场景，以及中间可能出现的加载、支援卡奖励、交流等
        * `rest`：休息动画。

    :param final_week: 是否是考试前复习周
    :return: 是否成功执行推荐行动
    """
    # 获取课程
    logger.debug("Getting recommended lesson...")
    device.screenshot()
    if not image.find(R.InPurodyuusu.IconAsariSenseiAvatar):
        return None
    it = Interval()
    cd = Countdown(sec=5).start()
    result = None
    while not cd.expired():
        logger.debug('Retrieving recommended lesson...')
        with cropped(device, y1=0.00, y2=0.30):
            if result := image.find_multi([
                R.InPurodyuusu.TextSenseiTipDance,
                R.InPurodyuusu.TextSenseiTipVocal,
                R.InPurodyuusu.TextSenseiTipVisual,
                R.InPurodyuusu.TextSenseiTipRest,
                R.InPurodyuusu.TextSenseiTipConsult,
            ]):
                break
        it.wait()
        device.screenshot()

    logger.debug("image.find_multi: %s", result)
    if result is None:
        logger.debug("No recommended lesson found")
        return None
    recommended = None
    # 普通周
    if not final_week:
        if result.index == 0:
            template = R.InPurodyuusu.ButtonPracticeDance
            recommended = ProduceAction.DANCE
            logger.info("Recommend lesson is dance.")
        elif result.index == 1:
            template = R.InPurodyuusu.ButtonPracticeVocal
            recommended = ProduceAction.VOCAL
            logger.info("Recommend lesson is vocal.")
        elif result.index == 2:
            template = R.InPurodyuusu.ButtonPracticeVisual
            recommended = ProduceAction.VISUAL
            logger.info("Recommend lesson is visual.")
        elif result.index == 3:
            rest()
            return ProduceAction.REST
        elif result.index == 4:
            enter_consult()
            return ProduceAction.CONSULT
        else:
            return None
        # 点击课程
        logger.debug("Try clicking lesson...")
        x, y = image.expect_wait(template).rect.center
        triple_click(x, y)
        return recommended
    # 冲刺周
    else:
        if result.index == 0:
            template = R.InPurodyuusu.ButtonFinalPracticeDance
            recommended = ProduceAction.DANCE
        elif result.index == 1:
            template = R.InPurodyuusu.ButtonFinalPracticeVocal
            recommended = ProduceAction.VOCAL
        elif result.index == 2:
            template = R.InPurodyuusu.ButtonFinalPracticeVisual
            recommended = ProduceAction.VISUAL
        else:
            return None
        logger.debug("Try clicking lesson...")
        x, y = image.expect(template).rect.center
        triple_click(x, y)
        return recommended


@action('等待进入行动场景')
def until_action_scene(week_first: bool = False):
    """等待进入行动场景"""
    # 检测是否到行动页面
    templates = [
        R.InPurodyuusu.TextPDiary, # 普通周
        R.InPurodyuusu.ButtonFinalPracticeDance # 离考试剩余一周
    ]
    if produce().is_nia:
        templates.extend([
            # 一次
            R.InPurodyuusu.TextAuditionMusicOrder,
            R.InPurodyuusu.TextAuditionHarmonyToNight,
            R.InPurodyuusu.TextAuditionMeroBang,
            # 二次
            R.InPurodyuusu.TextAuditionGalaxyMusic,
            R.InPurodyuusu.TextAuditionPopFair,
            R.InPurodyuusu.TextAuditionMelodyJourney,
            # 最终
            R.InPurodyuusu.TextAuditionFinale,
            R.InPurodyuusu.TextAuditionQuartet,
            R.InPurodyuusu.TextAuditionIdolBigup,
            R.InPurodyuusu.TextAuditionSingleCut,
        ])
    while not image.find_multi(templates):
        logger.info("Action scene not detected. Retry...")
        # commu_event 和 acquisitions 顺序不能颠倒。
        # 在 PRO 培育初始饮料、技能卡二选一事件时，右下方的
        # 快进按钮会被视为交流。如果先执行 acquisitions()，
        # 会因为命中交流而 continue，commut_event() 永远
        # 不会执行。
        # [screenshots/produce/in_produce/initial_commu_event.png]
        if week_first and commu_event():
            continue
        if fast_acquisitions():
            continue
        sleep(0.2)
    else:
        logger.info("Now at action scene.")
        return 

@action('等待进入练习场景')
def until_practice_scene():
    """等待进入练习场景"""
    while image.find(R.InPurodyuusu.TextClearUntil) is None:
        until_acquisition_clear()

@action('等待进入考试场景')
def until_exam_scene():
    """等待进入考试场景"""
    # NOTE: is_exam_scene() 通过 OCR 剩余回合数判断是否处于考试场景。
    # 本来有可能会与练习场景混淆，
    # 但是在确定后续只是考试场景的情况下应该不会
    while ocr.find(regex("合格条件|三位以上")) is None and not is_exam_scene():
        until_acquisition_clear()

@action('执行练习', screenshot_mode='manual')
def practice():
    """
    执行练习
    
    前置条件：位于练习场景\n
    结束状态：各种奖励领取弹窗、加载画面等
    """
    logger.info("Practice started")

    def threshold_predicate(card_count: int, result: CardDetectResult):
        border_scores = (result.left_score, result.right_score, result.top_score, result.bottom_score)
        is_strict_mode = conf().produce.recommend_card_detection_mode == RecommendCardDetectionMode.STRICT
        if is_strict_mode:
            return (
                result.score >= 0.05
                and len(list(filter(lambda x: x >= 0.05, border_scores))) >= 3
            )
        else:
            return result.score >= 0.03
        # is_strict_mode 见下方 exam() 中解释
        # 严格模式下区别：
        # 提高平均阈值，且同时要求至少有 3 边达到阈值。

    def end_predicate():
        return not image.find_multi([
            R.InPurodyuusu.TextClearUntil,
            R.InPurodyuusu.TextPerfectUntil
        ])

    do_cards(threshold_predicate, end_predicate)
    logger.info("CLEAR/PERFECT not found. Practice finished.")

@action('执行考试')
def exam(type: Literal['mid', 'final']):
    """
    执行考试
    
    前置条件：考试进行中场景（手牌可见）\n
    结束状态：考试结束交流/对话（TODO：截图）
    """
    logger.info("Exam started")

    def threshold_predicate(card_count: int, result: CardDetectResult):
        is_strict_mode = conf().produce.recommend_card_detection_mode == RecommendCardDetectionMode.STRICT
        total = lambda t: result.score >= t
        def borders(t):
            # 卡片数量小于三时无遮挡，以及最后一张卡片也总是无遮挡
            if card_count <= 3 or (result.type == card_count - 1):
                return (
                    result.left_score >= t
                    and result.right_score >= t
                    and result.top_score >= t
                    and result.bottom_score >= t
                )
            # 其他情况下，卡片的右侧会被挡住，并不会发光
            else:
                return (
                    result.left_score >= t
                    and result.top_score >= t
                    and result.bottom_score >= t
                )

        if is_strict_mode:
            if type == 'final':
                return total(0.4) and borders(0.2)
            else:
                return total(0.10) and borders(0.01)
        else:
            if type == 'final':
                if result.type == 10: # SKIP
                    return total(0.4) and borders(0.02)
                else:
                    return total(0.2) and borders(0.02)
            else:
                return total(0.10) and borders(0.01)

        # 关于上面阈值的解释：
        # 所有阈值均指卡片周围的“黄色度”，
        # score 指卡片四边的平均黄色度阈值，
        # left_score、right_score、top_score、bottom_score 指卡片每边的黄色度阈值

        # 为什么期中和期末考试阈值不一样：
        # 期末考试的场景为黄昏，背景中含有大量黄色，
        # 非常容易对推荐卡的检测造成干扰。
        # 解决方法是提高平均阈值的同时，为每一边都设置阈值。
        # 这样可以筛选出只有四边都包含黄色的发光卡片，
        # 而由夕阳背景造成的假发光卡片通常不会四边都包含黄色。
        
        # 为什么需要严格模式：
        # 严格模式主要用于琴音。琴音的服饰上有大量黄色元素，
        # 很容易干扰检测，因此需要针对琴音专门调整阈值。
        # 主要变化是给每一边都设置了阈值。

    def end_predicate():
        return bool(
            not ocr.find(contains('残りターン'), rect=R.InPurodyuusu.BoxExamTop)
            and image.find(R.Common.ButtonNext)
        )

    do_cards(threshold_predicate, end_predicate)
    device.click(image.expect_wait(R.Common.ButtonNext))
    if type == 'final':
        while ocr.wait_for(contains("メモリー"), timeout=7):
            device.click_center()

# TODO: 将这个函数改为手动截图模式
@action('考试结束流程')
def produce_end():
    """执行考试结束流程"""
    # 1. 考试结束交流 [screenshots/produce/in_produce/final_exam_end_commu.png]
    # 2. 然后是，考试结束对话 [screenshots\produce_end\step2.jpg]
    # 3. MV
    # 4. 培育结束交流
    # 上面这些全部一直点就可以


    # 等待选择封面画面 [screenshots/produce_end/select_cover.jpg]
    # 次へ
    logger.info("Waiting for select cover screen...")
    it = Interval()
    while not image.find(R.InPurodyuusu.ButtonNextNoIcon):
        # device.screenshot()
        # 未读交流
        if handle_unread_commu():
            logger.info("Skipping unread commu")
        # 跳过演出
        # [kotonebot-resource\sprites\jp\produce\screenshot_produce_end.png]
        elif image.find(R.Produce.ButtonSkipLive, preprocessors=[WhiteFilter()]):
            logger.info("Skipping live.")
            device.click()
        # [kotonebot-resource\sprites\jp\produce\screenshot_produce_end_skip.png]
        elif image.find(R.Produce.TextSkipLiveDialogTitle):
            logger.info("Confirming skip live.")
            device.click(image.expect_wait(R.Common.IconButtonCheck))
        it.wait()
        device.click(0, 0)
    # 选择封面
    logger.info("Use default cover.")
    sleep(3)
    logger.debug("Click next")
    device.click(image.expect_wait(R.InPurodyuusu.ButtonNextNoIcon))
    sleep(1)
    # 确认对话框 [screenshots/produce_end/select_cover_confirm.jpg]
    # 決定
    logger.debug("Click Confirm")
    device.click(image.expect_wait(R.Common.ButtonConfirm, threshold=0.8))
    sleep(1)
    # 上传图片，等待“生成”按钮
    # 注意网络可能会很慢，可能出现上传失败对话框
    logger.info("Waiting for cover uploading...")
    retry_count = 0
    MAX_RETRY_COUNT = 5
    while True:
        img = device.screenshot()
        # 处理上传失败
        if image.raw().find(img, R.InPurodyuusu.ButtonRetry):
            logger.info("Upload failed. Retry...")
            retry_count += 1
            if retry_count >= MAX_RETRY_COUNT:
                logger.info("Upload failed. Max retry count reached.")
                logger.info("Cancel upload.")
                device.click(image.expect_wait(R.InPurodyuusu.ButtonCancel))
                sleep(2)
                continue
            device.click()
        # 记忆封面保存失败提示
        elif image.raw().find(img, R.Common.ButtonClose):
            logger.info("Memory cover save failed. Click to close.")
            device.click()
        elif gen_btn := ocr.raw().find(img, contains("生成")):
            logger.info("Generate memory cover completed.")
            device.click(gen_btn)
            break
        else:
            device.click_center()
        sleep(2)
    # 后续动画
    logger.info("Waiting for memory generation animation completed...")
    while not image.find(R.InPurodyuusu.ButtonNextNoIcon):
        device.click_center()
        sleep(1)
    
    # 结算完毕
    # logger.info("Finalize")
    # # [screenshots/produce_end/end_next_1.jpg]
    # logger.debug("Click next 1")
    # device.click(image.expect_wait(R.InPurodyuusu.ButtonNextNoIcon))
    # sleep(1.3)
    # # [screenshots/produce_end/end_next_2.png]
    # logger.debug("Click next 2")
    # device.click(image.expect_wait(R.InPurodyuusu.ButtonNextNoIcon))
    # sleep(1.3)
    # # [screenshots/produce_end/end_next_3.png]
    # logger.debug("Click next 3")
    # device.click(image.expect_wait(R.InPurodyuusu.ButtonNextNoIcon))
    # sleep(1.3)
    # # [screenshots/produce_end/end_complete.png]
    # logger.debug("Click complete")
    # device.click(image.expect_wait(R.InPurodyuusu.ButtonComplete))
    # sleep(1.3)

    # 四个完成画面
    logger.info("Finalize")
    while True:
        # [screenshots/produce_end/end_next_1.jpg]
        # [screenshots/produce_end/end_next_2.png]
        # [screenshots/produce_end/end_next_3.png]
        if image.find(R.InPurodyuusu.ButtonNextNoIcon):
            logger.debug("Click next")
            device.click()
            wait(0.5, before='screenshot')
        # [screenshots/produce_end/end_complete.png]
        elif image.find(R.InPurodyuusu.ButtonComplete):
            logger.debug("Click complete")
            device.click(image.expect_wait(R.InPurodyuusu.ButtonComplete))
            wait(0.5, before='screenshot')
            break
        # 1. P任务解锁提示
        # 2. 培育得硬币活动时，弹出的硬币获得对话框
        elif dialog.no():
            pass

    # 点击结束后可能还会弹出来：
    # 活动进度、关注提示
    while not at_home():
        # 活动积分进度 奖励领取
        # [screenshots/produce_end/end_activity1.png]
        # 制作人 升级
        # [screenshots/produce_end/end_level_up.png]
        if image.find(R.Common.ButtonIconClose):
            logger.info("Activity award claim dialog found. Click to close.")
            device.click()
        # 活动积分进度
        # [screenshots/produce_end/end_activity.png]
        elif image.find(R.Common.ButtonNextNoIcon, colored=True):
            logger.debug("Click next")
            device.click()
        # 关注制作人
        # [screenshots/produce_end/end_follow.png]
        elif image.find(R.InPurodyuusu.ButtonCancel):
            logger.info("Follow producer dialog found. Click to close.")
            if conf().produce.follow_producer:
                logger.info("Follow producer")
                device.click(image.expect_wait(R.InPurodyuusu.ButtonFollowNoIcon))
            else:
                logger.info("Skip follow producer")
                device.click()
        # 偶像强化月 新纪录达成
        # [kotonebot-resource/sprites/jp/in_purodyuusu/screenshot_new_record.png]
        elif image.find(R.Common.ButtonOK):
            logger.info("OK button found. Click to close.")
            device.click()
        else:
            device.click_center()
        sleep(1)
    logger.info("Produce completed.")

@action('执行行动', screenshot_mode='manual-inherit')
def handle_action(action: ProduceAction, final_week: bool = False) -> ProduceAction | None:
    """
    执行行动

    前置条件：位于行动选择页面\n
    结束状态：若返回 True，取决于执行的行动。若返回 False，则仍然位于行动选择页面。

    :param action: 行动类型
    :param final_week: 是否为冲刺周
    :return: 执行的行动
    """
    device.screenshot()
    match action:
        case ProduceAction.RECOMMENDED:
            return handle_recommended_action(final_week)
        case ProduceAction.DANCE:
            # TODO: 这两个模板的名称要统一一下
            templ = R.InPurodyuusu.TextActionVisual if not final_week else R.InPurodyuusu.ButtonFinalPracticeVisual
            if button := image.find(templ):
                triple_click(*button.rect.center)
                return ProduceAction.DANCE
            else:
                return None
        case ProduceAction.VOCAL:
            templ = R.InPurodyuusu.TextActionVocal if not final_week else R.InPurodyuusu.ButtonFinalPracticeVocal
            if button := image.find(templ):
                triple_click(*button.rect.center)
                return ProduceAction.VOCAL
            else:
                return None
        case ProduceAction.VISUAL:
            templ = R.InPurodyuusu.TextActionDance if not final_week else R.InPurodyuusu.ButtonFinalPracticeDance
            if button := image.find(templ):
                triple_click(*button.rect.center)
                return ProduceAction.VISUAL
            else:
                return None
        case ProduceAction.REST:
            if is_rest_available():
                rest()
                return ProduceAction.REST
            return None
        case ProduceAction.OUTING:
            if outing_available():
                enter_outing()
                return ProduceAction.OUTING
            return None
        case ProduceAction.STUDY:
            if study_available():
                enter_study()
                return ProduceAction.STUDY
            return None
        case ProduceAction.ALLOWANCE:
            if allowance_available():
                enter_allowance()
                return ProduceAction.ALLOWANCE
            return None
        case ProduceAction.CONSULT:
            if consult_available():
                enter_consult()
                return ProduceAction.CONSULT
            return None
        case ProduceAction.PROMOTION:
            if promotion_available():
                handle_promotion()
                return ProduceAction.PROMOTION
            return None
        case ProduceAction.CARE_PACKAGE:
            if care_package_available():
                handle_care_package()
                return ProduceAction.CARE_PACKAGE
            return None
        case ProduceAction.SPECIAL_TRAINING:
            if special_training_available():
                handle_special_training()
                return ProduceAction.SPECIAL_TRAINING
            return None
        case _:
            assert_never(action)

def week_normal(week_first: bool = False, week_number: int | None = None):
    until_action_scene(week_first)
    logger.info("Handling actions...")
    action: ProduceAction | None = None
    # 强制休息
    if (
        week_number is not None
        and week_number in conf().produce.nia_rest_weeks
    ):
        logger.info(f"Week {week_number} resting because of NIA rest weeks.")
        action = ProduceAction.REST
        handle_action(action)
    # SP 课程
    elif (
        conf().produce.prefer_lesson_ap
        and handle_sp_lesson()
    ):
        action = ProduceAction.DANCE
    else:
        actions = conf().produce.actions_order
        for action in actions:
            logger.debug("Checking action: %s", action)
            if action := handle_action(action):
                logger.info("Action %s hit.", action)
                break
    match action:
        case (
            ProduceAction.REST |
            ProduceAction.OUTING | ProduceAction.STUDY | ProduceAction.ALLOWANCE |
            ProduceAction.CONSULT | ProduceAction.PROMOTION | ProduceAction.CARE_PACKAGE |
            ProduceAction.SPECIAL_TRAINING
        ):
            # 什么都不需要做
            pass
        case ProduceAction.DANCE | ProduceAction.VOCAL | ProduceAction.VISUAL:
            # TODO: 应当分离到单独的文件或函数，而不是 hajime 与 nia 混合
            if produce().mode.startswith('nia'):
                logger.info('No need to do actual practice in NIA mode.')
                sleep(5) # 等待游戏从行动场景切走 
                until_action_scene()
            else:
                until_practice_scene()
                practice()
        case ProduceAction.RECOMMENDED:
            # RECOMMENDED 应当被 handle_recommended_action 转换为具体的行动
            raise ValueError("Recommended action should not be handled here.")
        case None:
            raise ValueError("Action is None.")
        case _:
            assert_never(action)
    until_action_scene()

def week_final_lesson():
    until_action_scene()
    action: ProduceAction | None = None
    actions = conf().produce.actions_order
    for action in actions:
        logger.debug("Checking action: %s", action)
        if action := handle_action(action, True):
            logger.info("Action %s hit.", action)
            break
    match action:
        case (
            ProduceAction.REST |
            ProduceAction.OUTING | ProduceAction.STUDY | ProduceAction.ALLOWANCE |
            ProduceAction.CONSULT
        ):
            # 什么都不需要做
            pass
        case ProduceAction.DANCE | ProduceAction.VOCAL | ProduceAction.VISUAL:
            until_practice_scene()
            practice()
        case ProduceAction.RECOMMENDED:
            # RECOMMENDED 应当被 handle_recommended_action 转换为具体的行动
            raise ValueError("Recommended action should not be handled here.")
        case None:
            raise ValueError("Action is None.")
        case ProduceAction.PROMOTION | ProduceAction.CARE_PACKAGE | ProduceAction.SPECIAL_TRAINING:
            raise ValueError("ProduceAction.PROMOTION or CARE_PACKAGE or SPECIAL_TRAINING should not appear in Hajime final lesson.")
        case _:
            assert_never(action)

def week_mid_exam():
    logger.info("Week mid exam started.")
    logger.info("Wait for exam scene...")
    until_exam_scene()
    logger.info("Exam scene detected.")
    sleep(5)
    device.click_center()
    sleep(5)
    exam('mid')
    until_action_scene()

def week_final_exam():
    logger.info("Week final exam started.")
    logger.info("Wait for exam scene...")
    until_exam_scene()
    logger.info("Exam scene detected.")
    sleep(5)
    device.click_center()
    sleep(0.5)
    loading.wait_loading_end()
    exam('final')
    produce_end()

NiaAuditionType = Literal['first', 'second', 'final']
@action('执行 NIA 试镜', screenshot_mode='auto')
def week_nia_audition(audition_type: NiaAuditionType, week_number: int | None = None):
    match audition_type:
        case 'first':
            logger.info("Week NIA first audition started.")
            target_templ = conf().produce.nia_first_audition_type.template
        case 'second':
            logger.info("Week NIA second audition started.")
            target_templ = conf().produce.nia_second_audition_type.template
        case 'final':
            logger.info("Week NIA final audition started.")
            target_templ = conf().produce.nia_final_audition_type.template
        case _:
            assert_never(audition_type)
    device.double_click(image.expect_wait(target_templ))
    until_exam_scene()
    exam('mid')
    if audition_type == 'final':
        produce_end()

@action('执行 Regular 培育', screenshot_mode='manual-inherit')
def hajime_regular(week: int = -1, start_from: int = 1):
    """
    「初」 Regular 模式

    :param week: 第几周，从1开始，-1表示全部
    :param start_from: 从第几周开始，从1开始。
    """
    weeks = [
        lambda: week_normal(True), # 1: Vo.レッスン、Da.レッスン、Vi.レッスン
        week_normal, # 2: 授業
        week_normal, # 3: Vo.レッスン、Da.レッスン、Vi.レッスン、授業
        week_normal, # 4: おでかけ、相談、活動支給
        week_final_lesson, # 5: 追い込みレッスン
        week_mid_exam, # 6: 中間試験
        week_normal, # 7: おでかけ、活動支給
        week_normal, # 8: 授業、活動支給
        week_normal, # 9: Vo.レッスン、Da.レッスン、Vi.レッスン
        week_normal, # 10: Vo.レッスン、Da.レッスン、Vi.レッスン、授業
        week_normal, # 11: おでかけ、相談、活動支給
        week_final_lesson, # 12: 追い込みレッスン
        week_final_exam, # 13: 最終試験
    ]
    if week == 0 or start_from == 0:
        until_action_scene(True)
    if week != -1:
        logger.info("Week %d started.", week)
        weeks[week - 1]()
    else:
        for i, w in enumerate(weeks[start_from-1:]):
            logger.info("Week %d started.", i + start_from)
            w()

@action('执行 PRO 培育', screenshot_mode='manual-inherit')
def hajime_pro(week: int = -1, start_from: int = 1):
    """
    「初」 PRO 模式

    :param week: 第几周，从1开始，-1表示全部
    :param start_from: 从第几周开始，从1开始。
    """
    weeks = [
        lambda: week_normal(True), # 1
        week_normal, # 2
        week_normal, # 3
        week_normal, # 4
        week_normal, # 5
        week_final_lesson, # 6
        week_mid_exam, # 7
        week_normal, # 8
        week_normal, # 9
        week_normal, # 10
        week_normal, # 11
        week_normal, # 12
        week_normal, # 13
        week_normal, # 14
        week_final_lesson, # 15
        week_final_exam, # 16
    ]
    if week != -1:
        logger.info("Week %d started.", week)
        weeks[week - 1]()
    else:
        for i, w in enumerate(weeks[start_from-1:]):
            logger.info("Week %d started.", i + start_from)
            w()

@action("执行 MASTER 培育", screenshot_mode='manual-inherit')
def hajime_master(week: int = -1, start_from: int = 1):
    """
    「初」 MASTER 模式
    
    :param week: 第几周，从1开始，-1表示全部
    :param start_from: 从第几周开始，从1开始。
    """
    weeks = [
        lambda: week_normal(True), # 1
        week_normal, # 2
        week_normal, # 3
        week_normal, # 4
        week_normal, # 5
        week_normal, # 6
        week_final_lesson, # 7
        week_mid_exam, # 8
        week_normal, # 9
        week_normal, # 10
        week_normal, # 11
        week_normal, # 12
        week_normal, # 13
        week_normal, # 14
        week_normal, # 15
        week_normal, # 16
        week_final_lesson, # 17
        week_final_exam, # 18
    ]
    if week != -1:
        logger.info("Week %d started.", week)
        weeks[week - 1]()
    else:
        for i, w in enumerate(weeks[start_from-1:]):
            logger.info("Week %d started.", i + start_from)
            w()

@action("执行 NIA PRO 培育", screenshot_mode='manual-inherit')
def nia_pro(week: int = -1, start_from: int = 1):
    """
    执行 NIA PRO 培育。

    :param week: 第几周，从1开始，-1表示全部
    :param start_from: 从第几周开始，从1开始。
    """
    weeks = [
        week_normal, # 1
        week_normal, # 2
        week_normal, # 3
        week_normal, # 4
        week_normal, # 5
        week_normal, # 6
        week_normal, # 7
        week_normal, # 8
        partial(week_nia_audition, 'first'), # 9
        week_normal, # 10
        week_normal, # 11
        week_normal, # 12
        week_normal, # 13
        week_normal, # 14
        week_normal, # 15
        week_normal, # 16
        week_normal, # 17
        partial(week_nia_audition, 'second'), # 18
        week_normal, # 19
        week_normal, # 20
        week_normal, # 21
        week_normal, # 22
        week_normal, # 23
        week_normal, # 24
        week_normal, # 25
        week_normal, # 26
        partial(week_nia_audition, 'final'), # 27
    ]
    if week != -1:
        logger.info("Week %d started.", week)
        weeks[week - 1]()
    else:
        for i, w in enumerate(weeks[start_from-1:]):
            logger.info("Week %d started.", i + start_from)
            w(week_number=i + start_from)

@action('是否在考试场景')
def is_exam_scene():
    """是否在考试场景"""
    return ocr.find(contains('残りターン'), rect=R.InPurodyuusu.BoxExamTop) is not None

ProduceStage = Literal[
    'action', # 行动场景
    'practice-ongoing', # 练习场景
    'exam-ongoing', # 考试进行中
    'exam-end', # 考试结束
    'unknown', # 未知场景
]

@action('检测当前培育场景', dispatcher=True)
def detect_produce_scene(ctx: DispatcherContext) -> ProduceStage:
    """
    判断当前是培育的什么阶段，并开始 Regular 培育。

    前置条件：培育中的任意场景\n
    结束状态：游戏主页面\n
    """
    logger.info("Detecting current produce stage...")
    
    # 行动场景
    texts = ocr.ocr()
    if (
        image.find_multi([
            R.InPurodyuusu.TextPDiary, # 普通周
            R.InPurodyuusu.ButtonFinalPracticeDance # 离考试剩余一周
        ]) 
    ):
        logger.info("Detection result: At action scene.")
        ctx.finish()
        return 'action'
    elif texts.where(regex('CLEARまで|PERFECTまで')):
        logger.info("Detection result: At practice ongoing.")
        ctx.finish()
        return 'practice-ongoing'
    elif is_exam_scene():
        logger.info("Detection result: At exam scene.")
        ctx.finish()
        return 'exam-ongoing'
    else:
        if fast_acquisitions():
            return 'unknown'
        if commu_event():
            return 'unknown'
        return 'unknown'

@action('开始 Hajime 培育')
def hajime_from_stage(stage: ProduceStage, type: Literal['regular', 'pro', 'master'], week: int):
    """
    开始 Regular 培育。
    """
    if stage == 'action':
        texts = ocr.ocr(rect=R.InPurodyuusu.BoxWeeksUntilExam)
        # 提取周数
        remaining_week = texts.squash().replace('ó', '6').numbers()
        if not remaining_week:
            raise UnrecoverableError("Failed to detect week. text=" + repr(texts.squash()))
        # 判断阶段
        match type:
            case 'regular':
                MID_WEEK = 6
                FINAL_WEEK = 13
                function = hajime_regular
            case 'pro':
                MID_WEEK = 7
                FINAL_WEEK = 16
                function = hajime_pro
            case 'master':
                MID_WEEK = 8
                FINAL_WEEK = 18
                function = hajime_master
            case _:
                assert_never(type)
        if texts.where(contains('中間')):
            week = MID_WEEK - remaining_week[0]
            function(start_from=week)
        elif texts.where(contains('最終')):
            week = FINAL_WEEK - remaining_week[0]
            function(start_from=week)
        else:
            raise UnrecoverableError("Failed to detect produce stage.")
    elif stage == 'exam-ongoing':
        # TODO: 应该直接调用 week_final_exam 而不是再写一次
        logger.info("Exam ongoing. Start exam.")
        match type:
            case 'regular':
                if week > 6: # 第六周为期中考试
                    exam('final')
                    return produce_end()
                else:
                    exam('mid')
                    return hajime_from_stage(detect_produce_scene(), type, week)
            case 'pro':
                if week > 7:
                    exam('final')
                    return produce_end()
                else:
                    exam('mid')
                    return hajime_from_stage(detect_produce_scene(), type, week)
            case 'master':
                if week > 8:
                    exam('final')
                    return produce_end()
                else:
                    exam('mid')
                    return hajime_from_stage(detect_produce_scene(), type, week)
            case _:
                assert_never(type)
    elif stage == 'practice-ongoing':
        # TODO: 应该直接调用 week_final_exam 而不是再写一次
        logger.info("Practice ongoing. Start practice.")
        practice()
        return hajime_from_stage(detect_produce_scene(), type, week)
    else:
        raise UnrecoverableError(f'Cannot resume produce from stage "{stage}".')

@action('继续 Regular 培育')
def resume_regular_produce(week: int):
    """
    继续 Regular 培育。
    
    :param week: 当前周数。
    """
    hajime_from_stage(detect_produce_scene(), 'regular', week)

@action('继续 PRO 培育')
def resume_pro_produce(week: int):
    """
    继续 PRO 培育。
    
    :param week: 当前周数。
    """
    hajime_from_stage(detect_produce_scene(), 'pro', week)

@action('继续 MASTER 培育')
def resume_master_produce(week: int):
    """
    继续 MASTER 培育。
    
    :param week: 当前周数。
    """
    hajime_from_stage(detect_produce_scene(), 'master', week)

if __name__ == '__main__':
    from logging import getLogger

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    getLogger('kotonebot').setLevel(logging.DEBUG)
    getLogger(__name__).setLevel(logging.DEBUG)
    import os
    from datetime import datetime
    os.makedirs('logs', exist_ok=True)
    log_filename = datetime.now().strftime('logs/task-%y-%m-%d-%H-%M-%S.log')
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'))
    logging.getLogger().addHandler(file_handler)

    from kotonebot.backend.debug import debug
    debug.auto_save_to_folder = 'dumps'
    debug.enabled = True
    
    set_produce(ProduceSession(mode='nia-pro'))
    nia_pro(start_from=2)