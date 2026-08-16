"""从商店购买物品"""
import logging
from typing import Sequence

from kotonebot import task, device, action, sleep
from kotonebot.backend.loop import Loop

from kaa.tasks import R
from kaa.game_ui import dialog
from kaa.config import conf
from kotonebot.core import BoundPrefab, Prefab
from ..actions.scenes import goto_home

logger = logging.getLogger(__name__)


@action('商店购买.确认购买')
def confirm_purchase() -> bool:
    """
    处理购买确认弹窗：把数量加到最大，再点击确认。

    前置条件：购买确认弹窗已打开
    结束状态：购买确认弹窗已关闭

    :return: 是否应当继续购买。
    """
    for _ in Loop(interval=0.5):
        # 弹窗未打开，无需处理
        if not R.Daily.Shop.PurchaseConfirmDialog.Title.exists():
            logger.debug('Purchase confirm dialog not present.')
            break
        # 还可以增加数量时，先把数量加到最大
        if R.Daily.Shop.PurchaseConfirmDialog.ButtonAdd.q(enabled=True).try_click():
            sleep(0.3)
            continue
        # 如果不能增大，而且也不能购买，说明余额不足
        if (
            not R.Daily.Shop.PurchaseConfirmDialog.ButtonAdd.q(enabled=True).exists()
            and not R.Daily.Shop.PurchaseConfirmDialog.ButtonConfirm.q(enabled=True).exists()
        ):
            logger.warning('Insufficient balance to purchase item.')
            R.Daily.Shop.PurchaseConfirmDialog.ButtonCancel.click()
            sleep(0.5)
            return False
        # 点击确认购买并等待动画完成
        if R.Daily.Shop.PurchaseConfirmDialog.ButtonConfirm.q(enabled=True).try_click():
            logger.debug('Clicked purchase confirm button.')
            sleep(1)
            break
    return True

@action('商店购买.点击商品并确认')
def click_item_and_confirm(prefabs: Sequence[Prefab | BoundPrefab]) -> bool:
    """
    点击列表中的第一个可购买商品，并处理购买确认弹窗。

    :param prefabs: 商品对应的 Prefab 列表
    :return: 是否点击了某个商品
    """
    for prefab in prefabs:
        if prefab.try_click():
            logger.debug('Clicked a purchasable item.')
            sleep(1)
            if not confirm_purchase():
                logger.warning('Purchase failed due to insufficient balance.')
                break
            return True
    return False


@action('商店购买.金币商店')
def purchase_money():
    """
    购买金币商店商品：购买推荐商品和配置指定的商品，然后向下滚动直到列表底部。

    前置条件：位于日常商店
    结束状态：金币商店列表已经滚动到底部且全部购买完毕
    """
    # 配置中指定的金币商品
    money_prefabs = [
        item.to_resource().q(colored=True)
        for item in conf().tasks.purchase.money_items
    ]
    scrollbar = R.Daily.Shop.Scrollbar.require()
    for _ in Loop(interval=0.5):
        # 购买推荐商品（おすすめ）
        if rec := R.Daily.TextShopRecommended.find():
            logger.debug('Clicking recommended item.')
            device.click(rec.rect.moved(0, 30))
            sleep(1)
            if not confirm_purchase():
                break
            continue

        # 购买配置中指定的商品
        if click_item_and_confirm(money_prefabs):
            continue

        # 往下翻页
        scrollbar.update()
        if scrollbar.at_end:
            # 尝试刷新商品列表；无法刷新则结束金币购买
            if R.Daily.ButtonRefreshMoneyShop.try_click():
                logger.debug('Clicked refresh money shop list.')
                sleep(2)
                continue
            logger.info('Money shop list reached the end.')
            return
        scrollbar.by(0.3)


@action('商店购买.AP 商店')
def purchase_ap():
    """
    切换到 AP 商店 Tab，并购买配置指定的 AP 商品。

    前置条件：位于日常商店
    结束状态：AP 商品已全部购买完毕
    """
    # 配置中指定的 AP 商品
    ap_items = conf().tasks.purchase.ap_items
    ap_prefabs = [
        R.Daily.ApShop.Items.PtBoost if 0 in ap_items else None,
        R.Daily.ApShop.Items.NoteBoost if 1 in ap_items else None,
        R.Daily.ApShop.Items.Rechallenge if 2 in ap_items else None,
        R.Daily.ApShop.Items.MemoryRegenerate if 3 in ap_items else None,
    ]
    ap_prefabs = [item for item in ap_prefabs if item is not None]

    # 切换到 AP Tab
    logger.debug('Switching to AP tab.')
    R.Daily.TextTabShopAp.try_click()
    sleep(1)

    for _ in Loop(interval=0.5):
        if click_item_and_confirm(ap_prefabs):
            continue
        logger.info('No more AP items to buy.')
        break


@action('商店购买.进入日常商店')
def goto_daily_shop():
    """
    从首页进入日常商店。

    前置条件：位于首页附近
    结束状态：位于日常商店
    """
    for _ in Loop(interval=0.5):
        # 已经位于日常商店
        if R.Daily.TextTabShopAp.exists():
            logger.debug('Now at daily shop.')
            break
        # 关闭「默认购买次数改变」提示框
        if R.Daily.TextDefaultExchangeCountChangeDialog.exists():
            logger.debug('Closed default exchange count dialog.')
            dialog.yes()
            sleep(0.5)
            continue
        # 打开商店
        if R.Daily.ButtonShop.try_click():
            logger.debug('Clicked shop button.')
            sleep(0.5)
            continue
        # 进入每日商店
        if R.Daily.ButtonDailyShop.try_click():
            logger.debug('Clicked daily shop button.')
            sleep(1)


@action('商店购买.每周礼包')
def purchase_weekly_pack():
    """
    购买每周免费礼包。

    前置条件：任意位置
    结束状态：位于首页
    """
    goto_home()
    for _ in Loop(interval=0.5):
        # 已进入礼包商店
        if R.Daily.PackShop.Title.exists():
            logger.debug('Now at weekly pack shop.')
            break
        # 打开商店
        if R.Daily.ButtonShop.try_click():
            logger.debug('Clicked shop button.')
            sleep(0.5)
            continue
        # 点击礼包按钮
        if R.Common.ShopPackButton.try_click():
            logger.debug('Clicked pack shop button.')
            sleep(1)

    for _ in Loop(interval=0.5):
        # 先尝试点击确认（若存在遗留确认弹窗）
        if R.Common.ButtonConfirmNoIcon.try_click():
            logger.debug('Clicked pack purchase confirm button.')
            sleep(1)
            goto_home()
            break
        # 点击免费礼包购买按钮
        if R.Daily.PackShop.ButtonFree.q(enabled=True).try_click():
            logger.debug('Clicked free pack button.')
            sleep(1)
            continue
        # 没有免费礼包可以购买，回到首页
        logger.info('No free weekly pack to buy.')
        goto_home()
        break


@task('商店购买')
def purchase():
    if not conf().tasks.purchase.enabled:
        logger.info('Purchase task is disabled in config.')
        return
    
    ap_enabled = conf().tasks.purchase.ap_enabled
    money_enabled = conf().tasks.purchase.money_enabled
    pack_enabled = conf().tasks.purchase.weekly_enabled

    if ap_enabled or money_enabled:
        goto_daily_shop()
        if money_enabled:
            purchase_money()
        if ap_enabled:
            purchase_ap()

    if pack_enabled:
        purchase_weekly_pack()

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    purchase()