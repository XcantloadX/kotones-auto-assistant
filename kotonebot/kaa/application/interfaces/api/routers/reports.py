from fastapi import APIRouter, Response
from ..schemas import SaveResult
from kotonebot.kaa.main.gr import _save_bug_report
from kotonebot.kaa.main import Kaa

router = APIRouter(tags=["reports"]) 


@router.post("/reports/bug", response_model=SaveResult)
async def post_reports_bug(title: str, description: str, upload: bool = False) -> SaveResult:
    # 复用 gr.py 的保存报告实现
    try:
        kaa = Kaa('config.json')
        version = kaa.version
        gen = _save_bug_report(title, description, version, upload)
        # 消耗生成器直到结束
        last = ""
        for step in gen:
            last = step
        # 模块级生成器的 return 值无法直接获取；这里只返回进度最后一步文案
        return SaveResult(ok=True, message=last or "报告已保存")
    except Exception as e:
        return SaveResult(ok=False, message=f"保存失败：{e}")


@router.get("/reports/logs.zip")
async def get_reports_logs():
    # 简化：返回路径提示文本（原本计划返回文件下载，后续阶段再完善）
    from kotonebot.kaa.main.gr import KotoneBotUI
    kaa = Kaa('config.json')
    ui = KotoneBotUI(kaa)
    path = ui.export_logs()
    return Response(path, media_type="text/plain; charset=utf-8")


@router.get("/reports/dumps.zip")
async def get_reports_dumps():
    from kotonebot.kaa.main.gr import KotoneBotUI
    kaa = Kaa('config.json')
    ui = KotoneBotUI(kaa)
    path = ui.export_dumps()
    return Response(path, media_type="text/plain; charset=utf-8") 