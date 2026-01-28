import functools
from typing import Any, Callable, Literal, TypeVar, ParamSpec, cast, TYPE_CHECKING

import cv2
import numpy as np
from kotonebot.primitives import Rect
from kotonebot.core import GameObject, AnyOf, Prefab
from kotonebot.errors import UnrecoverableError
from kotonebot import logging, device, sleep, Countdown, Loop, cropped, ocr

from kaa.tasks import R
from kaa.tasks.common import skip
from kaa.config.const import ProduceAction
from kaa.tasks.actions.loading import loading
from kaa.game_ui import CommuEventButtonUI, dialog, badge
from .consts import Drink, Scene, SceneType, SelectDrinkDialog, PerformanceMetricsVal
from kaa.tasks.produce.cards import CardDetectResult, detect_recommended_card, skill_card_count
if TYPE_CHECKING:
    from .controller import ProduceController

logger = logging.getLogger(__name__)
ORANGE_RANGE = ((14, 87, 23)), ((37, 211, 255))
# 三个饮料的坐标
POSTIONS = [
    Rect(157, 820, 128, 128),  # x, y, w, h
    Rect(296, 820, 128, 128),
    Rect(435, 820, 128, 128),
]  # TODO: HARD CODED
_R = TypeVar("_R")
_P = ParamSpec("_P")

PITEM_POSTIONS = [
    Rect(157, 820, 128, 128), # x, y, w, h
    Rect(296, 820, 128, 128),
    Rect(435, 820, 128, 128),
] # TODO: HARD CODED

def wait_disappear(prefab: type[Prefab[Any]], timeout_sec: float = 10.0) -> bool:
    """等待 Prefab 消失

    :param prefab: 目标 Prefab 类型
    :param timeout_sec: 超时时间，单位秒
    :return: 是否成功消失
    """
    logger.debug(f"Waiting for {prefab} to disappear...")
    cd = Countdown(sec=timeout_sec).start()
    for _ in Loop():
        if cd.expired():
            logger.warning(f'Timeout waiting for {prefab} to disappear.')
            raise TimeoutError(f'Timeout waiting for {prefab} to disappear.')
            return False
        if not prefab.exists():
            logger.debug(f"{prefab} has disappeared.")
            return True
    return False

def eval_once(func: Callable[_P, _R]) -> Callable[_P, _R]:
    """
    按第一个位置参数缓存的装饰器。

    行为说明：
    - 如果调用时存在位置参数，则仅以第一个位置参数作为缓存键，后续使用相同第一个参数的调用
      将直接返回第一次计算的结果（忽略其它参数和关键字参数）。
    - 如果调用时没有任何位置参数，则使用单一的全局缓存（与原先的 "eval once" 行为一致）。
    """
    cache: dict[object, _R] = {}
    global_cached_result: _R | None = None
    global_is_cached = False

    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        nonlocal global_cached_result, global_is_cached

        if args:
            key = args[0]
            if key in cache:
                return cast(_R, cache[key])
            result = func(*args, **kwargs)
            cache[key] = result
            return cast(_R, result)

        if not global_is_cached:
            global_cached_result = func(*args, **kwargs)
            global_is_cached = True

        return cast(_R, global_cached_result)

    return wrapper

class Flow:
    """可被 `ProduceController` 调度的多步流程。

    `step` 应返回是否完成当前流程。
    """

    def step(self, scene: 'Scene') -> bool:
        """推进一步当前 Flow。会被 ProduceController 在每一 tick 调用一次。

        :param scene: 当前场景。
        :return: 若流程全部结束，则返回 True 表示退出当前流程，否则返回 False 表示继续当前流程。
        """
        raise NotImplementedError # pragma: no cover


class _SceneCheckMixin:
    def check_scene(self) -> Scene | None:
        return (
            self._check_loading()
            or self._check_interrupt_dialogs()
            or self._check_dialogs()
            or self._check_fullscreen_dialogs()
            or self._check_action_like()
            or self._battle_scene()
        )

    def check_interrupt_scene(self) -> Scene | None:
        """仅检测可在“子循环(pump)”中处理的中断/对话框类场景。

        注意：这里刻意不包含 ACTION_SELECT / PRACTICE / EXAM 等主流程场景，
        以避免在弹窗处理的阻塞循环中误触发主状态机逻辑。
        """
        return (
            self._check_loading()
            or self._check_interrupt_dialogs()
            or self._check_dialogs()
            or self._check_fullscreen_dialogs()
        )

    def _check_loading(self) -> Scene | None:
        """判断加载场景"""
        if loading():
            return Scene(SceneType.LOADING)
        return None

    def _check_interrupt_dialogs(self) -> Scene | None:
        """判断各种中断/弹窗场景"""
        # P饮料到达上限
        if R.InPurodyuusu.TextPDrinkMax.exists():
            logger.debug("Scene detected: PDRINK_MAX")
            return Scene(SceneType.PDRINK_MAX)

        # P饮料到达上限确认
        if R.InPurodyuusu.TextPDrinkMaxConfirmTitle.exists():
            logger.debug("Scene detected: PDRINK_MAX_CONFIRM")
            return Scene(SceneType.PDRINK_MAX_CONFIRM)

        # # 网络错误弹窗
        # if R.Common.TextNetworkError.exists():
        #     logger.debug("Scene detected: NETWORK_ERROR")
        #     return Scene(SceneType.NETWORK_ERROR)

        # # 日期变更弹窗（会跳回首页，需要特殊处理）
        # if R.Daily.TextDateChangeDialog.exists():
        #     logger.debug("Scene detected: DATE_CHANGE")
        #     return Scene(SceneType.DATE_CHANGE)
        
        # 第一次技能卡自选引导对话框
        if R.InPurodyuusu.TextSkillCardSelectGuideDialogTitle.exists():
            dialog.yes()
            return Scene(SceneType.IDLE)

        return None

    def _check_dialogs(self) -> Scene | None:
        # 卡片选择
        logger.verbose("Check skill card select...")
        if R.InPurodyuusu.TextSkillCard.exists():
            return Scene(SceneType.SELECT_CARD)
        
        # P道具选择
        logger.verbose("Check PItem select...")
        if R.InPurodyuusu.TextPItem.exists():
            return Scene(SceneType.SELECT_PITEM)

        # P饮料选择
        logger.verbose("Check PDrink select...")
        if R.InPurodyuusu.TextPDrink.exists():
            # HACK: 有一定概率 scene check 会识别到动画未结束状态的对话框
            # 因此这里加一个短暂的延时，确保动画结束
            # TODO: 也许有更好的方法。此时选择饮料的文本提示已存在，选择按钮也存在，
            # 三个饮料的图标似乎是从左到右依次出现的，最后跳过领取的勾选框才加载出来。
            # 如果此时命中，有可能误识别成没有跳过领取的状态
            sleep(0.3)
            device.screenshot()
            return Scene(SceneType.SELECT_DRINK)

    def _check_fullscreen_dialogs(self) -> Scene | None:
        # 技能卡自选强化
        if R.InPurodyuusu.IconTitleSkillCardEnhance.exists():
            return Scene(SceneType.SKILL_CARD_ENHANCE)
        
        # 技能卡自选删除
        if R.InPurodyuusu.IconTitleSkillCardRemoval.exists():
            return Scene(SceneType.SKILL_CARD_REMOVAL)

    def _check_action_like(self) -> Scene | None:
        """判断行动-like场景，右上角展示目标值的场景"""
        if not R.InPurodyuusu.TextReviewCriteria.exists():
            return None
        
        # 行动选择
        if AnyOf[
            R.InPurodyuusu.TextPDiary,
            R.InPurodyuusu.ButtonFinalPracticeVisual
        ].exists():
            return Scene(SceneType.ACTION_SELECT)

        # 授業
        if R.InPurodyuusu.IconTitleStudy.exists():
            buttons = CommuEventButtonUI().all(False, False)
            if len(buttons) > 1:
                return Scene(SceneType.STUDY)
            else:
                return Scene(SceneType.IDLE)
        
        # おでかけ
        if R.InPurodyuusu.TitleIconOuting.exists():
            buttons = CommuEventButtonUI().all(False, False)
            if len(buttons) > 1:
                return Scene(SceneType.OUTING)
            else:
                return Scene(SceneType.IDLE)

        # 相談
        if R.InPurodyuusu.IconTitleConsult.exists():
            return Scene(SceneType.CONSULT)

        # 活動支給
        if R.InPurodyuusu.IconTitleAllowance.exists():
            return Scene(SceneType.ALLOWANCE)
        
        # 培育初始饮料、卡片二选一
        ui = CommuEventButtonUI([ORANGE_RANGE])
        buttons = ui.all(description=False, title=False)
        if len(buttons) > 1:
            # return InitialDrinkOrCardSelectScene(type=SceneType.INITIAL_DRINK_OR_CARD_SELECT, buttons=buttons)
            device.double_click(buttons[0])
            return Scene(SceneType.IDLE)
        
    def _battle_scene(self) -> Scene | None:
        """判断打牌场景"""
        if AnyOf[
            R.InPurodyuusu.TextClearUntil,
            R.InPurodyuusu.TextPerfectUntil,
        ].exists():
            return Scene(SceneType.PRACTICE)
        
        if AnyOf[
            R.InPurodyuusu.TextExamRankSmallFirst,
            R.InPurodyuusu.TextExamRankLargeFirst,
        ].exists():
            return Scene(SceneType.EXAM)

        return None


class Context:
    def __init__(self, page: 'ProducePage', controller: 'ProduceController') -> None:
        self.page = page
        self.controller = controller


class DrinkSelectContext(Context):
    """饮料选择相关"""
    @eval_once
    def fetch_select_drink(self) -> SelectDrinkDialog:
        skip_btn = R.InPurodyuusu.TextDontClaim.find()
        drinks = [Drink(index=i) for i in range(3)]
        return SelectDrinkDialog(
            can_skip=skip_btn is not None,
            drinks=drinks,
            _skip_button=skip_btn,
        )

    def commit(self, data: SelectDrinkDialog, drink: Drink | None):
        """[饮料选择对话框] 提交

        :param drink: 目标饮料下标。None 表示不选择。
        :raises ValueError: _description_
        """
        if drink is None:
            if not data._skip_button:
                raise ValueError("Cannot skip drink selection: skip button not found.")
            data._skip_button.click()
            sleep(0.5)
            AnyOf[
                R.InPurodyuusu.ButtonDontClaim,
                R.InPurodyuusu.AcquireBtnDisabled
            ].try_click()
            logger.debug("Skipped PDrink selection.")
            return
    
        if drink.index < 0 or drink.index >= len(POSTIONS):
            raise ValueError(f"Invalid drink index: {drink.index}")
        device.click(POSTIONS[drink.index])
        sleep(0.5)
        logger.debug(f"PDrink clicked: {POSTIONS[drink.index]}")
        R.InPurodyuusu.AcquireBtnDisabled.wait().click()
        logger.debug("Clicked Acquire button for PDrink.")


class CardSelectContext(Context):
    @eval_once
    def fetch_cards(self):
        cards = AnyOf[
            R.InPurodyuusu.A,
            R.InPurodyuusu.M
        ].find_all()
        cards.sort(key=lambda x: x.rect.top_left)
        logger.info(f"Found {len(cards)} skill cards")
        return cards

    @eval_once
    def fetch_recommend_card(self) -> int | None:
        rec_badges = R.InPurodyuusu.TextRecommend.find_all()
        rec_badges = [card.rect for card in rec_badges]
        cards = self.fetch_cards()
        if rec_badges:
            cards = [card.rect for card in cards]
            matches = badge.match(cards, rec_badges, 'mb')
            logger.debug("Recommend card badge matches: %s", matches)
            for i, match in enumerate(matches):
                if match.badge is not None:
                    return i
            return None
        return None

    def commit(self, index: int):
        cards = self.fetch_cards()
        target = cards[index]
        for _ in Loop():
            device.click(target)
            btn = R.InPurodyuusu.AcquireBtnDisabled.find()
            if btn:
                btn.click()
                sleep(0.5)
                logger.debug(f"Clicked Acquire button for skill card index {index}.")
            else:
                break

class PItemSelectContext(Context):
    """PItem 选择对话框。

    前置：位于 PItem 选择对话框页面 \n
    """

    @eval_once
    def fecth_available_pitems(self) -> list[str]:
        return ['0', '1', '2']  # TODO: HARD CODED

    def commit(self, index: int):
        positions = PITEM_POSTIONS
        if index < 0 or index >= len(positions):
            raise ValueError(f"Invalid PItem index: {index}")
        device.click(positions[index])
        logger.debug(f"PItem clicked: {positions[index]}")
        R.InPurodyuusu.AcquireBtnDisabled.wait().click()
        logger.debug("Clicked Acquire button for PItem.")


class ActionSelectContext(Context):
    """行动页面相关操作"""
    @eval_once
    def is_final_week(self) -> bool:
        return R.InPurodyuusu.ButtonFinalPracticeVisual.exists()

    @eval_once
    def fetch_available_actions(self) -> tuple[list[ProduceAction], list[GameObject]]:
        """读取当前可用的行动"""
        if self.is_final_week():
            # 冲刺周只有 Da Vi Vo 三种行动
            return [
                ProduceAction.DANCE,
                ProduceAction.VOCAL,
                ProduceAction.VISUAL,
            ], [
                R.InPurodyuusu.ButtonFinalPracticeDance.require(threshold=0.6),
                R.InPurodyuusu.ButtonFinalPracticeVocal.require(threshold=0.6),
                R.InPurodyuusu.ButtonFinalPracticeVisual.require(threshold=0.6),
            ]
        else:
            # 否则逐个检测
            # 非课程
            actions = [
                (R.InPurodyuusu.Rest, ProduceAction.REST),

                (R.InPurodyuusu.ButtonIconOuting, ProduceAction.OUTING),
                (R.InPurodyuusu.ButtonIconStudy, ProduceAction.STUDY),
                (R.InPurodyuusu.ButtonTextAllowance, ProduceAction.ALLOWANCE),
                (R.InPurodyuusu.ButtonIconConsult, ProduceAction.CONSULT),
            ]
            buttons: list[GameObject] = []
            result: list[ProduceAction] = []
            for btn, action in actions:
                if obj := btn.find():
                    result.append(action)
                    buttons.append(obj)
            
            # 课程与 SP 课程的处理
            # 三个课程一定都有或都没有
            vo = R.InPurodyuusu.ButtonPracticeVocal.find()
            if vo is not None:
                vo_sp = da_sp = vi_sp = False
                da = R.InPurodyuusu.ButtonPracticeDance.require()
                vi = R.InPurodyuusu.ButtonPracticeVisual.require()
                sp_list = R.InPurodyuusu.IconSp.find_all()
                for cur_sp in sp_list:
                    if cur_sp.rect.center[0] < vo.rect.center[0]:
                        vo_sp = True
                    if vo.rect.center[0] < cur_sp.rect.center[0] < da.rect.center[0]:
                        da_sp = True
                    if da.rect.center[0] < cur_sp.rect.center[0] < vi.rect.center[0]:
                        vi_sp = True
                
                buttons.extend([da, vo, vi])
                result.append(ProduceAction.DANCE_SP if da_sp else ProduceAction.DANCE)
                result.append(ProduceAction.VOCAL_SP if vo_sp else ProduceAction.VOCAL)
                result.append(ProduceAction.VISUAL_SP if vi_sp else ProduceAction.VISUAL)
            return result, buttons
        
    @eval_once
    def fetch_sensei_tip(self) -> ProduceAction | None:
        """读取老师推荐的行动"""
        if not R.InPurodyuusu.IconAsariSenseiAvatar.exists():
            return None

        cd = Countdown(sec=5).start()
        result = None
        for _ in Loop():
            if cd.expired():
                break
            logger.debug('Retrieving recommended lesson...')
            with cropped(device, y1=0.00, y2=0.30):
                if result := AnyOf[
                    R.InPurodyuusu.TextSenseiTipDance,
                    R.InPurodyuusu.TextSenseiTipVocal,
                    R.InPurodyuusu.TextSenseiTipVisual,
                    R.InPurodyuusu.TextSenseiTipRest,
                    R.InPurodyuusu.TextSenseiTipConsult,
                ].find():
                    break
    
        logger.debug("image.find_multi: %s", result)
        if result is None:
            logger.debug("No recommended lesson found")
            return None
        
        result = result.prefab
        if result == R.InPurodyuusu.TextSenseiTipDance:
            return ProduceAction.DANCE
        elif result == R.InPurodyuusu.TextSenseiTipVocal:
            return ProduceAction.VOCAL
        elif result == R.InPurodyuusu.TextSenseiTipVisual:
            return ProduceAction.VISUAL
        elif result == R.InPurodyuusu.TextSenseiTipRest:
            return ProduceAction.REST
        elif result == R.InPurodyuusu.TextSenseiTipConsult:
            return ProduceAction.CONSULT
        else:
            raise ValueError("Unrecognized sensei tip action.")

    def _read_number(self, box: Rect) -> int:
        all_number = ocr.ocr(rect=box)
        all_number = all_number.squash().numbers()
        if all_number:
            try:
                return int(all_number[0])
            except Exception:
                return 0
        return 0

    @eval_once
    def fetch_perf_metrics(self) -> list[PerformanceMetricsVal]:
        cur_vo = self._read_number(R.InPurodyuusu.CurVoValue)
        cur_da = self._read_number(R.InPurodyuusu.CurDaValue)
        cur_vi = self._read_number(R.InPurodyuusu.CurViValue)
        max_val = self._read_number(R.InPurodyuusu.MaxDaValue)

        return [
            PerformanceMetricsVal(current=cur_vi, max=max_val, lesson=ProduceAction.VISUAL),
            PerformanceMetricsVal(current=cur_da, max=max_val, lesson=ProduceAction.DANCE),
            PerformanceMetricsVal(current=cur_vo, max=max_val, lesson=ProduceAction.VOCAL),
        ]
    
    def has_sp_lesson(self) -> bool:
        actions = self.fetch_available_actions()[0]
        return (
            ProduceAction.VISUAL_SP in actions or
            ProduceAction.VOCAL_SP in actions or
            ProduceAction.DANCE_SP in actions
        )

    def commit(self, action: 'ProduceAction'):
        _actions = self.fetch_available_actions()
        # 首先判断 action 是否可用
        # 对于课程的特判
        available = True
        if action == ProduceAction.VISUAL and ProduceAction.VISUAL_SP in _actions[0]:
            action = ProduceAction.VISUAL_SP
            logger.debug('Using VISUAL_SP instead of VISUAL.')
        elif action == ProduceAction.VOCAL and ProduceAction.VOCAL_SP in _actions[0]:
            action = ProduceAction.VOCAL_SP
            logger.debug('Using VOCAL_SP instead of VOCAL.')
        elif action == ProduceAction.DANCE and ProduceAction.DANCE_SP in _actions[0]:
            action = ProduceAction.DANCE_SP
            logger.debug('Using DANCE_SP instead of DANCE.')
        # 其他
        available = action in _actions[0]
        if not available:
            raise ValueError(f"Action {action} is not available now.")
        
        index = _actions[0].index(action)
        button = _actions[1][index]

        if button.prefab in [
            R.InPurodyuusu.ButtonIconOuting,
            R.InPurodyuusu.ButtonIconStudy,
            R.InPurodyuusu.ButtonTextAllowance,
            R.InPurodyuusu.ButtonIconConsult,

            R.InPurodyuusu.ButtonFinalPracticeDance,
            R.InPurodyuusu.ButtonFinalPracticeVocal,
            R.InPurodyuusu.ButtonFinalPracticeVisual,
            R.InPurodyuusu.TextActionVisual,
            R.InPurodyuusu.TextActionVocal,
            R.InPurodyuusu.TextActionDance,
            R.InPurodyuusu.ButtonPracticeDance,
            R.InPurodyuusu.ButtonPracticeVocal,
            R.InPurodyuusu.ButtonPracticeVisual,
        ]:
            for _ in range(3):
                button.click()
                sleep(0.3)
            
            sleep(2)
            logger.info(f"Entered action: {action}")
            self.controller.wait_disappear(button.prefab)
        else: # rest
            # 先等按钮出现
            # 点击休息直到确认对话框出现
            # TODO: 需要一种方法简化这种 pattern
            for _ in Loop():
                if R.InPurodyuusu.Rest.try_click():
                    sleep(0.5)
                elif R.InPurodyuusu.RestConfirmBtn.exists():
                    break
            # 然后等消失
            for _ in Loop():
                if R.InPurodyuusu.RestConfirmBtn.exists():
                    device.click()
                    sleep(0.5)
                else:
                    break



class PracticeContext(Context):
    def fetch_card_count(self) -> int:
        raise NotImplementedError
        img = device.screenshot()
        return skill_card_count(img)
    
    def fetch_recommend_card(self, threshold_predicate: Callable[[int, CardDetectResult], bool]):
        raise NotImplementedError
        img = device.screenshot()
        return detect_recommended_card(self.fetch_card_count(), threshold_predicate, img=img)

class ExamContext(Context):
    def is_final_exam(self) -> bool:
        img = device.screenshot()
        roi = R.InPurodyuusu.BoxDetectExamType
        roi_img = img[roi.y1:roi.y2, roi.x1:roi.x2]
        # L: 亮度, a: 绿-红, b: 蓝-黄
        cv2.imshow('roi', roi_img)
        cv2.waitKey(1)
        lab = cv2.cvtColor(roi_img, cv2.COLOR_BGR2Lab)
        _, a, b = cv2.split(lab)
        # 3. 计算 b 通道（黄蓝色轴）和 a 通道（红绿色轴）的平均值
        avg_b = np.mean(b)
        avg_a = np.mean(a)
        
        is_final = avg_b > 145 or (avg_b > 138 and avg_a > 135)
        if is_final:
            return True
        else:
            return False


class StudyContext(Context):
    @eval_once
    def is_self_study(self) -> bool:
        """是否为自习课"""
        # [kotonebot-resource\sprites\jp\in_purodyuusu\screenshot_study_self_study.png]
        return AnyOf[
            R.InPurodyuusu.TextSelfStudyDance,
            R.InPurodyuusu.TextSelfStudyVisual,
            R.InPurodyuusu.TextSelfStudyVocal
        ].exists()
    
    @eval_once
    def fetch_options(self):
        ui = CommuEventButtonUI()
        buttons = ui.all()
        if not buttons:
            raise UnrecoverableError("Failed to find any buttons.")
        return buttons
    
    def commit_self_study(self, lesson: Literal['dance', 'visual', 'vocal']):
        """执行自习课行动"""
        match lesson:
            case 'dance':
                R.InPurodyuusu.TextSelfStudyDance.wait().double_click()
            case 'visual':
                R.InPurodyuusu.TextSelfStudyVisual.wait().double_click()
            case 'vocal':
                R.InPurodyuusu.TextSelfStudyVocal.wait().double_click()
            case _:
                raise ValueError(f"Invalid self study subject: {lesson}")

    def commit(self, index: int):
        """执行非自习课内容"""
        buttons = self.fetch_options()
        target_btn = buttons[index]
        if target_btn.selected:
            device.click(target_btn)
        else:
            device.double_click(target_btn)
        sleep(2)
    

class OutingContext(Context):
    @eval_once
    def fetch_options(self):
        ui = CommuEventButtonUI()
        buttons = ui.all()
        return buttons

    def commit(self, index: int):
        buttons = self.fetch_options()
        if index < 0 or index >= len(buttons):
            raise ValueError(f"Invalid outing option index: {index}")
        target_btn = buttons[index]
        logger.debug('Clicking "%s".', target_btn.description)
        if target_btn.selected:
            device.click(target_btn)
        else:
            device.double_click(target_btn)
        sleep(2)
        

        # pi = ProduceInterrupt()
        # for _ in Loop():
        #     if AnyOf[
        #         R.InPurodyuusu.TextPDiary,
        #         R.InPurodyuusu.ButtonFinalPracticeDance,
        #     ].exists():
        #         break
        #     if pi.handle():
        #         continue
        #     if R.Common.ButtonSelect2.try_click():
        #         logger.info("AP max out dialog found. Clicked continue button.")
        #         sleep(0.1)

class _ConsultFlow(Flow):
    def __init__(self, controller: 'ProduceController') -> None:
        # start           -> 首次点击第一个条目，进入等待购买阶段
        # waiting_purchase-> 等待购买确认（对话框/按钮）
        # waiting_exit    -> 已点击结束按钮，等待退出完成
        self.contoller = controller
        self._phase: str = "start"
        self._wait_purchase_cd = Countdown(sec=5)
        self._exit_cd = Countdown(sec=5)
        self._purchase_clicked: bool = False
        self._purchase_confirmed: bool = False

    def step(self, scene: 'Scene') -> bool:
        """执行一次相談流程的单步。

        返回值:
        - True: 本次相談流程已结束；
        - False: 仍需在后续 tick 中继续执行。
        """
        # Phase: start
        if self._phase == "start":
            device.click(R.InPurodyuusu.PointConsultFirstItem)
            sleep(0.3)
            self._wait_purchase_cd.start()
            self._phase = "waiting_purchase"
            return False

        # Phase: waiting_purchase
        elif self._phase == "waiting_purchase":
            if self._wait_purchase_cd.expired():
                self._purchase_confirmed = True

            # 购买确认对话框
            if dialog.yes():
                # 第一次 yes：认为购买完成
                if self._purchase_clicked:
                    self._purchase_confirmed = True
                return False

            # 点击购买按钮
            if R.InPurodyuusu.ButtonIconExchange(enabled=True).try_click():
                self._purchase_clicked = True
                return False

            # 购买已确认，尝试点击结束咨询
            if self._purchase_confirmed and R.InPurodyuusu.ButtonEndConsult.try_click():
                self._exit_cd.start()
                self._phase = "waiting_exit"
                return False

            # 仍未确认购买，重复点击第一个条目以触发对话框
            if not self._purchase_confirmed:
                device.click(R.InPurodyuusu.PointConsultFirstItem)
                self._wait_purchase_cd.start()
            return False

        # Phase: waiting_exit
        elif self._phase == "waiting_exit":
            # 若再次出现确认对话框，继续点 yes
            if dialog.yes():
                return False

            if not self._exit_cd.started:
                self._exit_cd.start()
                return False

            if self._exit_cd.expired():
                return True

            return False
        # 未知 phase，防御性结束
        else:
            return True

class ConsultContext(Context):
    def commit(self):
        flow = _ConsultFlow(self.controller)
        self.controller._flow = flow
        flow.step(Scene(SceneType.CONSULT))


class AllowanceContext(Context):
    def claim(self):
        if R.InPurodyuusu.LootboxSliverLock.try_click():
            sleep(1)
        skip()


class PDrinkMaxContext(Context):
    """P饮料到达上限弹窗上下文"""
    pass


class PDrinkMaxConfirmContext(Context):
    """P饮料到达上限确认弹窗上下文"""
    pass


class NetworkErrorContext(Context):
    """网络错误弹窗上下文"""
    pass


class DateChangeContext(Context):
    """日期变更弹窗上下文"""
    pass


class SkillFullScreenDialogContext(Context):
    def __init__(self, page: 'ProducePage', controller: 'ProduceController', confirm_btn: type[Prefab[Any]]) -> None:
        super().__init__(page, controller)
        self.confirm_btn = confirm_btn

    @eval_once
    def fetch_cards(self):
        # TODO: 这里目前只处理了第一个，后续需要扩展为搜索所有
        return [AnyOf[
            R.InPurodyuusu.A,
            R.InPurodyuusu.M
        ].require()]

    def commit(self, index: int):
        cards = self.fetch_cards()
        cards[0].click()
        self.confirm_btn.wait().click()
        sleep(1)


class SkillCardEnhanceContext(SkillFullScreenDialogContext):
    def __init__(self, page: 'ProducePage', controller: 'ProduceController') -> None:
        super().__init__(page, controller, R.InPurodyuusu.ButtonEnhance(enabled=True))

    @eval_once
    def fetch_required_count(self) -> int:
        """读入需要选择的卡片张数"""
        raise NotImplementedError

    def commit(self, index: int = 0):
        """遍历多张卡，尝试点击每张卡并点强化按钮，直到成功为止。"""
        if index != 0:
            raise NotImplementedError("SkillCardEnhanceContext.commit only supports index=0 for now.")
        cards = self.fetch_cards()
        if not cards:
            logger.info("No skill cards found for enhance")
            return

        # 从右侧开始尝试（反序）
        for card in reversed(cards):
            device.click(card)
            sleep(0.5)
            device.screenshot()
            if R.InPurodyuusu.ButtonEnhance(enabled=True).try_click(threshold=0.7):
                sleep(0.5)
                logger.debug("Enhance button clicked for a card.")
                break
        logger.debug("Handle skill card enhance finished.")


class SkillCardRemovalContext(SkillFullScreenDialogContext):
    def __init__(self, page: 'ProducePage', controller: 'ProduceController') -> None:
        super().__init__(page, controller, R.InPurodyuusu.ButtonRemove)

    def commit(self, index: int = 0):
        if index != 0:
            raise NotImplementedError("SkillCardRemovalContext.commit only supports index=0 for now.")
        cards = self.fetch_cards()
        if not cards:
            logger.info("No skill cards found for removal")
            return

        if index < 0 or index >= len(cards):
            target = cards[0]
        else:
            target = cards[index]

        device.click(target)
        for _ in Loop():
            if R.InPurodyuusu.ButtonRemove.try_click():
                logger.debug("Remove button clicked.")
                break
        logger.debug("Handle skill card removal finished.")


class ProducePage(
        _SceneCheckMixin,
    ):
    def __init__(self) -> None:
        pass

if __name__ == '__main__':
    from kotonebot.backend.debug.mock import MockDevice
    from kotonebot.backend.context.context import init_context, manual_context
    # d = MockDevice()
    # d.load_image(r'E:\GithubRepos\KotonesAutoAssistant\dump_tmp\1766923332.9383092-EXAM.png')
    # d.load_image(r'b.png')
    # init_context(target_device=d, force=True)
    # with manual_context():
    #     ret = AnyOf[
    #         R.InPurodyuusu.TextExamRankSmallFirst,
    #         R.InPurodyuusu.TextExamRankLargeFirst,
    #     ].find()
    #     # print(ret)
    # import cv2
    # from kotonebot.backend.image import find
    # img = cv2.imread(r'b.png')
    # assert img is not None
    # print(find(img, R.InPurodyuusu.TextExamRankLargeFirst.template, threshold=0))
    # print(find(img, R.InPurodyuusu.TextExamRankLargeFirst.template, threshold=0, rect=R.InPurodyuusu.TextExamRankLargeFirst.template.slice_rect))
    ctx = ExamContext(ProducePage(), None)
    
    
    while True:
        (ctx.is_final_exam())
    
    # accumulator for masks (float32, stores summed normalized mask values)
    acc: np.ndarray | None = None
    # per-frame decay (0.0 = no decay). 可按需调整或暴露为参数
    DECAY_PER_FRAME = 0.0

    while True:
        img = device.screenshot()

        # HSV，只取黄色
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_yellow = np.array([14, 60, 60])
        upper_yellow = np.array([40, 255, 255])
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # 初始化累加器（与 mask 同形状，float32）
        if acc is None:
            acc = np.zeros_like(mask, dtype=np.float32)

        # 将 mask 归一化到 0..1 后累加
        acc += (mask.astype(np.float32) / 255.0)

        # 可选的指数衰减，防止长期累加完全饱和
        if DECAY_PER_FRAME > 0.0:
            acc *= (1.0 - DECAY_PER_FRAME)

        # 为显示做归一化：按当前最大值缩放到 0..255 保持对比度
        maxv = float(acc.max()) if acc is not None else 0.0
        if maxv > 0.0:
            disp = np.clip((acc / maxv) * 255.0, 0, 255).astype(np.uint8)
        else:
            disp = np.zeros_like(mask, dtype=np.uint8)

        # 为了更直观，用伪彩（jet）渲染累加结果
        disp_color = cv2.applyColorMap(disp, cv2.COLORMAP_JET)

        # 展示原始单帧 mask 与叠加结果
        cv2.imshow('mask', cv2.resize(mask, None, fx=0.5, fy=0.5))
        cv2.imshow('accum', cv2.resize(disp_color, None, fx=0.5, fy=0.5))

        # 键盘控制：q 退出，r 重置累加，s 保存当前叠加图
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            if acc is not None:
                acc.fill(0)
                logger.info('Accumulator reset')
        elif key == ord('s'):
            # 保存为 PNG（伪彩）
            cv2.imwrite('accum.png', disp_color)
            logger.info('Saved accumulated image to accum.png')