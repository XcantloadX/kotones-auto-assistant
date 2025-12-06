"""从商店购买物品"""
import logging
from typing import Optional

from kotonebot.backend.loop import Loop
from kaa.tasks import R
from kaa.config import conf, DailyMoneyShopItems
from kotonebot.primitives.geometry import Point
from kotonebot.util import Countdown, cropped
from kotonebot import task, device, image, action, sleep
from ..actions.scenes import goto_home, goto_shop, at_daily_shop

logger = logging.getLogger(__name__)

@action('购买 Money 物品', screenshot_mode='manual')
def money_items2(items: Optional[list[DailyMoneyShopItems]] = None):
    """
    购买 Money 物品

    前置条件：商店页面的 マニー Tab\n
    结束状态：-

    :param items: 要购买的物品列表，默认为 None。为 None 时使用配置文件里的设置。
    """
    # 前置条件：[screenshots\shop\money1.png]
    logger.info(f'Purchasing マニー items.')

    if items is None:
        items = conf().purchase.money_items
    
    device.screenshot()
    if DailyMoneyShopItems.Recommendations in items:
        dispatch_recommended_items()
        items.remove(DailyMoneyShopItems.Recommendations)

    finished = []
    max_scroll = 3
    scroll = 0
    while items:
        for item in items:
            if ret := image.find(item.to_resource(), colored=True):
                logger.info(f'Purchasing {item.to_ui_text(item)}...')
                confirm_purchase(ret.position)
                finished.append(item)
        items = [item for item in items if item not in finished]
        # 全都买完了
        if not items:
            break
        # 还有，翻页后继续
        else:
            device.swipe_scaled(x1=0.5, x2=0.5, y1=0.8, y2=0.5)
            sleep(0.5)
            device.screenshot()
            scroll += 1
            if scroll >= max_scroll:
                break
    logger.info(f'Purchasing money items completed. {len(finished)} item(s) purchased.')
    if items:
        logger.info(f'{len(items)} item(s) not purchased/already purchased: {", ".join([item.to_ui_text(item) for item in items])}')

@action('购买推荐商品', screenshot_mode='manual')
def dispatch_recommended_items():
    """
    购买推荐商品

    前置条件：商店页面的 マニー Tab\n
    结束状态：-
    """
    # 前置条件：[screenshots\shop\money1.png]
    logger.info(f'Start purchasing recommended items.')

    for _ in Loop():
        if rec := image.find(R.Daily.TextShopRecommended):
            logger.info(f'Clicking on recommended item.') # TODO: 计数
            pos = rec.position.offset(dx=0, dy=80)
            confirm_purchase(pos)
            sleep(2.5) # 
        elif image.find(R.Daily.IconTitleDailyShop) and not image.find(R.Daily.TextShopRecommended):
            logger.info(f'No recommended item found. Finished.')
            break

@action('确认购买', screenshot_mode='manual')
def confirm_purchase(target_item_pos: Point | None = None):
    """
    确认购买

    前置条件：点击某个商品后的瞬间\n
    结束状态：对话框关闭后原来的界面
    """
    # 前置条件：[screenshots\shop\dialog.png]
    # TODO: 需要有个更好的方式检测是否已购买
    purchased = False
    cd = Countdown(sec=3)
    for _ in Loop():
        if cd.expired():
            purchased = True
            break
        if image.find(R.Daily.TextShopItemSoldOut):
            logger.info('Item sold out.')
            purchased = True
            break
        elif image.find(R.Daily.TextShopItemPurchased):
            logger.info('Item already purchased.')
            purchased = True
            break
        elif image.find(R.Common.ButtonConfirm):
            logger.info('Confirming purchase...')
            device.click()
            sleep(0.5)
        else:
            if target_item_pos:
                device.click(target_item_pos)
    
    if purchased:
        logger.info('Item sold out.')
        sleep(1) # 等待售罄提示消失
        return
    else:
        device.screenshot()
        # TODO: 这下面这段代码是干什么的？为什么上面和下面都点击了 Confirm？
        for _ in Loop(interval=0.2):
            if image.find(R.Daily.ButtonShopCountAdd, colored=True):
                logger.debug('Adjusting quantity(+1)...')
                device.click()
            else:
                break
        logger.debug('Confirming purchase...')
        device.click(image.expect_wait(R.Common.ButtonConfirm))
    # 等待对话框动画结束
    image.expect_wait(R.Daily.IconTitleDailyShop)

@action('购买 AP 物品')
def ap_items():
    """
    购买 AP 物品

    前置条件：位于商店页面的 AP Tab
    """
    # [screenshots\shop\ap1.png]
    logger.info(f'Purchasing AP items.')
    results = image.find_all(R.Daily.IconShopAp, threshold=0.7)
    sleep(1)
    # 按 X, Y 坐标排序从小到大
    results = sorted(results, key=lambda x: (x.position[0], x.position[1]))
    # 按照配置文件里的设置过滤
    item_indices = conf().purchase.ap_items
    logger.info(f'Purchasing AP items: {item_indices}')
    for index in item_indices:
        if index <= len(results):
            logger.info(f'Purchasing #{index} AP item.')
            device.click(results[index])
            sleep(0.5)
            purchased = image.wait_for(R.Daily.TextShopItemSoldOut, timeout=1)
            if purchased is not None:
                logger.info(f'AP item #{index} already purchased.')
                continue
            comfirm = image.expect_wait(R.Common.ButtonConfirm, timeout=2)
            # 如果数量不是最大,调到最大
            for _ in Loop(interval=0.3):
                if image.find(R.Daily.ButtonShopCountAdd, colored=True):
                    logger.debug('Adjusting quantity(+1)...')
                    device.click()
                else:
                    break
            logger.debug(f'Confirming purchase...')
            device.click(comfirm)
            sleep(1.5)
        else:
            logger.warning(f'AP item #{index} not found')
    logger.info(f'Purchasing AP items completed. {len(item_indices)} items purchased.')

@action('购买 周免费礼包')
def weekly_free_pack():
    """
    购买 周免费礼包

    前置条件：位于主商店页面
    """
    logger.info(f'Purchasing weekly free pack.')
    
    sleep(1.0) # 动画加载完毕，但是按钮不可点击
    device.click(image.expect_wait(R.Common.ShopPackButton))

    if image.wait_for(R.Daily.WeeklyFreePack, colored=True, timeout=1):
        device.click()
        device.click(image.expect_wait(R.Common.ButtonConfirmNoIcon))
        logger.info('Confirming purchase of weekly free pack.')

@task('商店购买')
def purchase():
    """
    从商店购买物品
    """
    if not conf().purchase.enabled:
        logger.info('Purchase is disabled.')
        return

    goto_shop()
    # 进入每日商店 [screenshots\shop\shop.png]
    device.click(image.expect_wait(R.Daily.ButtonDailyShop)) # TODO: memoable
    # 等待载入
    ap_tab = image.expect_wait(R.Daily.TextTabShopAp)

    # 购买マニー物品
    if conf().purchase.money_enabled:
        image.expect_wait(R.Daily.IconShopMoney)
        money_items2()
        sleep(0.5)
        if conf().purchase.money_refresh and image.find(R.Daily.ButtonRefreshMoneyShop):
            logger.info('Refreshing money shop.')
            device.click()
            # 等待刷新完成
            for _ in Loop():
                if not image.find(R.Daily.ButtonRefreshMoneyShop):
                    break
                logger.debug('Waiting for money shop refresh...')
            money_items2()
            sleep(0.5)
    else:
        logger.info('Money purchase is disabled.')
    
    # 购买 AP 物品
    if conf().purchase.ap_enabled:
        # 点击 AP 选项卡
        device.click(ap_tab)
        # 等待 AP 选项卡加载完成
        image.expect_wait(R.Daily.IconShopAp, threshold=0.7)
        ap_items()
        sleep(0.5)
    else:
        logger.info('AP purchase is disabled.')
    
    # 返回主商店页面
    device.click(image.expect_wait(R.Common.ButtonToolbarBack))
    
    # 购买周免费礼包
    if conf().purchase.weekly_enabled:
        weekly_free_pack()
    
    goto_home()

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    purchase()
