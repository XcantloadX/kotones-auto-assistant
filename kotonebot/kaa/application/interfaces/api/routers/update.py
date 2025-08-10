from fastapi import APIRouter
from ..schemas import VersionInfo, SaveResult

router = APIRouter(tags=["update"]) 


@router.get("/update/versions", response_model=VersionInfo)
async def get_update_versions() -> VersionInfo:
    # 占位：真实实现应查询发布渠道；此处返回已安装版本与一个示例最新版本
    try:
        import importlib.metadata
        installed = importlib.metadata.version('ksaa')
    except Exception:
        installed = None
    latest = installed
    versions = [v for v in ([installed] if installed else [])]
    return VersionInfo(installed=installed, latest=latest, versions=versions)


@router.post("/update/install", response_model=SaveResult)
async def post_update_install() -> SaveResult:
    # 占位：返回需要退出/即将重启提示
    return SaveResult(ok=True, message="已开始安装（示例）。请稍后手动重启应用。") 