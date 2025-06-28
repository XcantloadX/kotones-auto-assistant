import logging
from itertools import cycle
from typing import Optional, Literal
from typing_extensions import assert_never

from kotonebot.kaa.skill_card_action.global_idol_setting_action import update_archetype_by_idol_skin_id
from kotonebot.ui import user
from kotonebot.util import Countdown, Interval
from kotonebot.backend.context.context import wait
from kotonebot.backend.dispatch import SimpleDispatcher

from kotonebot.kaa.tasks import R
from kotonebot.kaa.common import conf
from kotonebot.kaa.game_ui import dialog
from ..actions.scenes import at_home, goto_home
from kotonebot.kaa.game_ui.idols_overview import locate_idol, find_idol_skin_id_on_resume_produce
from ..produce.in_purodyuusu import hajime_pro, hajime_regular, hajime_master, resume_pro_produce, resume_regular_produce, \
    resume_master_produce
from kotonebot import device, image, ocr, task, action, sleep, contains, regex

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
    it = Interval()
    while not image.find(R.Common.ButtonConfirmNoIcon):
        if image.find(R.Produce.ButtonPIdolOverview):
            device.click()
        device.screenshot()
        it.wait()
    # 选择偶像
    pos = locate_idol(skin_id)
    if pos is None:
        raise ValueError(f"Idol {skin_id} not found.")
    # 确认
    it.reset()
    while btn_confirm := image.find(R.Common.ButtonConfirmNoIcon):
        device.click(pos)
        sleep(0.3)
        device.click(btn_confirm)
        it.wait()

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
    
@action('继续当前培育', screenshot_mode='manual-inherit')
def resume_produce():
    """
    继续当前培育

    前置条件：游戏首页，且当前有进行中培育\n
    结束状态：游戏首页
    """
    device.screenshot()
    # 点击 プロデュース中
    # [res/sprites/jp/daily/home_1.png]
    logger.info('Click ongoing produce button.')
    device.click(R.Produce.BoxProduceOngoing)
    btn_resume = image.expect_wait(R.Produce.ButtonResume)
    # 判断信息
    mode_result = image.find_multi([
        R.Produce.ResumeDialogRegular,
        R.Produce.ResumeDialogPro,
        R.Produce.ResumeDialogMaster
    ])
    if not mode_result:
        raise ValueError('Failed to detect produce mode.')
    if mode_result.index == 0:
        mode = 'regular'
    elif mode_result.index == 1:
        mode = 'pro'
    else:
        mode = 'master'
    logger.info(f'Produce mode: {mode}')
    retry_count = 0
    max_retries = 5
    current_week = None
    while retry_count < max_retries:
        week_text = ocr.ocr(R.Produce.BoxResumeDialogWeeks).squash().regex(r'\d+/\d+')
        if week_text:
            weeks = week_text[0].split('/')
            logger.info(f'Current week: {weeks[0]}/{weeks[1]}')
            if len(weeks) >= 2:
                current_week = int(weeks[0])
                break
        retry_count += 1
        logger.warning(f'Failed to detect weeks. week_text="{week_text}". Retrying... ({retry_count}/{max_retries})')
        sleep(0.5)
        device.screenshot()
    
    if retry_count >= max_retries:
        raise ValueError('Failed to detect weeks after multiple retries.')
    if current_week is None:
        raise ValueError('Failed to detect current_week.')

    # 更新全局偶像信息
    img = device.screenshot()
    skin_id = find_idol_skin_id_on_resume_produce(img)
    update_archetype_by_idol_skin_id(skin_id)

    # 点击 再開する
    # [kotonebot-resource/sprites/jp/produce/produce_resume.png]
    logger.info('Click resume button.')
    device.click(btn_resume)
    match mode:
        case 'regular':
            resume_regular_produce(current_week)
        case 'pro':
            resume_pro_produce(current_week)
        case 'master':
            resume_master_produce(current_week)
        case _:
            assert_never(mode)

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
    
    :param idol: 要培育的偶像。如果为 None，则使用配置文件中的偶像。
    :param mode: 培育模式。
    :return: 是否因为 AP 不足而跳过本次培育。
    """
    if not at_home():
        goto_home()

    device.screenshot()
    # 有进行中培育的情况
    if ocr.find(contains('中'), rect=R.Produce.BoxProduceOngoing):
        logger.info('Ongoing produce found. Try to resume produce.')
        resume_produce()
        return True

    # 新培育时更新偶像信息
    update_archetype_by_idol_skin_id(idol_skin_id)
    # 0. 进入培育页面
    mode_text = mode.upper()
    if mode_text == 'MASTER':
        mode_text = 'MASTER|MIASTER'
    logger.info(f'Enter produce page. Mode: {mode_text}')
    result = (SimpleDispatcher('enter_produce')
        .click(R.Produce.ButtonProduce)
        .click(regex(mode_text))
        .until(R.Produce.ButtonPIdolOverview, result=True)
        .until(R.Produce.TextAPInsufficient, result=False)
    ).run()
    if not result:
        if conf().produce.use_ap_drink:
            # [kotonebot-resource\sprites\jp\produce\screenshot_no_enough_ap_1.png]
            # [kotonebot-resource\sprites\jp\produce\screenshot_no_enough_ap_2.png]
            # [kotonebot-resource\sprites\jp\produce\screenshot_no_enough_ap_3.png]
            logger.info('AP insufficient. Try to use AP drink.')
            it = Interval()
            while True:
                if image.find(R.Produce.ButtonUse):
                    device.click()
                elif image.find(R.Produce.ButtonRefillAP):
                    device.click()
                elif ocr.find(contains(mode_text)):
                    device.click()
                elif image.find(R.Produce.ButtonPIdolOverview):
                    break
                device.screenshot()
                it.wait()
        else:
            logger.info('AP insufficient. Exiting produce.')
            device.click(image.expect_wait(R.InPurodyuusu.ButtonCancel))
            return False
    # 1. 选择 PIdol [screenshots/produce/screenshot_produce_start_1_p_idol.png]
    select_idol(idol_skin_id)
    it = Interval()
    while True:
        it.wait()
        device.screenshot()
        if image.find(R.Produce.TextAnotherIdolAvailableDialog):
            dialog.no()
        elif image.find(R.Common.ButtonNextNoIcon):
            device.click()
        if image.find(R.Produce.TextStepIndicator2):
            break
    # 2. 选择支援卡 自动编成 [screenshots/produce/screenshot_produce_start_2_support_card.png]
    image.expect_wait(R.Produce.TextStepIndicator2)
    it = Interval()
    while True:
        if image.find(R.Common.ButtonNextNoIcon, colored=True):
            device.click()
            break
        elif image.find(R.Produce.ButtonAutoSet):
            device.click()
            sleep(1)
        elif image.find(R.Common.ButtonConfirm, colored=True):
            device.click()
        device.screenshot()
        it.wait()
    # 3. 选择回忆 自动编成 [screenshots/produce/screenshot_produce_start_3_memory.png]
    image.expect_wait(R.Produce.TextStepIndicator3)
    # 自动编成
    if memory_set_index is not None and not 1 <= memory_set_index <= 10:
        raise ValueError('`memory_set_index` must be in range [1, 10].')
    if memory_set_index is None:
        device.click(image.expect_wait(R.Produce.ButtonAutoSet))
        wait(0.5, before='screenshot')
        device.screenshot()
    # 指定编号
    else:
        select_set(memory_set_index)
    (SimpleDispatcher('do_produce.step_3')
        .until(R.Produce.TextStepIndicator4)
        .click(R.Common.ButtonNextNoIcon)
        .click(R.Common.IconButtonCheck)
    ).run()

    # 4. 选择道具 [screenshots/produce/screenshot_produce_start_4_end.png]
    # TODO: 如果道具不足，这里加入推送提醒
    if conf().produce.use_note_boost:
        if image.find(R.Produce.CheckboxIconNoteBoost):
            device.click()
            sleep(0.1)
    if conf().produce.use_pt_boost:
        if image.find(R.Produce.CheckboxIconSupportPtBoost):
            device.click()
            sleep(0.1)
    device.click(image.expect_wait(R.Produce.ButtonProduceStart))
    # 5. 相关设置弹窗 [screenshots/produce/skip_commu.png]
    cd = Countdown(5).start()
    while not cd.expired():
        device.screenshot()
        if image.find(R.Produce.RadioTextSkipCommu):
            device.click()
        if image.find(R.Common.ButtonConfirmNoIcon):
            device.click()
    match mode:
        case 'regular':
            hajime_regular()
        case 'pro':
            hajime_pro()
        case 'master':
            hajime_master()
        case _:
            assert_never(mode)
    return True

@task('培育')
def produce():
    """
    培育任务
    """
    if not conf().produce.enabled:
        logger.info('Produce is disabled.')
        return
    import time
    count = conf().produce.produce_count
    idols = conf().produce.idols
    memory_sets = conf().produce.memory_sets
    mode = conf().produce.mode
    # 数据验证
    if count < 0:
        user.warning('配置有误', '培育次数不能小于 0。将跳过本次培育。')
        return

    idol_iterator = cycle(idols)
    memory_set_iterator = cycle(memory_sets)
    for i in range(count):
        start_time = time.time()
        idol = next(idol_iterator)
        if conf().produce.auto_set_memory:
            memory_set = None
        else:
            memory_set = next(memory_set_iterator, None)
        logger.info(
            f'Produce start with: '
            f'idol: {idol}, mode: {mode}, memory_set: #{memory_set}'
        )
        if not do_produce(idol, mode, memory_set):
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
    import os
    from datetime import datetime
    os.makedirs('logs', exist_ok=True)
    log_filename = datetime.now().strftime('logs/task-%y-%m-%d-%H-%M-%S.log')
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    import time
    from kotonebot.backend.context import init_context
    from kotonebot.kaa.common import BaseConfig

    init_context(config_type=BaseConfig)
    conf().produce.enabled = True
    conf().produce.mode = 'pro'
    conf().produce.produce_count = 1
    # conf().produce.idols = ['i_card-skin-hski-3-002']
    conf().produce.memory_sets = [1]
    conf().produce.auto_set_memory = False
    # do_produce(PIdol.月村手毬_初声, 'pro', 5)
    produce()
    # a()
    # select_idol()
    # select_set(10)
    # manual_context().begin()
    # print(ocr.ocr(rect=R.Produce.BoxSetCountIndicator).squash().numbers())