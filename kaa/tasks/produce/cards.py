import logging
from functools import partial
from typing import Callable, NamedTuple, Literal

import cv2
import numpy as np
from cv2.typing import MatLike

from kaa.db.drink import Drink
from kaa.game_ui.drinks_overview import locate_all_drinks_in_3_drink_slots
from kaa.tasks import R
from kaa.config import conf
from kaa.game_ui import dialog
from kaa.tasks.produce.common import acquisition_date_change_dialog
from kaa.util.trace import trace
from kotonebot.primitives import RectTuple, Rect
from kotonebot import action, Interval, Countdown, device, image, sleep, ocr, contains, use_screenshot, color
from kotonebot.backend.loop import Loop

class SkillCard(NamedTuple):
    available: bool
    rect: Rect

class CardPosInfo(NamedTuple):
    x: int
    y: int
    w: int
    h: int
    type: Literal[0, 1, 2, 3, 4, 10] # 0~4=卡片下标，10=SKIP

class CardDetectResult(NamedTuple):
    type: int
    """
    点击的卡片类型。

    0=第一张卡片，1=第二张卡片，2=第三张卡片，3=第四张卡片，10=SKIP。
    """
    score: float
    """总分数"""
    left_score: float
    """左边分数"""
    right_score: float
    """右边分数"""
    top_score: float
    """上边分数"""
    bottom_score: float
    """下边分数"""
    rect: Rect

logger = logging.getLogger(__name__)

# TODO: 硬编码。需要想办法移动到资源文件中
CARD_SIZE = (192, 252) # 卡片大小 w, h
CARD_Y = 883 # 卡片 Y 坐标
# 只有一张卡的情况
CARD_START_X_1 = 264
CARD_DELTA_X_1 = 0
# 两张卡的情况
CARD_START_X_2 = 156 # 第一张卡的起始 X
CARD_DELTA_X_2 = 24 # 间隔距离 = card_x_2 - card_x_1 - card_width
# 三张卡的情况
CARD_START_X_3 = 47
CARD_DELTA_X_3 = 25
# 四张卡的情况
CARD_START_X_4 = 17
CARD_DELTA_X_4 = -27
# 五张卡的情况
CARD_START_X_5 = 17
CARD_DELTA_X_5 = -68
# SKIP 按钮
SKIP_CARD_BUTTON = CardPosInfo(621, 739, 85, 85, 10)


def calc_card_position(card_count: int):
    w, h = CARD_SIZE
    if card_count == 1:
        result = [
            CardPosInfo(x=CARD_START_X_1, y=CARD_Y, w=w, h=h, type=0)
        ]
    elif card_count == 2:
        delta = CARD_DELTA_X_2 + w
        result = [
            CardPosInfo(x=CARD_START_X_2, y=CARD_Y, w=w, h=h, type=0),
            CardPosInfo(x=CARD_START_X_2 + delta, y=CARD_Y, w=w, h=h, type=1),
        ]
    elif card_count == 3:
        delta = CARD_DELTA_X_3 + w
        result = [
            CardPosInfo(x=CARD_START_X_3, y=CARD_Y, w=w, h=h, type=0),
            CardPosInfo(x=CARD_START_X_3 + delta, y=CARD_Y, w=w, h=h, type=1),
            CardPosInfo(x=CARD_START_X_3 + delta * 2, y=CARD_Y, w=w, h=h, type=2),
        ]
    elif card_count == 4:
        delta = CARD_DELTA_X_4 + w
        result = [
            CardPosInfo(x=CARD_START_X_4, y=CARD_Y, w=w, h=h, type=0),
            CardPosInfo(x=CARD_START_X_4 + delta, y=CARD_Y, w=w, h=h, type=1),
            CardPosInfo(x=CARD_START_X_4 + delta * 2, y=CARD_Y, w=w, h=h, type=2),
            CardPosInfo(x=CARD_START_X_4 + delta * 3, y=CARD_Y, w=w, h=h, type=3),
        ]
    elif card_count == 5:
        delta = CARD_DELTA_X_5 + w
        result = [
            CardPosInfo(x=CARD_START_X_5, y=CARD_Y, w=w, h=h, type=0),
            CardPosInfo(x=CARD_START_X_5 + delta, y=CARD_Y, w=w, h=h, type=1),
            CardPosInfo(x=CARD_START_X_5 + delta * 2, y=CARD_Y, w=w, h=h, type=2),
            CardPosInfo(x=CARD_START_X_5 + delta * 3, y=CARD_Y, w=w, h=h, type=3),
            CardPosInfo(x=CARD_START_X_5 + delta * 4, y=CARD_Y, w=w, h=h, type=4),
        ]
    else:
        raise ValueError(f'不支持 {card_count} 张手牌')
    return result

@action('打牌', screenshot_mode='manual')
def do_cards(
        is_exam: bool,
        threshold_predicate: Callable[[int, CardDetectResult], bool],
        end_predicate: Callable[[], bool]
    ):
    """
    循环打出推荐卡，直到考试/练习结束

    前置条件：考试/练习页面\n
    结束状态：考试/练习结束的一瞬间

    :param is_exam: 是否是考试
    :param threshold_predicate: 推荐卡检测阈值判断函数
    :param end_predicate: 结束条件判断函数
    """
    timeout_cd = Countdown(sec=conf().produce.produce_timeout_cd).start() # 推荐卡检测超时计时器
    break_cd = Countdown(sec=5) # 满足结束条件计时器
    no_card_cd = Countdown(sec=4) # 无手牌计时器
    detect_card_count_cd = Countdown(sec=4).start() # 刷新检测手牌数量间隔
    tries = 1
    card_count = -1
    timeout_card_id = 1 # timeout时，选择的卡的编号
                        # 每次选择后会自增；若成功打出，则重置为1；如果全不无法选中，那么预测系统应该会选择空过本回合，不用考虑

    enable_drink: bool = is_exam # 避免耦合
    drinks_list: list[tuple[Drink, RectTuple]] | None = None
    drink_selected_idx: int = -1 # 此索引指向drinks_list
    drink_retries = 0
    DRINK_MAX_RETRIES = 5

    for _ in Loop(interval=1/30):
        device.click(10, 10)
        img = device.screenshot()

        # 技能卡自选移动对话框
        if image.find(R.InPurodyuusu.IconTitleSkillCardMove):
            if handle_skill_card_move():
                sleep(4)  # 等待卡片刷新
                continue
        # 饮品详细对话框（需要在 ButtonIconCheckMark 之前，因为ButtonUse也是√）
        if image.find(R.InPurodyuusu.ButtonUse):
            # 任何情况下都点击（避免卡死）
            device.click()
            if enable_drink and drinks_list is not None:
                if drink_selected_idx < 0 or drink_selected_idx >= len(drinks_list):
                    logger.warning('`drink_selected_idx` dismatches, internal error!')
                else:
                    drinks_list.pop(drink_selected_idx)
                    drink_selected_idx = -1 # Reset
                    drink_retries = 0 # 逻辑正常运作，重置drink_retries
                    logger.info('Used selected drink.')
                    sleep(3) # 饮品动画
                    img = device.screenshot()
                    drinks_list = locate_all_drinks_in_3_drink_slots(img)
                    logger.info("Rematched %d drinks. Detailed: %s", len(drinks_list), str(drinks_list))
            else:
                logger.warning('Unexpected use drink dialog.')
            continue
        # 技能卡效果无法发动对话框
        if image.find(R.Common.ButtonIconCheckMark):
            logger.info("Confirmation dialog detected")
            device.click()
            sleep(4)  # 等待卡片刷新
            continue

        # 匹配饮品
        # - 顺序应该在对话框检测之后、卡片更新之前
        # 考试时，初始化饮料
        if enable_drink and drinks_list is None:
            drinks_list = locate_all_drinks_in_3_drink_slots(img)
            logger.info("Matched %d drinks. Detailed: %s", len(drinks_list), str(drinks_list))
        # 考试时，处理具体的饮料
        if enable_drink and drinks_list is not None and len(drinks_list) > 0:
            if drinks_list[0][0].name in Drink.ordinary_drinks_name():
                # 可以处理第0个饮品
                drink_selected_idx = 0
                # 点击
                device.click(Rect(xywh=drinks_list[drink_selected_idx][1]))
                # Log
                logger.info('Click drink %s', drinks_list[0][0].name)
            else:
                # Log
                logger.info('Drink %s cannot be process, skip', drinks_list[0][0].name)
                # 不可以处理第0个饮品
                drinks_list.pop(0)
                drink_retries = 0 # 逻辑正常运作，重置drink_retries

            drink_retries += 1
            if drink_retries > DRINK_MAX_RETRIES: # 卡死
                drink_retries = 0
                drinks_list.pop(drink_selected_idx)
                logger.warning('Drink processing stuck. Force to pop drink.')
            continue

        # 更新卡片数量
        if card_count == -1 or detect_card_count_cd.expired():
            detect_card_count_cd.reset()
            card_count = skill_card_count(img)
            logger.debug("Current card count: %d", card_count)
        # 处理手牌
        if card_count == 0:
            # 处理本回合已无剩余手牌的情况
            # TODO: 使用模板匹配而不是 OCR，提升速度
            no_card_cd.start()
            no_remaining_card = ocr.find(contains("0枚"), rect=R.InPurodyuusu.BoxNoSkillCard)
            if no_remaining_card and no_card_cd.expired():
                logger.debug('No remaining card detected. Skip this turn.')
                # TODO: HARD CODEDED
                SKIP_POSITION = Rect(621, 739, 85, 85)
                device.click(SKIP_POSITION)
                no_card_cd.reset()
                continue
        else:
            if handle_recommended_card(
                card_count=card_count,
                threshold_predicate=threshold_predicate,
                img=img
            ):
                logger.info("Handle recommended card success with %d tries", tries)
                sleep(4.5)
                tries = 0
                timeout_cd.reset()
                continue
            else:
                tries += 1
        # 检测超时（防止一直卡在检测）
        if timeout_cd.expired():
            if card_count == 0:
                logger.warning("Recommend card detection timeout but no card found.")
                timeout_cd.reset()
                continue
            card_rects = calc_card_position(card_count)
            assert len(card_rects) == card_count, "len(card_rects) != card_count, internal code error!"

            # 让timeout_card_id自增，避免“因为第一张卡无法打出，导致卡在第一张卡上”的情况
            timeout_card_id = timeout_card_id % card_count + 1
            logger.info(f"Recommend card detection timed out. Click {timeout_card_id}-th card.")

            card_rect = card_rects[timeout_card_id - 1]
            device.double_click(Rect(xywh=card_rect[:4]))
            sleep(2)
            timeout_cd.reset()
        # 日期变更检测
        acquisition_date_change_dialog()
        # 结束条件
        if card_count == 0 and end_predicate():
            if not break_cd.started:
                logger.debug('start break_cd')
                break_cd.reset().start()
            if break_cd.expired():
                logger.info("End condition met. do_cards finished.")
                break
        else:
            logger.debug('reset break_cd')
            break_cd.stop()

@action("技能卡移动")
def handle_skill_card_move():
    """
    前置条件：技能卡移动对话框\n
    结束状态：对话框结束瞬间
    """
    cards = image.find_all_multi([
        R.InPurodyuusu.A,
        R.InPurodyuusu.M,
        R.InPurodyuusu.T,
    ])
    if not cards:
        logger.info("No skill cards found")
        return False

    cd = Countdown(sec=3)
    for _ in Loop():
        # 判断对话框是否关闭
        # 已关闭，开始计时
        if not image.find(R.InPurodyuusu.IconTitleSkillCardMove):
            cd.start()
            if cd.expired():
                logger.info("Skill card move dialog closed.")
                break
        # 没有，要继续选择并确定
        else:
            cd.reset()
            if not cards:
                logger.info("No skill cards left. Retrying...")
                cards = image.find_all_multi([
                    R.InPurodyuusu.A,
                    R.InPurodyuusu.M,
                    R.InPurodyuusu.T,
                ])
            card = cards.pop()
            device.double_click(card)
            sleep(1)
            dialog.yes()
    logger.debug("Handle skill card move finished.")

@action('获取当前卡牌信息', screenshot_mode='manual-inherit')
def obtain_cards(img: MatLike | None = None):
    img = use_screenshot(img)
    cards_rects = image.find_all_multi([
        R.InPurodyuusu.A,
        R.InPurodyuusu.M,
        R.InPurodyuusu.T
    ])
    logger.info("Current cards: %s", len(cards_rects))
    cards = []
    for result in cards_rects:
        available = color.find('#7a7d7d', rect=result.rect) is None
        cards.append(SkillCard(available=available, rect=result.rect))
    return cards


def handle_recommended_card(
        card_count: int, timeout: float = 7,
        threshold_predicate: Callable[[int, CardDetectResult], bool] = lambda _, __: True,
        *,
        img: MatLike | None = None,
    ):
    result = detect_recommended_card(card_count, threshold_predicate, img=img)
    if result is not None:
        device.double_click(result)
        return result
    return None


@action('获取当前卡片数量', screenshot_mode='manual-inherit')
def skill_card_count(img: MatLike | None = None):
    """获取当前持有的技能卡数量"""
    img = use_screenshot(img)
    x, y, w, h = R.InPurodyuusu.BoxCardLetter.xywh
    img = img[y:y+h, x:x+w]
    count = image.raw().count(img, R.InPurodyuusu.A)
    count += image.raw().count(img, R.InPurodyuusu.M)
    count += image.raw().count(img, R.InPurodyuusu.T)
    logger.info("Current skill card count: %d", count)
    return count


def detect_recommended_card(
        card_count: int,
        threshold_predicate: Callable[[int, CardDetectResult], bool],
        *,
        img: MatLike | None = None,
    ):
    """
    识别推荐卡片

    前置条件：练习或考试中\n
    结束状态：-

    :param card_count: 卡片数量(2-4)
    :param threshold_predicate: 阈值判断函数
    :return: 执行结果。若返回 None，表示未识别到推荐卡片。
    """
    YELLOW_LOWER = np.array([20, 100, 100])
    YELLOW_UPPER = np.array([30, 255, 255])
    GLOW_EXTENSION = 15

    cards = calc_card_position(card_count)
    cards.append(SKIP_CARD_BUTTON)

    img = use_screenshot(img)
    original_image = img.copy()
    results: list[CardDetectResult] = []
    for x, y, w, h, return_value in cards:
        outer = (max(0, x - GLOW_EXTENSION), max(0, y - GLOW_EXTENSION))
        # 裁剪出检测区域
        glow_area = img[outer[1]:y + h + GLOW_EXTENSION, outer[0]:x + w + GLOW_EXTENSION]
        area_h = glow_area.shape[0]
        area_w = glow_area.shape[1]
        glow_area[GLOW_EXTENSION:area_h-GLOW_EXTENSION, GLOW_EXTENSION:area_w-GLOW_EXTENSION] = 0

        # 过滤出目标黄色
        glow_area = cv2.cvtColor(glow_area, cv2.COLOR_BGR2HSV)
        yellow_mask = cv2.inRange(glow_area, YELLOW_LOWER, YELLOW_UPPER)
        
        # 分割出每一边
        left_border = yellow_mask[:, 0:GLOW_EXTENSION]
        right_border = yellow_mask[:, area_w-GLOW_EXTENSION:area_w]
        top_border = yellow_mask[0:GLOW_EXTENSION, :]
        bottom_border = yellow_mask[area_h-GLOW_EXTENSION:area_h, :]
        y_border_pixels = area_h * GLOW_EXTENSION
        x_border_pixels = area_w * GLOW_EXTENSION

        # 计算每一边的分数
        left_score = np.count_nonzero(left_border) / y_border_pixels
        right_score = np.count_nonzero(right_border) / y_border_pixels
        top_score = np.count_nonzero(top_border) / x_border_pixels
        bottom_score = np.count_nonzero(bottom_border) / x_border_pixels

        result = (left_score + right_score + top_score + bottom_score) / 4
        results.append(CardDetectResult(
            return_value,
            result,
            left_score,
            right_score,
            top_score,
            bottom_score,
            Rect(x, y, w, h)
        ))
        img = original_image.copy()
    #     cv2.imshow(f"card detect {return_value}", cv2.cvtColor(glow_area, cv2.COLOR_HSV2BGR))
    #     cv2.namedWindow(f"card detect {return_value}", cv2.WINDOW_NORMAL)
    #     cv2.moveWindow(f"card detect {return_value}", 100 + (return_value % 3) * 300, 100 + (return_value // 3) * 300)
    # cv2.waitKey(1)
    filtered_results = list(filter(partial(threshold_predicate, card_count), results))
    if not filtered_results:
        max_result = max(results, key=lambda x: x.score)
        logger.info("Max card detect result (discarded): value=%d score=%.4f borders=(%.4f, %.4f, %.4f, %.4f)",
            max_result.type,
            max_result.score,
            max_result.left_score,
            max_result.right_score,
            max_result.top_score,
            max_result.bottom_score
        )
        return None
    filtered_results.sort(key=lambda x: x.score, reverse=True)
    logger.info("Max card detect result: value=%d score=%.4f borders=(%.4f, %.4f, %.4f, %.4f)",
        filtered_results[0].type,
        filtered_results[0].score,
        filtered_results[0].left_score,
        filtered_results[0].right_score,
        filtered_results[0].top_score,
        filtered_results[0].bottom_score
    )
    # 跟踪检测结果
    if conf().trace.recommend_card_detection:
        x, y, w, h = filtered_results[0].rect.xywh
        cv2.rectangle(original_image, (x, y), (x+w, y+h), (0, 0, 255), 3)
        trace('rec-card', original_image, {
            'card_count': card_count,
            'type': filtered_results[0].type,
            'score': filtered_results[0].score,
            'borders': (
                filtered_results[0].left_score,
                filtered_results[0].right_score,
                filtered_results[0].top_score,
                filtered_results[0].bottom_score
            )
        })
    return filtered_results[0]

if __name__ == '__main__':
    img = cv2.imread(r'/kotonebot-resource/sprites/jp/in_purodyuusu/produce_exam_1.png')
    print(skill_card_count(img))