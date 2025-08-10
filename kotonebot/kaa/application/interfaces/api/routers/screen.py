from fastapi import APIRouter, Response, Query
import cv2

router = APIRouter(tags=["screen"]) 


@router.get("/screen/current")
async def get_screen_current(size: str = Query("thumb", pattern="^(thumb|full)$")):
    from kotonebot.backend.context import device
    img = device.screenshot()
    if size == "thumb":
        h, w = img.shape[:2]
        scale = 240 / max(h, w)
        if scale < 1.0:
            img = cv2.resize(img, (int(w*scale), int(h*scale)))
    buff = cv2.imencode('.png', img)[1].tobytes()
    return Response(buff, media_type="image/png")


@router.get("/screen/last")
async def get_screen_last(size: str = Query("thumb", pattern="^(thumb|full)$")):
    # 目前与 current 等价；如需缓存可扩展
    return await get_screen_current(size) 