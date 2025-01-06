import random
import re
import time
from typing_extensions import deprecated
import numpy as np
import cv2
import unicodedata
import logging
from time import sleep

from kotonebot import ocr, device, fuzz, contains, image, debug, regex
from kotonebot.backend.util import crop_y, cropper_y
from kotonebot.tasks import R
from kotonebot.tasks.actions import loading
from kotonebot.tasks.actions.pdorinku import acquire_pdorinku

logger = logging.getLogger(__name__)

def enter_recommended_action(final_week: bool = False) -> bool:
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
        return False
    if not final_week:
        if "ボーカル" in ret.text:
            lesson_text = "Vo.レッスン"
        elif "ダンス" in ret.text:
            lesson_text = "Da.レッスン"
        elif "ビジュアル" in ret.text:
            lesson_text = "Vi.レッスン"
        elif "休" in ret.text or "体力" in ret.text:
            rest()
            return True
        else:
            return False
        logger.info("Rec. lesson: %s", lesson_text)
        # 点击课程
        logger.debug("Try clicking lesson...")
        lesson_ret = ocr.expect(contains(lesson_text))
        device.double_click(lesson_ret.rect)
        return True
    else:
        if "ボーカル" in ret.text:
            template = R.InPurodyuusu.ButtonFinalPracticeVocal
        elif "ダンス" in ret.text:
            template = R.InPurodyuusu.ButtonFinalPracticeDance
        elif "ビジュアル" in ret.text:
            template = R.InPurodyuusu.ButtonFinalPracticeVisual
        else:
            return False
        logger.debug("Try clicking lesson...")
        device.double_click(image.expect_wait(template))
        return True

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
        (264, 883, 192, 252)
    ]
    CARD_POSITIONS_2 = [
        (156, 883, 192, 252),
        (372, 883, 192, 252),
        # delta_x = 216, delta_x-width = 24
    ]
    CARD_POSITIONS_3 = [
        (47, 883, 192, 252),  # 左卡片 (x, y, w, h)
        (264, 883, 192, 252),  # 中卡片
        (481, 883, 192, 252)   # 右卡片
        # delta_x = 217, delta_x-width = 25
    ]
    CARD_POSITIONS_4 = [
        (17, 883, 192, 252),
        (182, 883, 192, 252),
        (346, 883, 192, 252),
        (511, 883, 192, 252),
        # delta_x = 165, delta_x-width = -27
    ]
    SKIP_POSITION = (621, 739, 85, 85)

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

    logger.debug("等待截图...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        img = device.screenshot()

        # 检测卡片
        card_glows = []
        for x, y, w, h in calc_pos2(card_count) + [SKIP_POSITION]:
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
            
            card_glows.append((x, y, w, h, glow_value))

        # 找到荧光值最高的卡片
        if not card_glows:
            logger.debug("No glowing card found, retrying...")
            continue
        else:
            max_glow_card = max(card_glows, key=lambda x: x[4])
            x, y, w, h, glow_value = max_glow_card
            if glow_value < GLOW_THRESHOLD:
                logger.debug("Glow value is too low, retrying...")
                continue
            
            # 点击卡片中心
            logger.debug(f"Click glowing card at: ({x + w//2}, {y + h//2})")
            device.click(x + w//2, y + h//2)
            sleep(random.uniform(0.5, 1.5))
            device.click(x + w//2, y + h//2)
            return True
    return False

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

def acquisitions():
    """处理行动结束可能需要处理的事件，直到到行动页面为止"""
    logger.info("Action end stuffs...")
    # P饮料被动领取
    logger.info("Check PDrink acquisition...")
    if image.find(R.InPurodyuusu.PDrinkIcon):
        logger.info("Click to finish animation")
        device.click_center()
        sleep(1)
    # P物品
    # logger.info("Check PItem acquisition...")
    # if image.wait_for(R.InPurodyuusu.PItemIcon, timeout=1):
    #     logger.info("Click to finish animation")
    #     device.click_center()
    #     sleep(1)
    # 技能卡被动领取
    logger.info("Check skill card acquisition...")
    if image.wait_for_any([
        R.InPurodyuusu.PSkillCardIconBlue,
        R.InPurodyuusu.PSkillCardIconColorful
    ], timeout=1):
        logger.info("Acquire skill card")
        device.click_center()
    # 技能卡主动领取
    if ocr.find(contains("受け取るスキルカードを選んでください")):
        logger.info("Acquire skill card")
        acquire_skill_card()
    # P饮料主动领取
    if ocr.find(contains("受け取るＰドリンクを選れでください")):
        # 不领取
        device.click(ocr.expect(contains("受け取らない")))
        sleep(0.5)
        device.click(image.expect(R.InPurodyuusu.ButtonNotAcquire))
        sleep(0.5)
        device.click(image.expect(R.InPurodyuusu.ButtonConfirm))

    # 检测目标达成
    if ocr.find(contains("達成")):
        logger.debug("達成: clicked")
        device.click_center()
        sleep(2)
        logger.debug("達成: clicked 2")
        device.click_center()
    # 支援卡
    # logger.info("Check support card acquisition...")
    # 记忆
    # 未跳过剧情

def until_action_scene():
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
    while not image.wait_for(R.InPurodyuusu.TextClearUntil, timeout=1):
        acquisitions()
        sleep(1)

def practice():
    """执行练习"""
    logger.info("Practice started")
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
        if not click_recommended_card(card_count=count):
            break
        sleep(9) # TODO: 采用更好的方式检测练习结束
    # 跳过动画
    logger.info("Recommend card not found. Practice finished.")
    ocr.expect_wait(contains("上昇"))
    device.click_center()
    logger.info("Wait practice finish animation...")
    # # 领取P饮料
    # sleep(7) # TODO: 采用更好的方式检测动画结束
    # if image.wait_for(R.InPurodyuusu.PDrinkIcon, timeout=5):
    #     logger.info("Click to finish animation")
    #     device.click_center()
    #     sleep(1)
    # # 领取技能卡
    # ocr.wait_for(contains("受け取るスキルカードを選んでください"))
    # logger.info("Acquire skill card")
    # acquire_skill_card()

    # # 等待加载动画
    # loading.wait_loading_start()
    # logger.info("Loading...")
    # loading.wait_loading_end()
    # logger.info("Loading end")

    # # 检测目标达成
    # if ocr.wait_for(contains("達成"), timeout=5):
    #     logger.debug("達成: clicked")
    #     device.click_center()
    #     sleep(2)
    #     logger.debug("達成: clicked 2")
    #     device.click_center()

def exam():
    """执行考试"""
    logger.info("Wait for exam scene...")
    # TODO: 等待考试开始
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
        if not click_recommended_card(card_count=count):
            break
        sleep(9) # TODO: 采用更好的方式检测练习结束
    
    # 点击“次へ”
    device.click(image.expect_wait(R.InPurodyuusu.NextBtn))
    while ocr.wait_for(contains("メモリー"), timeout=7):
        device.click_center()
    # 领取技能卡
    acquire_skill_card()


def hajime_regular(week: int = -1, start_from: int = 0):
    """
    「初」 Regular 模式
    :param week: 第几周，从1开始，-1表示全部
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
        logger.info("Regular week 2 started.")
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
        logger.info("Regular week 3 started.")
        week1()

    def week4():
        """
        第四周 期中考试剩余2周\n
        行动：おでかけ、相談、活動支給
        """
        logger.info("Regular week 4 started.")
        week3()

    def week5():
        """TODO"""

    def week6():
        """期中考试"""
        logger.info("Regular week 6 started.")

    def week7():
        """第七周 期末考试剩余6周"""
        logger.info("Regular week 7 started.")
        if not enter_recommended_action():
            rest()

    def week8():
        """
        第八周 期末考试剩余5周\n
        行动：授業、活動支給
        """
        logger.info("Regular week 8 started.")
        if not enter_recommended_action():
            rest()

    def week_common():
        if not enter_recommended_action():
            rest()
        else:
            sleep(5)
            until_practice_scene()
            practice()
        until_action_scene()
        

    def week_final():
        if not enter_recommended_action(final_week=True):
            raise ValueError("Failed to enter recommended action on final week.")
        sleep(5)
        until_practice_scene()
        practice()
        # until_exam_scene()
        
    weeks = [
        week_common, # 1
        week_common, # 2
        week_common, # 3
        week_common, # 4
        week_final, # 5
        exam, # 6
        week_common, # 7
        week_common, # 8
        week_common, # 9
        week_common, # 10
        week_common, # 11
        week_final, # 12
        exam, # 13
    ]
    if week != -1:
        weeks[week - 1]()
    else:
        for w in weeks[start_from-1:]:
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

    # exam()
    # enter_recommended_action()
    # remaing_turns_and_points()
    practice()
    # action_end()
    # acquire_pdorinku(0)
    # image.wait_for(R.InPurodyuusu.InPractice.PDorinkuIcon)
    # hajime_regular(start_from=5)
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
