import logging
from typing import Optional, Literal
from typing_extensions import assert_never

from kaa.kaa_context import produce_solution
from kaa.tasks.produce.shared.common import resume_produce_pre
from kaa.tasks.produce.new.controller import ProduceController
from kaa.tasks.produce.legacy.in_purodyuusu import (
    hajime_regular, hajime_pro, hajime_master,
    resume_regular_produce, resume_pro_produce, resume_master_produce,
)
from kotonebot.ui import user
from kaa.tasks import R
from kaa.config import conf
from kaa.game_ui import dialog
from ..actions.scenes import at_home, goto_home
from kotonebot.backend.loop import Loop
from kotonebot.util import Countdown
from kaa.game_ui.idols_overview import locate_idol
from kotonebot import device, ocr, task, action, sleep
from kaa.errors import IdolCardNotFoundError
from .prepare import prepare

logger = logging.getLogger(__name__)

def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}m {seconds}s"

def unify(arr: list[int]):
    # 先对数组进行排序
    arr.sort()
    result = []
    i = 0
    while i < len(arr):
        # 将当前元素加入结果
        result.append(arr[i])
        # 跳过所有与当前元素相似的元素
        j = i + 1
        while j < len(arr) and abs(arr[j] - arr[i]) <= 10:
            j += 1
        i = j
    return result

@action('选择P偶像', screenshot_mode='manual-inherit')
def select_idol(skin_id: str):
    """
    选择目标P偶像

    前置条件：偶像选择页面 1.アイドル選択\n
    结束状态：偶像选择页面 1.アイドル選択\n
    """
    logger.info("Find and select idol: %s", skin_id)
    # 进入总览
    device.screenshot()
    for _ in Loop():
        if not R.Common.ButtonConfirmNoIcon.exists():
            R.Produce.ButtonPIdolOverview.try_click()
        else:
            break
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
        else:
            break

@action('培育开始.编成翻页', screenshot_mode='manual-inherit')
def select_set(index: int):
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
    
@action('继续当前培育.继续培育', screenshot_mode='manual-inherit')
def resume_produce_lst(
    mode: Literal['regular', 'pro', 'master'],
    current_week: int
):
    """
    继续当前培育.继续培育\n
    该函数正常情况不应该被单独调用。

    前置条件：培育中的任意一个页面\n
    结束状态：游戏首页

    :param mode: 培育模式
    :param current_week: 培育的周数
    """
    match mode:
        case 'regular':
            resume_regular_produce(current_week)
        case 'pro':
            resume_pro_produce(current_week)
        case 'master':
            resume_master_produce(current_week)
        case _:
            assert_never(mode)

@action('继续当前培育', screenshot_mode='manual-inherit')
def resume_produce():
    """
    继续当前培育

    前置条件：游戏首页，且当前有进行中培育\n
    结束状态：游戏首页
    """

    mode, current_week = resume_produce_pre()

    if conf().tasks.produce.produce_engine == 'legacy':
        resume_produce_lst(mode, current_week)
    else:
        ProduceController(mode=mode).run()

@action('执行培育', screenshot_mode='manual-inherit')
def do_produce(
    idol_skin_id: str,
    mode: Literal['regular', 'pro', 'master'],
    memory_set_index: Optional[int] = None
) -> bool:
    """
    进行培育流程

    前置条件：可导航至首页的任意页面\n
    结束状态：游戏首页\n

    :param memory_set_index: 回忆编成编号。
    :param idol_skin_id: 要培育的偶像。如果为 None，则使用配置文件中的偶像。
    :param mode: 培育模式。
    :return: 是否因为 AP 不足而跳过本次培育。
    :raises ValueError: 如果 `memory_set_index` 不在 [1, 20] 的范围内。
    """
    if memory_set_index is not None and not 1 <= memory_set_index <= 20:
        raise ValueError('`memory_set_index` must be in range [1, 20].')

    if not at_home():
        goto_home()

    device.screenshot()
    # 点击培育按钮，然后判断是新开还是再开培育
    for _ in Loop(interval=0.6):
        # 跨端破坏培育提示
        if R.Produce.BreakProduceDialog.Title.exists():
            if R.Produce.BreakProduceDialog.ButtonConfirm.try_click():
                logger.info('Confirmed break produce dialog.')
                continue
            
        if R.Produce.LogoHajime.exists(): # Hajime培育界面
            # 新开
            break
        elif R.Produce.LogoNia.exists(): # NIA培育界面
            device.click(R.Produce.PointNiaToHajime)
            sleep(0.5)
            continue
        elif R.Produce.ButtonResume.exists():
            # 再开
            resume_produce()
            return True
        # 首页的各种贴脸通知（比如 TRUE END 达成）
        elif dialog.no():
            continue
        else:
            device.click(R.Produce.BoxProduceOngoing)
            sleep(2)

    # 0. 进入培育页面
    logger.info(f'Enter produce page. Mode: {mode}')
    match mode:
        case 'regular':
            target_buttons = [R.Produce.ButtonHajime0Regular, R.Produce.ButtonHajime1Regular]
        case 'pro':
            target_buttons = [R.Produce.ButtonHajime0Pro, R.Produce.ButtonHajime1Pro]
        case 'master':
            target_buttons = [R.Produce.ButtonHajime1Master]
        case _:
            assert_never(mode)
    find_target_button = lambda: next((b for b in target_buttons if b.find()), None)  # noqa: E731
    result = None
    for _ in Loop():
        # 强化月间处理
        if conf().tasks.produce.enable_fever_month == 'on' and R.Produce.SwitchEventModeOff.exists():
            logger.info('Fever month checked on.')
            device.click()
            sleep(0.5)
        elif conf().tasks.produce.enable_fever_month == 'off' and R.Produce.SwitchEventModeOn.exists():
            logger.info('Fever month checked off.')
            device.click()
            sleep(0.5)
        elif btn := find_target_button():
            btn.click()
        elif R.Produce.ButtonPIdolOverview.exists():
            result = True
            break
        elif R.Produce.TextAPInsufficient.exists():
            result = False
            break
    if not result:
        if produce_solution().data.use_ap_drink:
            # [kotonebot-resource\sprites\jp\produce\screenshot_no_enough_ap_1.png]
            # [kotonebot-resource\sprites\jp\produce\screenshot_no_enough_ap_2.png]
            # [kotonebot-resource\sprites\jp\produce\screenshot_no_enough_ap_3.png]
            logger.info('AP insufficient. Try to use AP drink.')
            for _ in Loop(interval=1):
                if R.Produce.ButtonUse.q(enabled=True).try_click():
                    pass
                elif R.Produce.ButtonRefillAP.try_click():
                    pass
                elif btn := find_target_button():
                    btn.click()
                elif R.Produce.ButtonPIdolOverview.exists():
                    break
        else:
            logger.info('AP insufficient. Exiting produce.')
            R.InPurodyuusu.ButtonCancel.wait().click()
            return False

    prepare()

    R.Produce.Step4.ButtonProduceStart.wait().click()

    # 5. 相关设置弹窗 [screenshots/produce/skip_commu.png]
    cd = Countdown(5).start()
    for _ in Loop():
        if cd.expired():
            break
        device.screenshot()
        if R.Produce.RadioTextSkipCommu.try_click():
            pass
        if R.Common.ButtonConfirmNoIcon.try_click():
            pass
    if conf().tasks.produce.produce_engine == 'legacy':
        match mode:
            case 'regular':
                hajime_regular()
            case 'pro':
                hajime_pro()
            case 'master':
                hajime_master()
            case _:
                assert_never(mode)
    else:
        c = ProduceController(mode=mode)
        c.run()
    return True

@task('培育')
def produce():
    """
    培育任务
    """
    if not conf().tasks.produce.enabled:
        logger.info('Produce is disabled.')
        return
    import time
    count = conf().tasks.produce.produce_count
    idol = produce_solution().data.idol
    memory_set = produce_solution().data.memory_set
    support_card_set = produce_solution().data.support_card_set
    mode = produce_solution().data.mode
    # 数据验证
    if count < 0:
        user.warning('配置有误', '培育次数不能小于 0。将跳过本次培育。')
        return
    if idol is None:
        user.warning('配置有误', '未设置要培育的偶像。将跳过本次培育。')
        return

    for i in range(count):
        start_time = time.time()
        if produce_solution().data.auto_set_memory:
            memory_set_to_use = None
        else:
            memory_set_to_use = memory_set
        if produce_solution().data.auto_set_support_card:
            support_card_set_to_use = None
        else:
            support_card_set_to_use = support_card_set
        logger.info(
            f'Produce start with: '
            f'idol: {idol}, mode: {mode}, memory_set: #{memory_set_to_use}, support_card_set: #{support_card_set_to_use}'
        )
        if not do_produce(idol, mode, memory_set_to_use):
            user.info('AP 不足', f'由于 AP 不足，跳过了 {count - i} 次培育。')
            logger.info('%d produce(s) skipped because of insufficient AP.', count - i)
            break
        end_time = time.time()
        logger.info(f"Produce time used: {format_time(end_time - start_time)}")

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logging.getLogger('kotonebot').setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    from kotonebot.backend.context import init_context
    from kaa.common import KaaConfig
    from kaa.main import Kaa

    conf().tasks.produce.enabled = True
    conf().tasks.produce.produce_count = 3
    conf().tasks.produce.enable_fever_month = 'ignore'
    produce_solution().data.mode = 'pro'
    # produce_solution().data.idol = 'i_card-skin-hski-3-002'
    # produce_solution().data.memory_set = 1
    # produce_solution().data.auto_set_memory = True
    # do_produce(PIdol.月村手毬_初声, 'pro', 5)
    produce()
    # a()
    # select_idol()
    # select_set(10)
    # manual_context().begin()
    # print(ocr.ocr(rect=R.Produce.BoxSetCountIndicator).squash().numbers())
