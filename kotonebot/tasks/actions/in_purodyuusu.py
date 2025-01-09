import random
import re
import time
from typing import Literal
from typing_extensions import deprecated
import numpy as np
import cv2
import unicodedata
import logging
from time import sleep

from kotonebot import ocr, device, fuzz, contains, image, debug, regex
from kotonebot.backend.context import init_context
from kotonebot.backend.util import crop_y, cropper_y, grayscale, grayscale_cached
from kotonebot.tasks import R
from kotonebot.tasks.actions import loading
from kotonebot.tasks.actions.pdorinku import acquire_pdorinku

logger = logging.getLogger(__name__)

ActionType = None | Literal['lesson', 'rest']
def enter_recommended_action(final_week: bool = False) -> ActionType:
    """
    在行动选择页面，执行推荐行动

    :param final_week: 是否是考试前复习周
    :return: 是否成功执行推荐行动
    """
    # 获取课程
    logger.debug("Waiting for recommended lesson...")
    with device.hook(cropper_y(0.00, 0.30)):
        ret = ocr.wait_for(regex('ボーカル|ダンス|ビジュアル|休|体力'))
    logger.debug("ocr.wait_for: %s", ret)
    if ret is None:
        return None
    if not final_week:
        if "ボーカル" in ret.text:
            lesson_text = "Vo"
        elif "ダンス" in ret.text:
            lesson_text = "Da"
        elif "ビジュアル" in ret.text:
            lesson_text = "Vi"
        elif "休" in ret.text or "体力" in ret.text:
            rest()
            return 'rest'
        else:
            return None
        logger.info("Rec. lesson: %s", lesson_text)
        # 点击课程
        logger.debug("Try clicking lesson...")
        lesson_ret = ocr.expect(contains(lesson_text))
        device.double_click(lesson_ret.rect)
        return 'lesson'
    else:
        if "ボーカル" in ret.text:
            template = R.InPurodyuusu.ButtonFinalPracticeVocal
        elif "ダンス" in ret.text:
            template = R.InPurodyuusu.ButtonFinalPracticeDance
        elif "ビジュアル" in ret.text:
            template = R.InPurodyuusu.ButtonFinalPracticeVisual
        else:
            return None
        logger.debug("Try clicking lesson...")
        device.double_click(image.expect_wait(template))
        return 'lesson'

def before_start_action():
    """检测支援卡剧情、领取资源等"""
    raise NotImplementedError()

def click_recommended_card(timeout: float = 7, card_count: int = 3) -> int:
    """点击推荐卡片
    
    :param timeout: 超时时间(秒)
    :param card_count: 卡片数量(2-4)
    :return: 执行结果。-1=失败，0~3=卡片位置，10=跳过此回合。
    """
    import cv2
    import numpy as np
    from cv2.typing import MatLike

    # 定义检测参数
    TARGET_ASPECT_RATIO_RANGE = (0.73, 0.80)
    TARGET_COLOR = (240, 240, 240)
    YELLOW_LOWER = np.array([20, 100, 100])
    YELLOW_UPPER = np.array([30, 255, 255])
    GLOW_EXTENSION = 10  # 向外扩展的像素数
    GLOW_THRESHOLD = 1200  # 荧光值阈值

    # 固定的卡片坐标 (for 720x1280)
    CARD_POSITIONS_1 = [
        # 格式：(x, y, w, h, return_value)
        (264, 883, 192, 252, 0)
    ]
    CARD_POSITIONS_2 = [
        (156, 883, 192, 252, 1),
        (372, 883, 192, 252, 2),
        # delta_x = 216, delta_x-width = 24
    ]
    CARD_POSITIONS_3 = [
        (47, 883, 192, 252, 0),  # 左卡片 (x, y, w, h)
        (264, 883, 192, 252, 1),  # 中卡片
        (481, 883, 192, 252, 2)   # 右卡片
        # delta_x = 217, delta_x-width = 25
    ]
    CARD_POSITIONS_4 = [
        (17, 883, 192, 252, 0),
        (182, 883, 192, 252, 1),
        (346, 883, 192, 252, 2),
        (511, 883, 192, 252, 3),
        # delta_x = 165, delta_x-width = -27
    ]
    SKIP_POSITION = (621, 739, 85, 85, 10)

    @deprecated('此方法待改进')
    def calc_pos(card_count: int):
        # 根据卡片数量计算实际位置
        CARD_PAD = 25
        CARD_SCREEN_PAD = 17
        card_positions = []
        
        # 计算卡片位置
        if card_count == 1:
            card_positions = [CARD_POSITIONS_3[1]]  # 只使用中间位置
        else:
            # 计算原始卡片间距
            card_spacing = CARD_POSITIONS_3[1][0] - CARD_POSITIONS_3[0][0]
            card_width = CARD_POSITIONS_3[0][2]
            
            # 计算屏幕可用宽度
            screen_width = 720
            available_width = screen_width - (CARD_SCREEN_PAD * 2)
            
            # 计算使用原始间距时的总宽度
            original_total_width = (card_count - 1) * card_spacing + card_width
            
            # 判断是否需要重叠布局
            if original_total_width > available_width:
                spacing = (available_width - card_width * card_count - CARD_SCREEN_PAD * 2) // (card_count)
                start_x = CARD_SCREEN_PAD
            else:
                spacing = card_spacing
                start_x = (screen_width - original_total_width) // 2
            
            # 生成所有卡片位置
            x = start_x
            for i in range(card_count):
                y = CARD_POSITIONS_3[0][1]
                w = CARD_POSITIONS_3[0][2]
                h = CARD_POSITIONS_3[0][3]
                card_positions.append((round(x), round(y), round(w), round(h)))
                x += spacing + card_width
        return card_positions

    def calc_pos2(card_count: int):
        if card_count == 1:
            return CARD_POSITIONS_1
        elif card_count == 2:
            return CARD_POSITIONS_2
        elif card_count == 3:
            return CARD_POSITIONS_3
        elif card_count == 4:
            return CARD_POSITIONS_4
        else:
            raise ValueError(f"Unsupported card count: {card_count}")

    if card_count == 4:
        # 随机选择一张卡片点击
        # TODO: 支持对四张卡片进行检测
        logger.warning("4 cards detected, detecting glowing card in 4 cards is not supported yet.")
        logger.info("Click random card")
        card_index = random.randint(0, 3)
        device.click(CARD_POSITIONS_4[card_index][:4])
        sleep(1)
        device.click(CARD_POSITIONS_4[card_index][:4])
        return card_index

    start_time = time.time()
    while time.time() - start_time < timeout:
        img = device.screenshot()

        # 检测卡片
        card_glows = []
        for x, y, w, h, return_value in calc_pos2(card_count) + [SKIP_POSITION]:
            # 获取扩展后的卡片区域坐标
            outer_x = max(0, x - GLOW_EXTENSION)
            outer_y = max(0, y - GLOW_EXTENSION)
            outer_w = w + (GLOW_EXTENSION * 2)
            outer_h = h + (GLOW_EXTENSION * 2)
            
            # 获取内外两个区域
            outer_region = img[outer_y:y+h+GLOW_EXTENSION, outer_x:x+w+GLOW_EXTENSION]
            inner_region = img[y:y+h, x:x+w]
            
            # 创建掩码
            outer_hsv = cv2.cvtColor(outer_region, cv2.COLOR_BGR2HSV)
            inner_hsv = cv2.cvtColor(inner_region, cv2.COLOR_BGR2HSV)
            
            # 计算外部区域的黄色部分
            outer_mask = cv2.inRange(outer_hsv, YELLOW_LOWER, YELLOW_UPPER)
            inner_mask = cv2.inRange(inner_hsv, YELLOW_LOWER, YELLOW_UPPER)
            
            # 创建环形区域的掩码（仅计算扩展区域的荧光值）
            ring_mask = outer_mask.copy()
            ring_mask[GLOW_EXTENSION:GLOW_EXTENSION+h, GLOW_EXTENSION:GLOW_EXTENSION+w] = 0
            
            # 计算环形区域的荧光值
            glow_value = cv2.countNonZero(ring_mask)
            
            card_glows.append((x, y, w, h, glow_value, return_value))

        # 找到荧光值最高的卡片
        if not card_glows:
            logger.debug("No glowing card found, retrying...")
            continue
        else:
            max_glow_card = max(card_glows, key=lambda x: x[4])
            x, y, w, h, glow_value, return_value = max_glow_card
            if glow_value < GLOW_THRESHOLD:
                logger.debug("Glow value is too low, retrying...")
                continue
            
            # 点击卡片中心
            logger.debug(f"Click glowing card at: ({x + w//2}, {y + h//2})")
            device.click(x + w//2, y + h//2)
            sleep(random.uniform(0.5, 1.5))
            device.click(x + w//2, y + h//2)
            # 体力溢出提示框
            ret = image.wait_for(R.InPurodyuusu.ButtonConfirm, timeout=1)
            if ret is not None:
                logger.info("Skill card confirmation dialog detected")
                device.click(ret)
            if return_value == 10:
                logger.info("No enough AP. Skip this turn")
            elif return_value == -1:
                logger.warning("No glowing card found")
            else:
                logger.info("Recommended card is Card %d", return_value + 1)
            return return_value
    return -1

@deprecated('此方法待改进')
def skill_card_count1():
    """获取当前持有的技能卡数量"""
    img = device.screenshot()
    img = crop_y(img, 0.83, 0.90)
    # 黑白
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 白色 -> 黑色
    # 仅将白色(255)替换为黑色(0),保持其他颜色不变
    img[img == 255] = 0
    # 二值化
    _, img = cv2.threshold(img, 240, 255, cv2.THRESH_BINARY)
    debug.show(img)
    ret = ocr.raw('en').ocr(img)
    # 统计字母 A、M 数量
    count = 0
    for item in ret:
        if 'A' in item.text or 'M' in item.text:
            count += 1
    logger.info("Current skill card count: %d", count)
    return count

def skill_card_count():
    """获取当前持有的技能卡数量"""
    img = device.screenshot()
    img = crop_y(img, 0.83, 0.90)
    count = image.raw().count(img, R.InPurodyuusu.A, threshold=0.85)
    count += image.raw().count(img, R.InPurodyuusu.M, threshold=0.85)
    logger.info("Current skill card count: %d", count)
    return count

def remaing_turns_and_points():
    """获取剩余回合数和积分"""
    ret = ocr.ocr()
    logger.debug("ocr.ocr: %s", ret)
    def index_of(text: str) -> int:
        for i, item in enumerate(ret):
            # ＣＬＥＡＲまで -> CLEARまで
            if text == unicodedata.normalize('NFKC', item.text):
                return i
        return -1
    turns_tip_index = index_of("残りターン数")
    points_tip_index = index_of("CLEARまで")
    turns_rect = ret[turns_tip_index].rect
    # 向下扩展100像素
    turns_rect_extended = (
        turns_rect[0],  # x
        turns_rect[1],  # y 
        turns_rect[2],  # width
        turns_rect[3] + 100  # height + 100
    )
    
    # 裁剪并再次识别
    turns_img = device.screenshot()[
        turns_rect_extended[1]:turns_rect_extended[1]+turns_rect_extended[3],
        turns_rect_extended[0]:turns_rect_extended[0]+turns_rect_extended[2]
    ]
    turns_ocr = ocr.ocr(turns_img)
    logger.debug("turns_ocr: %s", turns_ocr)

def acquire_skill_card():
    """获取技能卡（スキルカード）"""
    # TODO: 识别卡片内容，而不是固定选卡
    # TODO: 不硬编码坐标
    CARD_POSITIONS = [
        (157, 820, 128, 128),
        (296, 820, 128, 128),
        (435, 820, 128, 128),
    ]
    logger.info("Click first skill card")
    device.click(CARD_POSITIONS[0])
    sleep(0.5)
    # 确定
    logger.info("Click 受け取る")
    device.click(ocr.expect(contains("受け取る")).rect)
    # 跳过动画
    device.click(image.expect_wait_any([
        R.InPurodyuusu.PSkillCardIconBlue,
        R.InPurodyuusu.PSkillCardIconColorful
    ]))

def rest():
    """执行休息"""
    logger.info("Rest for this week.")
    # 点击休息
    device.click(image.expect_wait(R.InPurodyuusu.Rest))
    # 确定
    device.click(image.expect_wait(R.InPurodyuusu.RestConfirmBtn))

AcquisitionType = Literal[
    "PDrinkAcquire", # P饮料被动领取
    "PDrinkSelect", # P饮料主动领取
    "PDrinkMax", # P饮料到达上限
    "PSkillCardAcquire", # 技能卡被动领取
    "PSkillCardSelect", # 技能卡主动领取
    "PItem", # P物品
    "Clear", # 目标达成
]
def acquisitions() -> AcquisitionType | None:
    """处理行动开始前和结束后可能需要处理的事件，直到到行动页面为止"""
    img = device.screenshot_raw()
    gray_img = grayscale(img)
    logger.info("Acquisition stuffs...")

    # P饮料被动领取
    logger.info("Check PDrink acquisition...")
    if image.raw().find(img, R.InPurodyuusu.PDrinkIcon):
        logger.info("Click to finish animation")
        device.click_center()
        sleep(1)
        return "PDrinkAcquire"
    # P饮料主动领取
    # if ocr.raw().find(img, contains("受け取るＰドリンクを選れでください")):
    if image.raw().find(img, R.InPurodyuusu.TextPleaseSelectPDrink):
        logger.info("PDrink acquisition")
        # 不领取
        # device.click(ocr.expect(contains("受け取らない")))
        # sleep(0.5)
        # device.click(image.expect(R.InPurodyuusu.ButtonNotAcquire))
        # sleep(0.5)
        # device.click(image.expect(R.InPurodyuusu.ButtonConfirm))
        acquire_pdorinku(index=0)
        return "PDrinkSelect"
    # P饮料到达上限
    if image.raw().find(img, R.InPurodyuusu.TextPDrinkMax):
        device.click(image.expect(R.InPurodyuusu.ButtonLeave))
        sleep(0.7)
        # 可能需要点击确认
        device.click(image.expect(R.InPurodyuusu.ButtonConfirm, threshold=0.8))
        return "PDrinkMax"
    # 技能卡被动领取
    logger.info("Check skill card acquisition...")
    if image.raw().find_any(img, [
        R.InPurodyuusu.PSkillCardIconBlue,
        R.InPurodyuusu.PSkillCardIconColorful
    ]):
        logger.info("Acquire skill card")
        device.click_center()
        return "PSkillCardAcquire"
    # 技能卡主动领取
    if ocr.raw().find(img, contains("受け取るスキルカードを選んでください")):
        logger.info("Acquire skill card")
        acquire_skill_card()
        sleep(5)
        return "PSkillCardSelect"

    # 目标达成
    if image.raw().find(gray_img, grayscale_cached(R.InPurodyuusu.IconClearBlue)):
        logger.debug("達成: clicked")
        device.click_center()
        sleep(5)
        # TODO: 可能不存在 達成 NEXT
        logger.debug("達成 NEXT: clicked")
        device.click_center()
        return "Clear"
    # P物品
    if image.raw().find(img, R.InPurodyuusu.PItemIconColorful):
        logger.info("Click to finish PItem acquisition")
        device.click_center()
        sleep(1)
        return "PItem"
    # 支援卡
    # logger.info("Check support card acquisition...")
    # 记忆
    # 未跳过剧情
    return None

def until_action_scene():
    """等待进入行动场景"""
    # 检测是否到行动页面
    while not image.wait_for_any([
        R.InPurodyuusu.TextPDiary, # 普通周
        R.InPurodyuusu.ButtonFinalPracticeDance # 离考试剩余一周
    ], timeout=1):
        logger.info("Action scene not detected. Retry...")
        acquisitions()
        sleep(1)
    else:
        logger.info("Now at action scene.")
        return 

def until_practice_scene():
    """等待进入练习场景"""
    while image.wait_for(R.InPurodyuusu.TextClearUntil, timeout=1) is None:
        acquisitions()
        sleep(1)

def until_exam_scene():
    """等待进入考试场景"""
    while ocr.find(regex("合格条件|三位以上")) is None:
        acquisitions()
        sleep(1)

def practice():
    """执行练习"""
    logger.info("Practice started")
    # 循环打出推荐卡
    no_card_count = 0
    MAX_NO_CARD_COUNT = 3
    while True:
        with device.pinned():
            count = skill_card_count()
            if count == 0:
                logger.info("No skill card found. Wait and retry...")
                # no_card_count += 1
                # if no_card_count >= MAX_NO_CARD_COUNT:
                #     break
                if not image.find_any([
                    R.InPurodyuusu.TextPerfectUntil,
                    R.InPurodyuusu.TextClearUntil
                ]):
                    logger.info("PERFECTまで/CLEARまで not found. Practice finished.")
                    break
                sleep(3)
                continue
        if click_recommended_card(card_count=count) == -1:
            logger.info("Click recommended card failed. Retry...")
            continue
        logger.info("Wait for next turn...")
        sleep(9) # TODO: 采用更好的方式检测练习结束
    # 跳过动画
    logger.info("Recommend card not found. Practice finished.")
    ocr.expect_wait(contains("上昇"))
    logger.info("Click to finish 上昇 ")
    device.click_center()

def exam():
    """执行考试"""
    logger.info("Exam started")
    # 循环打出推荐卡
    no_card_count = 0
    MAX_NO_CARD_COUNT = 3
    while True:
        count = skill_card_count()
        if count == 0:
            logger.info("No skill card found. Wait and retry...")
            no_card_count += 1
            if no_card_count >= MAX_NO_CARD_COUNT:
                break
            sleep(3)
            continue
        if click_recommended_card(card_count=count) == -1:
            break
        sleep(9) # TODO: 采用更好的方式检测练习结束
    
    # 点击“次へ”
    device.click(image.expect_wait(R.InPurodyuusu.NextBtn))
    while ocr.wait_for(contains("メモリー"), timeout=7):
        device.click_center()

def produce_end():
    """执行考试结束"""
    # 考试结束对话
    image.expect_wait(R.InPurodyuusu.TextAsariProduceEnd, timeout=30)
    bottom = (int(device.screen_size[0] / 2), int(device.screen_size[1] * 0.9))
    device.click(*bottom)
    sleep(3)
    device.click_center()
    sleep(3)
    device.click(*bottom)
    sleep(3)
    device.click(*bottom)
    sleep(3)

    # MV
    # 等就可以了，反正又不要自己操作（

    # 结算
    # 最終プロデュース評価
    image.expect_wait(R.InPurodyuusu.TextFinalProduceRating, timeout=60 * 2.5)
    device.click_center()
    sleep(3)
    # 次へ
    device.click(image.expect_wait(R.InPurodyuusu.ButtonNextNoIcon))
    sleep(1)
    # 決定
    device.click(image.expect_wait(R.InPurodyuusu.ButtonConfirm, threshold=0.8))
    sleep(1)
    # 上传图片。注意网络可能会很慢，可能出现上传失败对话框
    retry_count = 0
    MAX_RETRY_COUNT = 5
    while True:
        # 处理上传失败
        if image.find(R.InPurodyuusu.ButtonRetry):
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
        elif image.find(R.InPurodyuusu.ButtonClose):
            logger.info("Memory cover save failed. Click to close.")
            device.click()
        # 结算完毕
        elif image.find(R.InPurodyuusu.ButtonNextNoIcon):
            logger.info("Finalize")
            device.click()
            device.click(image.expect_wait(R.InPurodyuusu.ButtonNextNoIcon))
            device.click(image.expect_wait(R.InPurodyuusu.ButtonNextNoIcon))
            device.click(image.expect_wait(R.InPurodyuusu.ButtonComplete))
            # 关注提示
            # if image.wait_for(R.InPurodyuusu.ButtonFollowProducer, timeout=2):
            #     device.click(image.expect_wait(R.InPurodyuusu.ButtonCancel))
            break
        # 开始生成记忆
        # elif image.find(R.InPurodyuusu.ButtonGenerateMemory):
        #     logger.info("Click generate memory button")
        #     device.click()
        # 跳过结算内容
        else:
            device.click_center()
        sleep(2)


def hajime_regular(week: int = -1, start_from: int = 1):
    """
    「初」 Regular 模式

    :param week: 第几周，从1开始，-1表示全部
    :param start_from: 从第几周开始，从1开始。
    """
    def week1():
        """
        第一周 期中考试剩余5周\n
        行动：Vo.レッスン、Da.レッスン、Vi.レッスン
        """
        enter_recommended_action()
        loading.wait_loading_start()
        logger.info("Loading...")
        loading.wait_loading_end()
        logger.info("Loading end")
        # 支援卡判断
        practice()


    def week2():
        """
        第二周 期中考试剩余4周\n
        行动：授業（学习）
        """
        # 点击“授業”
        rect = image.expect_wait(R.InPurodyuusu.Action.ActionStudy).rect
        device.click(rect)
        sleep(0.5)
        device.click(rect)
        # 等待加载
        loading.wait_loading_start()
        logger.info("Loading...")
        # 等待加载结束
        loading.wait_loading_end()
        logger.info("Loading end")
        # 判断是否触发支援卡剧情

        # TODO:检查是否有支援卡要领取的技能卡

        # 等待加载
        loading.wait_loading_start()
        logger.info("Loading...")
        # 等待加载结束
        loading.wait_loading_end()
        logger.info("Loading end")

        # 进入授業页面
        pos = image.expect_wait(R.InPurodyuusu.Action.VocalWhiteBg).rect
        device.click(pos)
        sleep(0.5)
        device.click(pos)
        # 选择选项
        # TODO: 不固定点击 Vocal
        device.double_click(image.expect_wait(R.InPurodyuusu.Action.VocalWhiteBg).rect)
        # 领取技能卡
        acquire_skill_card()

        # 三次加载画面
        loading.wait_loading_start()
        logger.info("Loading 1...")
        loading.wait_loading_end()
        logger.info("Loading 1 end")
        loading.wait_loading_start()
        logger.info("Loading 2...")
        loading.wait_loading_end()
        logger.info("Loading 2 end")
        loading.wait_loading_start()
        logger.info("Loading 3...")
        loading.wait_loading_end()
        logger.info("Loading 3 end")

    def week3():
        """
        第三周 期中考试剩余3周\n
        行动：Vo.レッスン、Da.レッスン、Vi.レッスン、授業
        """
        week1()

    def week4():
        """
        第四周 期中考试剩余2周\n
        行动：おでかけ、相談、活動支給
        """
        week3()

    def week5():
        """TODO"""

    def week6():
        """期中考试"""

    def week7():
        """第七周 期末考试剩余6周"""
        if not enter_recommended_action():
            rest()

    def week8():
        """
        第八周 期末考试剩余5周\n
        行动：授業、活動支給
        """
        if not enter_recommended_action():
            rest()

    def week_common():
        until_action_scene()
        executed_action = enter_recommended_action()
        logger.info("Executed recommended action: %s", executed_action)
        if executed_action == 'lesson':
            sleep(5)
            until_practice_scene()
            practice()
        elif executed_action == 'rest':
            pass
        elif executed_action is None:
            rest()
        until_action_scene()
        

    def week_final():
        if enter_recommended_action(final_week=True) != 'lesson':
            raise ValueError("Failed to enter recommended action on final week.")
        sleep(5)
        until_practice_scene()
        practice()
        # until_exam_scene()
    
    def week_mid_exam():
        logger.info("Week mid exam started.")
        logger.info("Wait for exam scene...")
        until_exam_scene()
        logger.info("Exam scene detected.")
        sleep(5)
        device.click_center()
        sleep(5)
        exam()
        until_action_scene()
    
    def week_final_exam():
        logger.info("Week final exam started.")
        logger.info("Wait for exam scene...")
        until_exam_scene()
        logger.info("Exam scene detected.")
        sleep(5)
        device.click_center()
        sleep(5)
        exam()
        produce_end()
    
    weeks = [
        week_common, # 1
        week_common, # 2
        week_common, # 3
        week_common, # 4
        week_final, # 5
        week_mid_exam, # 6
        week_common, # 7
        week_common, # 8
        week_common, # 9
        week_common, # 10
        week_common, # 11
        week_final, # 12
        week_final_exam, # 13
    ]
    if week != -1:
        logger.info("Week %d started.", week)
        weeks[week - 1]()
    else:
        for i, w in enumerate(weeks[start_from-1:]):
            logger.info("Week %d started.", i + start_from)
            w()

def purodyuusu(
    # TODO: 参数：成员、支援、记忆、 两个道具
):
    # 流程：
    # 1. Sensei 对话
    # 2. Idol 对话
    # 3. 领取P饮料（？）
    # 4. 触发支援卡事件。触发后必定需要领取物品
    pass


__actions__ = [enter_recommended_action]

if __name__ == '__main__':
    from logging import getLogger
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    getLogger('kotonebot').setLevel(logging.DEBUG)
    getLogger(__name__).setLevel(logging.DEBUG)
    init_context()

    while not image.wait_for_any([
        R.InPurodyuusu.TextPDiary, # 普通周
        R.InPurodyuusu.ButtonFinalPracticeDance # 离考试剩余一周
    ], timeout=2):
        logger.info("Action scene not detected. Retry...")
        acquisitions()
        sleep(3)

    # image.wait_for_any([
    #     R.InPurodyuusu.TextPDiary, # 普通周
    #     R.InPurodyuusu.ButtonFinalPracticeDance # 离考试剩余一周
    # ], timeout=2)
    # while True:
    #     sleep(10)

    # exam()
    # produce_end()
    # enter_recommended_action()
    # remaing_turns_and_points()
    # practice()
    # until_action_scene()
    # acquisitions()
    # acquire_pdorinku(0)
    # image.wait_for(R.InPurodyuusu.InPractice.PDorinkuIcon)
    # hajime_regular(start_from=1)
    # until_practice_scene()
    # device.click(image.expect_wait_any([
    #     R.InPurodyuusu.PSkillCardIconBlue,
    #     R.InPurodyuusu.PSkillCardIconColorful
    # ]).rect)
    # exam()
    # device.double_click(image.expect_wait(R.InPurodyuusu.Action.VocalWhiteBg).rect)
    # print(skill_card_count())
    # click_recommended_card(card_count=skill_card_count())
    # click_recommended_card(card_count=2)
    # acquire_skill_card()
    # rest()
    # enter_recommended_lesson(final_week=True)
