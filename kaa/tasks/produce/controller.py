from typing_extensions import assert_never

from kotonebot import logging, Loop, action, sleep

from .page import (
    ActionSelectContext, DrinkSelectContext, ProducePage,
    PracticeContext, ExamContext, CardSelectContext, PItemSelectContext,
    StudyContext, OutingContext, ConsultContext, AllowanceContext,
    SkillCardEnhanceContext, SkillCardRemovalContext,
    PDrinkMaxContext, PDrinkMaxConfirmContext, NetworkErrorContext, DateChangeContext,
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
        for l in Loop():
            if not self.running:
                logger.info("Produce session exiting.")
                break
            self._update()


    def _dispatch(self, scene: 'Scene', last_scene: 'Scene | None'):
        if last_scene and last_scene.type == SceneType.PRACTICE and scene.type != SceneType.PRACTICE:
            logger.info("Exited practice battle scene.")
            self.strategy.on_practice_exited()
        
        match scene.type:
            case SceneType.LOADING:
                logger.info("Loading...")
            case SceneType.PDRINK_MAX:
                ctx = PDrinkMaxContext(self.page, self)
                self.strategy.on_pdrink_max(ctx)
            case SceneType.PDRINK_MAX_CONFIRM:
                ctx = PDrinkMaxConfirmContext(self.page, self)
                self.strategy.on_pdrink_max_confirm(ctx)
            case SceneType.NETWORK_ERROR:
                ctx = NetworkErrorContext(self.page, self)
                self.strategy.on_network_error(ctx)
            case SceneType.DATE_CHANGE:
                ctx = DateChangeContext(self.page, self)
                self.strategy.on_date_change(ctx)
            case SceneType.SELECT_DRINK:
                ctx = DrinkSelectContext(self.page, self)
                sleep(0.3)
                self.strategy.on_select_drink(ctx)
            case SceneType.SELECT_CARD:
                ctx = CardSelectContext(self.page, self)
                self.strategy.on_select_card(ctx)
            case SceneType.SELECT_PITEM:
                ctx = PItemSelectContext(self.page, self)
                self.strategy.on_select_pitem(ctx)
            case SceneType.SKILL_CARD_ENHANCE:
                ctx = SkillCardEnhanceContext(self.page, self)
                self.strategy.on_skill_card_enhance(ctx)
            case SceneType.SKILL_CARD_REMOVAL:
                ctx = SkillCardRemovalContext(self.page, self)
                self.strategy.on_skill_card_removal(ctx)
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
            case _:
                skip()
                assert_never(scene.type)
        

    
if __name__ == '__main__':
    c = ProduceController(mode='')
    c.run()