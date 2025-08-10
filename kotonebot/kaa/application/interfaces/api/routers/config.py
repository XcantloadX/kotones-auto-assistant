from fastapi import APIRouter
from ..schemas import SaveResult, ConfigDocument
from kotonebot.config.manager import load_config, save_config
from kotonebot.kaa.config import BaseConfig
from kotonebot.config.base_config import RootConfig

router = APIRouter(tags=["config"]) 


@router.get("/config")
async def get_config() -> ConfigDocument:
    root = load_config("config.json", type=BaseConfig)
    return ConfigDocument(data=root.model_dump(mode='json'))


@router.put("/config", response_model=SaveResult)
async def put_config(doc: ConfigDocument) -> SaveResult:
    try:
        root = RootConfig[BaseConfig].model_validate(doc.data)
        save_config(root, "config.json")
        # 尝试热重载（按 gr.py 的 reload 行为）
        try:
            from kotonebot.kaa.main.gr import KotoneBotUI  # 仅为了复用思路，这里不直接实例化 UI
            # 后台 API 模式下我们通过 Kaa 重置配置
            from kotonebot.kaa.application.interfaces.api.deps import get_state
            state = get_state()
            kaa = state.kaa
            if kaa is not None:
                kaa.config_path = "config.json"
                kaa.config_type = BaseConfig
                # 重新初始化
                kaa.initialize()
        except Exception:
            pass
        return SaveResult(ok=True, message="设置已保存")
    except Exception as e:
        return SaveResult(ok=False, message=f"保存失败：{e}") 