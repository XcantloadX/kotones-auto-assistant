from kotonebot import device, logging, Loop, sleep, ocr
from kotonebot.errors import UnrecoverableError

from kaa.tasks import R
from kaa.game_ui import dialog
from kaa.kaa_context import produce_solution
from kaa.errors import IdolCardNotFoundError
from kaa.game_ui.idols_overview import locate_idol, match_idol

logger = logging.getLogger(__name__)


def _select_idol(skin_id: str):
    """
    选择目标P偶像

    前置条件：偶像选择页面 1.アイドル選択\n
    结束状态：偶像选择页面 1.アイドル選択\n
    """
    logger.info("Find and select idol: %s", skin_id)
    # 进入总览
    device.screenshot()
    for _ in Loop():
        # 到达偶像选择页面
        if R.Produce.IdolOverview.ButtonConfirm.exists():
            break
        # 尝试点击 总览
        elif not R.Common.ButtonConfirmNoIcon.exists():
            R.Produce.ButtonPIdolOverview.try_click()
            sleep(1)
        # 有新的 アナザー 偶像提示弹窗
        elif R.Produce.TextAnotherIdolAvailableDialog.exists():
            dialog.no(msg='Closed another idol available dialog.')
    # 选择偶像
    pos = locate_idol(skin_id)
    if pos is None:
        raise IdolCardNotFoundError(skin_id)
    # 确认
    for _ in Loop():
        if btn_confirm := R.Common.ButtonConfirmNoIcon.find():
            device.click(pos)
            sleep(0.3)
            btn_confirm.click()
        if R.Produce.TextStepIndicator1.exists():
            break


def _select_set(index: int):
    """
    选择指定编号的支援卡/回忆编成。

    前置条件：STEP 2/3 页面
    结束状态：STEP 2/3 页面

    :param index: 支援卡/回忆编成的编号，从 1 开始。
    """
    def _current():
        numbers = []
        while not numbers:
            device.screenshot()
            numbers = ocr.ocr(rect=R.Produce.BoxSetCountIndicator).squash().numbers()
            if not numbers:
                logger.warning('Failed to get current set number. Retrying...')
                sleep(0.2)
        return numbers[0]
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        current = _current()
        logger.info(f'Navigate to set #{index}. Now at set #{current}.')
        
        # 计算需要点击的次数
        click_count = abs(index - current)
        if click_count == 0:
            logger.info(f'Already at set #{current}.')
            return
        click_target = R.Produce.PointProduceNextSet if current < index else R.Produce.PointProducePrevSet
        
        # 点击
        for _ in range(click_count):
            device.click(click_target)
            sleep(0.1)
        
        # 确认
        final_current = _current()
        if final_current == index:
            logger.info(f'Arrived at set #{final_current}.')
            return
        else:
            retry_count += 1
            logger.warning(f'Failed to navigate to set #{index}. Current set is #{final_current}. Retrying... ({retry_count}/{max_retries})')
    
    logger.error(f'Failed to navigate to set #{index} after {max_retries} retries.')
    
# 选择偶像
def step1(idol_skin_id: str) -> bool:
    if not R.Produce.TextStepIndicator1.exists():
        logger.debug('Not at step1, returning False')
        return False
    
    logger.info('Target idol is %s, locating...', idol_skin_id)

    # 首先判断是否已选中目标偶像
    def _check_idol() -> bool:
        img = device.screenshot()
        x, y, w, h = R.Produce.BoxSelectedIdol.xywh
        if img is not None and match_idol(idol_skin_id, img[y:y+h, x:x+w]):
            return True
        else:
            logger.info('Not selected. Trying to select.')
            return False
    
    if _check_idol():
        logger.info('Idol already %s selected.', idol_skin_id)
        return True
    sleep(0.5)

    count = 0
    while not _check_idol():
        logger.warning('Selected idol is not expected. Retrying.')
        count += 1
        if count > 5:
            raise UnrecoverableError(idol_skin_id)
        _select_idol(idol_skin_id)

    logger.info('Idol %s selected successfully.', idol_skin_id)
    return True

# 选择支援卡
def step2(set_number: int | None = None, auto_set: bool | None = None) -> bool:
    """培育准备 STEP2。
    前提：位于 STEP2 页面。

    :param set_number: 编成编号, [1, 20], defaults to None
    :param auto_set: 是否自动编成, defaults to None
    """
    if set_number is None and auto_set is None:
        raise ValueError("Either set_number or auto_set must be provided.")
    if set_number is not None and auto_set is not None:
        raise ValueError("Only one of set_number or auto_set should be provided.")
    
    if not R.Produce.TextStepIndicator2.exists():
        logger.debug('Not at step2, returning False')
        return False
    
    if auto_set:
        for _ in Loop():
            # 结束条件
            if R.Produce.Step2.ButtonNext.q(enabled=True).exists():
                logger.info('Auto set completed.')
                return True
            # 触发自动编成
            elif R.Produce.ButtonAutoSet.try_click():
                sleep(1)
            # 自动编成确认弹窗
            elif R.Produce.Step2.AutoSet.ConfirmTitle.exists():
                R.Produce.Step2.AutoSet.ConfirmButton.try_click()
                sleep(2)
    if set_number is not None:
        # 先导航到目标编成
        _select_set(set_number)
        # 然后配置租借
        for _ in Loop():
            # 到达租借界面
            if R.Produce.Step2.Rent.ConfirmButton.exists():
                logger.info('At support card rent')
                break
            # 点击租借加号
            if R.Produce.Step2.EmptySupportCardSlot.try_click():
                pass
        # 确认租借
        for _ in Loop():
            # 结束条件
            if R.Produce.Step2.ButtonNext.q(enabled=True).exists():
                logger.info('Support card rent completed.')
                return True
            # 勾选只展示符合 PLAN 的
            elif chk := R.Produce.Step2.Rent.CheckboxPlan.q(checked=False).find():
                chk.set_checked(True)
                sleep(1)
            elif R.Produce.Step2.Rent.ConfirmButton.try_click():
                sleep(1)
        return True
    
    assert False, 'not possible'

# 选择回忆
def step3(set_number: int | None = None, auto_set: bool | None = None) -> bool:
    """培育准备 STEP3。
    前提：位于 STEP3 页面。

    :param set_number: 编成编号, [1, 20], defaults to None
    :param auto_set: 是否自动编成, defaults to None
    """
    if set_number is None and auto_set is None:
        raise ValueError("Either set_number or auto_set must be provided.")
    if set_number is not None and auto_set is not None:
        raise ValueError("Only one of set_number or auto_set should be provided.")
    
    if not R.Produce.TextStepIndicator3.exists():
        logger.debug('Not at step3, returning False')
        return False
    
    if auto_set:
        for _ in Loop():
            # 触发自动编成
            if R.Produce.ButtonAutoSet.try_click():
                sleep(1)
            # 自动编成确认弹窗
            elif R.Produce.Step3.AutoSet.ConfirmTitle.exists():
                break
        for _ in Loop():
            # 结束条件
            if (
                not R.Produce.Step3.AutoSet.ConfirmTitle.exists()
                and R.Produce.Step3.ButtonNext.q(enabled=True).exists()
                and R.Produce.TextStepIndicator3.exists()
            ):
                break
            # 点击确认
            elif R.Produce.Step3.AutoSet.ConfirmButton.try_click():
                sleep(2)
        return True

    if set_number is not None:
        # 导航到目标编成
        _select_set(set_number)
        return True
    
    assert False, 'not possible'

#
def step4(note_boost: bool, pt_boost: bool) -> bool:
    """培育准备 STEP4。
    前提：位于 STEP4 页面。
    """
    if not R.Produce.TextStepIndicator4.exists():
        logger.debug('Not at step4, returning False')
        return False
    
    if chk := R.Produce.Step4.CheckboxNoteBoost.q(threshold=0.6).find():
        chk.set_checked(note_boost)
        sleep(1)
    if chk := R.Produce.Step4.CheckboxPtBoost.q(threshold=0.6).find():
        chk.set_checked(pt_boost)
        sleep(1)

    return True

def prepare():
    """完成培育准备，从 STEP1 到 STEP4 共四个步骤。

    前提：位于 STEP1 页面。\n
    结束：位于 STEP4，点击开始培育按钮前。
    """
    if not R.Produce.TextStepIndicator1.exists():
        logger.debug('Not at step1, returning False')
        return False
    
    # 选择偶像
    idol_skin_id = produce_solution().data.idol
    assert idol_skin_id is not None, "idol_skin_id is None"
    step1(idol_skin_id)
    R.Produce.Step1.ButtonNext.wait().click()
    
    # 选择支援卡
    R.Produce.TextStepIndicator2.wait()
    if produce_solution().data.auto_set_support_card:
        step2(auto_set=True)
    else:
        set_number = produce_solution().data.support_card_set
        assert set_number is not None, "support_card_set is None"
        step2(set_number=set_number)
    R.Produce.Step2.ButtonNext.wait().click()
    
    # 选择回忆
    R.Produce.TextStepIndicator3.wait()
    if produce_solution().data.auto_set_memory:
        step3(auto_set=True)
    else:
        set_number = produce_solution().data.memory_set
        assert set_number is not None, "memory_set is None"
        step3(set_number=set_number)
    
    # 处理没有租借时弹出的有可用次数提示
    for _ in Loop():
        # 弹窗
        if R.Produce.TextRentAvailable.exists():
            R.Produce.RentAvailableConfirmButton.try_click()
            sleep(1)
        # 3 -> 4
        elif R.Produce.TextStepIndicator3.exists():
            R.Produce.Step3.ButtonNext.try_click()
        elif R.Produce.TextStepIndicator4.exists():
            break
    
    # 设置加成
    note_boost = produce_solution().data.use_note_boost
    pt_boost = produce_solution().data.use_pt_boost
    step4(note_boost=note_boost, pt_boost=pt_boost)

if __name__ == "__main__":
    from kotonebot.backend.context import manual_context, init_context
    from kotonebot.client.host import Mumu12V5Host
    from kotonebot.client.host.mumu12_host import MuMu12HostConfig
    from logging import basicConfig, DEBUG
    basicConfig(level=DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    d = Mumu12V5Host.list()[0].create_device('nemu_ipc', MuMu12HostConfig())
    d.start()
    init_context(target_device=d)
    manual_context().begin()

    from kaa.kaa_context import init
    from kaa.config import manager
    name = '12'
    init(manager.read(name=name), name)
    
    # step1(produce_solution().data.idol)
    # step2(auto_set=True)
    # step2(set_number=2)
    # step3(auto_set=True)
    # step3(set_number=2)
    # step4(False, True)
    prepare()
