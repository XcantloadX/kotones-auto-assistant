from fastapi import APIRouter
from kotonebot.config.manager import load_config
from kotonebot.kaa.config import BaseConfig

router = APIRouter(tags=["emulator"]) 


@router.get("/emulators/mumu")
async def get_mumu():
    root = load_config("config.json", type=BaseConfig)
    user = root.user_configs[0]
    return {
        "value": {
            "adb_emulator_name": user.backend.adb_emulator_name,
            "emulator_path": user.backend.emulator_path,
        },
        "choices": ["MuMu Player 12", "MuMu Player X"],
    }


@router.get("/emulators/leidian")
async def get_leidian():
    root = load_config("config.json", type=BaseConfig)
    user = root.user_configs[0]
    return {
        "value": {
            "adb_emulator_name": user.backend.adb_emulator_name,
            "emulator_path": user.backend.emulator_path,
        },
        "choices": ["Leidian 9", "Leidian 64bit"],
    } 