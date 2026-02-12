import logging
from dataclasses import dataclass

from cv2.typing import MatLike

from kotonebot.primitives import Rect
from kotonebot import ocr, device, image, action
from kotonebot.core import AnyOf
from kotonebot.backend.core import HintBox
from kaa.config import ProduceAction
from kaa.tasks import R

logger = logging.getLogger(__name__)

# 三属性的当前值与最大值读取范围
CurVoValue = HintBox(x1=185, y1=680, x2=285, y2=720, source_resolution=(720, 1280))
CurDaValue = HintBox(x1=330, y1=680, x2=430, y2=720, source_resolution=(720, 1280))
CurViValue = HintBox(x1=475, y1=680, x2=575, y2=720, source_resolution=(720, 1280))
MaxDaValue = HintBox(x1=285, y1=720, x2=430, y2=750, source_resolution=(720, 1280))


@dataclass
class Lesson:
    """
    :param rect: 课程位置
    :param sp: 是否为 SP 课程
    :param act: 课程类型
    :param cur_attr_value: 课程属性的当前值
    :param max_attr_value: 课程属性的最大值
    """
    rect: Rect
    sp: bool
    act: ProduceAction
    cur_attr_value: int
    max_attr_value: int


class Schedule:
    def __init__(self):
        """
        初始化日程表
        这里本来想传入本次培育中的全局信息，比如 难度，偶像信息，各个课程sp率
        这些信息在整局培育中是相同的
        """
        pass

    @action('检测日程是否有课程', screenshot_mode='manual-inherit')
    def have_lesson(self) -> bool:
        """
        判断是否有课程，依据是课程的名字的图片
        TODO: NIA 课程的名字的图片没放到这里，后续若要支持NIA需要添加对应的图片
        """
        device.screenshot()
        result = AnyOf[
            R.InPurodyuusu.TextActionVocal,
            R.InPurodyuusu.TextActionDance,
            R.InPurodyuusu.TextActionVisual,
        ].find()
        return result is not None

    @action('识别日程，课程抉择，', screenshot_mode='manual-inherit')
    def select_lesson(self) -> Lesson:
        """
        选择课程，根据推荐、属性进行抉择
        :return: 课程
        """
        recommended = self.read_sensei_recommended()
        lesson_data = self.read_lesson_data()
        sp_lessons, nor_lessons = [], []
        for l in lesson_data:
            sp_lessons.append(l) if l.sp else nor_lessons.append(l)
        have_sp = len(sp_lessons) > 0
        for lesson in lesson_data:
            if lesson.act == recommended and lesson.sp == have_sp:
                logger.info(f'Recommended: {lesson}')
                return lesson

        # TODO: 各个课程的属性上限需要根据难度+偶像属性要求进行调整，之后再根据此上限选择课程.目前设置上限为 attr_limit_ratio
        cal_lesson = None
        attr_limit_ratio = 0.8
        if sp_lessons:
            lesson = min(sp_lessons, key=lambda x: x.cur_attr_value)
            if lesson.cur_attr_value < lesson.max_attr_value * attr_limit_ratio:
                cal_lesson = lesson
        if cal_lesson is None and nor_lessons:
            cal_lesson = min(nor_lessons, key=lambda x: x.cur_attr_value)
        if cal_lesson is None:
            logger.warning('Lesson calculate error, select vocal')
            return lesson_data[0]
        logger.info(f'Recommended is not sp, calculate result:  {cal_lesson}')
        return cal_lesson

    @action('读取日程中课程数据', screenshot_mode='manual-inherit')
    def read_lesson_data(self) -> list[Lesson]:
        """
        读取当前课程数据，包括位置，是否为sp，当前属性对应数值和最大值
        :return: 课程数据列表
        """
        img = device.screenshot()
        sp_list = R.InPurodyuusu.IconSp.find_all()
        vo_sp = da_sp = vi_sp = False
        # 等待课程按钮模板出现，使用 rect.center[0] 作为水平位置比较
        vo = R.InPurodyuusu.ButtonPracticeVocal.wait()
        da = R.InPurodyuusu.ButtonPracticeDance.wait()
        vi = R.InPurodyuusu.ButtonPracticeVisual.wait()
        for cur_sp in sp_list:
            if cur_sp.rect.center[0] < vo.rect.center[0]:
                vo_sp = True
            elif vo.rect.center[0] < cur_sp.rect.center[0] < da.rect.center[0]:
                da_sp = True
            elif da.rect.center[0] < cur_sp.rect.center[0] < vi.rect.center[0]:
                vi_sp = True
        max_value = self.read_number(img, MaxDaValue)
        lesson_data = [
            Lesson(vo.rect, vo_sp, ProduceAction.VOCAL, self.read_number(img, CurVoValue), max_value),
            Lesson(da.rect, da_sp, ProduceAction.DANCE, self.read_number(img, CurDaValue), max_value),
            Lesson(vi.rect, vi_sp, ProduceAction.VISUAL, self.read_number(img, CurViValue), max_value),
        ]
        for lesson in lesson_data:
            logger.info(f'Lesson: {lesson}')
        return lesson_data

    @action('读取日程中老师的推荐行动', screenshot_mode='manual-inherit')
    def read_sensei_recommended(self) -> ProduceAction:
        """
        读取老师的推荐行动
        :return: 当前推荐行动，如果没推荐行动，返回 RECOMMENDED
        """
        device.screenshot()
        if R.InPurodyuusu.IconAsariSenseiAvatar.exists():
            logger.debug('Retrieving recommended lesson...')
            result = AnyOf[
                R.InPurodyuusu.TextSenseiTipVocal,
                R.InPurodyuusu.TextSenseiTipDance,
                R.InPurodyuusu.TextSenseiTipVisual,
                R.InPurodyuusu.TextSenseiTipRest,
                R.InPurodyuusu.TextSenseiTipConsult,
            ].find()
            if result:
                if result.prefab == R.InPurodyuusu.TextSenseiTipVocal:
                    return ProduceAction.VOCAL
                if result.prefab == R.InPurodyuusu.TextSenseiTipDance:
                    return ProduceAction.DANCE
                if result.prefab == R.InPurodyuusu.TextSenseiTipVisual:
                    return ProduceAction.VISUAL
                if result.prefab == R.InPurodyuusu.TextSenseiTipRest:
                    return ProduceAction.REST
                if result.prefab == R.InPurodyuusu.TextSenseiTipConsult:
                    return ProduceAction.CONSULT
        return ProduceAction.RECOMMENDED

    def read_number(self, img: MatLike, box: HintBox) -> int:
        """
        :param img: MatLike 图像
        :param box: HintBox 需要读取数值的范围
        :return: int 数值，读取失败返回0
        """
        all_number = ocr.raw().ocr(img, rect=box)
        all_number = all_number.squash().numbers()
        if all_number:
            return int(all_number[0])
        else:
            return 0
