"""从商店购买物品"""
import logging

from kotonebot import task, device
from kotonebot.pipeline import prefab as p, dummy, Pipeline, click_first, node, sleep as make_sleep, resolve_labels, Fragment

from kaa.tasks import R
from kaa.game_ui import dialog
from kaa.config import conf
from ..actions.scenes import goto_home

logger = logging.getLogger(__name__)


@node
def _go_home() -> bool:
    goto_home()
    return True

def ConfirmPurchase():
    entry = dummy()
    exit = dummy()

    is_at_dialog = p(R.Daily.Shop.PurchaseConfirmDialog.Title)
    try_add = p(
        R.Daily.Shop.PurchaseConfirmDialog.ButtonAdd.q(enabled=True),
        [click_first, make_sleep(0.3)]
    )
    click_confirm = p(R.Common.ButtonConfirm, [click_first, make_sleep(3)])
    @node
    def is_not_at_dialog() -> bool:
        return not R.Daily.Shop.PurchaseConfirmDialog.Title.exists()

    _ = is_at_dialog >> [
        try_add >> is_at_dialog,
        click_confirm >> exit,
        # is_at_daily_shop >> is_not_at_dialog >> exit
    ]

    resolve_labels()
    return Fragment(entry=is_at_dialog, exit=exit)

def PurchaseWeeklyPack():
    entry = dummy()
    stage_go_shop = dummy()
    stage_purchase = dummy()
    exit = dummy()

    click_shop = p(R.Daily.ButtonShop, [click_first])
    click_pack = p(R.Common.ShopPackButton, [click_first])
    at_pack_shop = p(R.Daily.PackShop.Title, [make_sleep(1)])
    click_free_button = p(R.Daily.PackShop.ButtonFree.q(enabled=True), [click_first, make_sleep(1)])
    click_confirm = p(R.Common.ButtonConfirmNoIcon, [click_first, make_sleep(1)])

    _ = entry >> _go_home() >> stage_go_shop >> [
        click_shop >> stage_go_shop,
        click_pack >> stage_go_shop,
        at_pack_shop >> stage_purchase >> [
            click_confirm >> _go_home() >> exit,
            click_free_button >> stage_purchase,
            # 如果没有就退出
            _go_home() >> exit,
        ]
    ]

    resolve_labels()
    return Pipeline(entry=entry, exit=exit)

def Purchase():
    # TODO: AP/金币 不足的逻辑需要处理
    money_items = conf().tasks.purchase.money_items
    ap_items = conf().tasks.purchase.ap_items
    money_item_prefabs = [item.to_resource().q(colored=True) for item in money_items]
    ap_item_prefabs = [
        R.Daily.ApShop.Items.PtBoost if 0 in ap_items else None,
        R.Daily.ApShop.Items.NoteBoost if 1 in ap_items else None,
        R.Daily.ApShop.Items.Rechallenge if 2 in ap_items else None,
        R.Daily.ApShop.Items.MemoryRegenerate if 3 in ap_items else None,
    ]
    ap_item_prefabs = [item for item in ap_item_prefabs if item is not None]
    scrollbar = R.Daily.Shop.Scrollbar.require()

    entry = dummy()
    stage_purchase_money = dummy()
    stage_purchase_ap = dummy()
    exit = dummy()

    click_shop = p(R.Daily.ButtonShop, [click_first])
    click_daily_shop = p(R.Daily.ButtonDailyShop, [click_first])
    # 可以设置默认购买数量为 MAX 的提示框
    close_tip = p(R.Daily.TextDefaultExchangeCountChangeDialog, [lambda ctx: dialog.yes()])
    is_at_daily_shop = p(R.Daily.TextTabShopAp)
    click_recommended = p(
        R.Daily.TextShopRecommended,
        [lambda ctx: device.click(ctx.matches[0].rect.moved(0, 30)), make_sleep(1)]
    )
    click_money_items = p(money_item_prefabs, [click_first, make_sleep(1)], id="prefab:click_money_items")
    click_ap_items = p(ap_item_prefabs, [click_first, make_sleep(1)])
    click_ap_tab = p(R.Daily.TextTabShopAp, [click_first, make_sleep(1)])
    click_refresh = p(R.Daily.ButtonRefreshMoneyShop, [click_first, make_sleep(2)])

    @node
    def scoll_and_is_at_end() -> bool:
        scrollbar.update()
        if scrollbar.at_end:
            return True
        else:
            scrollbar.by(0.3)
            return False

    @node
    def money_not_enabled() -> bool:
        return not conf().tasks.purchase.money_enabled

    @node
    def ap_not_enabled() -> bool:
        return not conf().tasks.purchase.ap_enabled

    _ = entry >> [
        # 1. 进入商店
        click_shop >> entry,
        click_daily_shop >> entry,
        close_tip >> entry,
        is_at_daily_shop >> stage_purchase_money >> [
            # 没开直接跳到 AP 购买阶段
            money_not_enabled() >> stage_purchase_ap,
            # 购买推荐商品
            click_recommended >> [
                ConfirmPurchase() >> stage_purchase_money,
                # 要是没点到就继续点
                click_recommended
            ],
            # 购买指定商品
            click_money_items >> [
                ConfirmPurchase() >> stage_purchase_money,
                # 要是没点到就继续点
                click_money_items
            ],
            # 往下翻页
            scoll_and_is_at_end() >> [
                # 尝试刷新
                click_refresh >> is_at_daily_shop,
                # 都买完了
                stage_purchase_ap >> click_ap_tab >> [
                    ap_not_enabled() >> exit,
                    # 购买 AP 物品
                    click_ap_items >> [
                        ConfirmPurchase() >> stage_purchase_ap,
                        # 要是没点到就继续点
                        click_ap_items
                    ],
                    # 没有了退出
                    exit
                ]
            ]

        ]
    ]

    resolve_labels()
    return Pipeline(entry=entry, strict=False)

@task('商店购买')
def purchase():
    purchase_ap = conf().tasks.purchase.ap_enabled
    purchase_money = conf().tasks.purchase.money_enabled
    purchase_pack = conf().tasks.purchase.weekly_enabled

    if purchase_ap or purchase_money:
        Purchase().run(interval=1)
    if purchase_pack:
        PurchaseWeeklyPack().run(interval=1)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] [%(lineno)d] %(message)s')
    logger.setLevel(logging.DEBUG)
    purchase()
    # PurchaseWeeklyPack().run(interval=1)
    while True:
        device.screenshot()
        print(R.Common.ButtonConfirmNoIcon.exists())
