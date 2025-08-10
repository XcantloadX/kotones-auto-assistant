from fastapi import APIRouter
from ..schemas import OptionItem
from kotonebot.kaa.config import APShopItems, DailyMoneyShopItems

router = APIRouter(tags=["options"]) 


@router.get("/options/purchase/money_items", response_model=list[OptionItem])
async def list_money_items():
    return [
        OptionItem(label=DailyMoneyShopItems.to_ui_text(item), value=int(item))
        for item in DailyMoneyShopItems
    ]


@router.get("/options/purchase/ap_items", response_model=list[OptionItem])
async def list_ap_items():
    labels: dict[APShopItems, str] = {
        APShopItems.PRODUCE_PT_UP: "支援强化点数提升",
        APShopItems.PRODUCE_NOTE_UP: "笔记数提升",
        APShopItems.RECHALLENGE: "重新挑战券",
        APShopItems.REGENERATE_MEMORY: "回忆再生成券",
    }
    return [OptionItem(label=label, value=int(item)) for item, label in labels.items()] 