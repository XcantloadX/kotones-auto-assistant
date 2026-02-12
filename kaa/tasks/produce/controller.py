from typing import Callable
from typing_extensions import assert_never

from kaa.tasks.produce.common import ProduceInterrupt
from kotonebot import logging, Loop, action, sleep, device, Countdown

from .page import (
    ActionSelectContext, DrinkSelectContext, ProducePage,
    PracticeContext, ExamContext, CardSelectContext, PItemSelectContext,
    StudyContext, OutingContext, ConsultContext, AllowanceContext,
    SkillCardEnhanceContext, SkillCardRemovalContext,
    PDrinkMaxContext, PDrinkMaxConfirmContext, NetworkErrorContext, DateChangeContext,
    Flow
)
from kaa.tasks.common import skip
from .consts import Scene, SceneType
from .strategy import StandardStrategy

logger = logging.getLogger(__name__)


class ProduceController:
    def __init__(self, *, mode: str) -> None:
        self.page = ProducePage()
        self.strategy = StandardStrategy(self)
        self.running: bool = True
        self._last_scene: Scene | None = None
        self._flow: Flow | None = None
        self._interrupt_depth: int = 0

    def abort(self) -> None:
        logger.info("Aborting the produce session.")
        self.running = False

    def __iter__(self):
        self.running = True
        return self

    def __next__(self):
        self._update()
        return self
    
    def _update(self):
        scene = self.page.check_scene()
        if not scene:
            scene = Scene(SceneType.UNKNOWN)

        # logger.debug(f"Current scene: {scene}")
        # if scene != SceneType.UNKNOWN:
        #     timestamp = time.time()
        #     file_name = f'dump_tmp/{timestamp}-{scene.type.name}.png'
        #     assert l.screenshot is not None
        #     import os
        #     os.makedirs('dump_tmp', exist_ok=True)
        #     cv2.imwrite(file_name, l.screenshot)
        
        self._dispatch(scene, self._last_scene)
        self._last_scene = scene

    @action('执行培育循环', screenshot_mode='manual')
    def run(self):
        for _ in Loop():
            if not self.running:
                logger.info("Produce session exiting.")
                break
            self._update()

    def wait_disappear(self, prefab: type, timeout_sec: float = 10.0) -> None:
        """等待指定 Prefab 消失，同时在等待期间同步处理各类中断弹窗。

        这是一个同步阻塞循环（不会调用主 dispatch），用于替代旧的 ProduceInterrupt.resolve 模式。
        """
        self.pump_interrupts_until(lambda: not prefab.exists(), timeout=timeout_sec)

    def _handle_interrupts(self, scene: Scene) -> bool:
        """统一的 interrupt/dialog 处理入口，供 controller 的 pump 调用。

        返回值表示本轮是否执行了任何 UI 操作/处理（用于决定是否继续快速循环）。
        """
        match scene.type:
            case SceneType.LOADING:
                # 加载中无需点击，但认为“已处理”，继续循环等待
                sleep(0.2)
                return True
            case SceneType.PDRINK_MAX:
                self.strategy.on_pdrink_max(PDrinkMaxContext(self.page, self))
                return True
            case SceneType.PDRINK_MAX_CONFIRM:
                self.strategy.on_pdrink_max_confirm(PDrinkMaxConfirmContext(self.page, self))
                return True
            case SceneType.SELECT_DRINK:
                self.strategy.on_select_drink(DrinkSelectContext(self.page, self))
                return True
            case SceneType.SELECT_CARD:
                self.strategy.on_select_card(CardSelectContext(self.page, self))
                return True
            case SceneType.SELECT_PITEM:
                self.strategy.on_select_pitem(PItemSelectContext(self.page, self))
                return True
            case SceneType.SKILL_CARD_ENHANCE:
                self.strategy.on_skill_card_enhance(SkillCardEnhanceContext(self.page, self))
                return True
            case SceneType.SKILL_CARD_REMOVAL:
                self.strategy.on_skill_card_removal(SkillCardRemovalContext(self.page, self))
                return True
            case _:
                return False

    def pump_interrupts_until(
        self,
        done: Callable[[], bool],
        *,
        timeout: float = 10.0,
        interval: float = 0.2,
    ) -> None:
        """同步循环处理所有 interrupt/dialog 场景，直到 done() 成立。

        设计目标：
        - 用于在处理某个弹窗时，继续“像以前一样循环处理其他弹窗”。
        - 绝不调用 ProduceController.run/_update/_dispatch，因此不会递归。
        - 只处理 interrupt/dialog 类场景（包含 SELECT_DRINK/SELECT_CARD/SELECT_PITEM 等）。
        """
        self._interrupt_depth += 1
        try:
            cd = Countdown(sec=timeout).start()
            for _ in Loop():
                if cd.expired():
                    raise TimeoutError("Timeout waiting condition in pump_interrupts_until")

                img = device.screenshot()
                if done():
                    return
                scene = self.page.check_interrupt_scene()

                handled = False
                if scene is not None:
                    handled = self._handle_interrupts(scene)
                if not handled:
                    handled = ProduceInterrupt._check_skip_commu(img)

                if not handled:
                    sleep(interval)
        finally:
            self._interrupt_depth -= 1


    def _dispatch(self, scene: 'Scene', last_scene: 'Scene | None'):
        # PRACTICE 退出通知
        if last_scene and last_scene.type == SceneType.PRACTICE and scene.type != SceneType.PRACTICE:
            logger.info("Exited practice battle scene.")
            self.strategy.on_practice_exited()
            return

        # 先处理全局中断/弹窗类场景（与 pump 使用同一入口，避免逻辑分叉）
        if self._handle_interrupts(scene):
            return

        # 若存在正在运行的 Flow，则优先推进它
        if self._flow is not None:
            done = self._flow.step(scene)
            if done:
                logger.debug("Flow %s completed.", type(self._flow).__name__)
                self._flow = None
            return

        # 否则按当前场景分发
        match scene.type:
            case SceneType.ACTION_SELECT:
                ctx = ActionSelectContext(self.page, self)
                self.strategy.on_action_select(ctx)
            case SceneType.PRACTICE:
                ctx = PracticeContext(self.page, self)
                if not last_scene or last_scene.type != SceneType.PRACTICE:
                    logger.info("Entered practice battle scene.")
                    self.strategy.on_practice_entered(ctx)
                else:
                    self.strategy.on_practice_tick(ctx)
            case SceneType.EXAM:
                ctx = ExamContext(self.page, self)
                if not last_scene or last_scene.type != SceneType.EXAM:
                    logger.info("Entered exam battle scene.")
                    self.strategy.on_exam_entered(ctx)
                self.strategy.on_exam(ctx)
            case SceneType.STUDY:
                ctx = StudyContext(self.page, self)
                self.strategy.on_study(ctx)
            case SceneType.OUTING:
                ctx = OutingContext(self.page, self)
                self.strategy.on_outing(ctx)
            case SceneType.CONSULT:
                ctx = ConsultContext(self.page, self)
                self.strategy.on_consult(ctx)
            case SceneType.ALLOWANCE:
                ctx = AllowanceContext(self.page, self)
                self.strategy.on_allowance(ctx)
            case SceneType.IDLE:
                skip()
                logger.info("Idle state. Doing nothing.")
            case SceneType.UNKNOWN:
                skip()
                logger.debug(f"Unknown scene: {scene}")
            case SceneType.INITIAL_DRINK_OR_CARD_SELECT:
                # TODO: 此类型目前在 page.py 中处理掉了，后续需要移动到 strategy 中
                pass
            case (
                SceneType.LOADING | SceneType.PDRINK_MAX | SceneType.PDRINK_MAX_CONFIRM | 
                SceneType.SELECT_DRINK | SceneType.SELECT_CARD | SceneType.SELECT_PITEM | 
                SceneType.SKILL_CARD_ENHANCE | SceneType.SKILL_CARD_REMOVAL
            ):
                # 这些类型应由 interrupt 处理逻辑捕获，不应到达这里
                raise RuntimeError(f"Interrupt scene {scene.type} reached main dispatch unexpectedly.")
            case _:
                skip()
                assert_never(scene.type)
        

    
if __name__ == '__main__':
    c = ProduceController(mode='')
    c.run()