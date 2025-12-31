from fastapi import APIRouter

from .tasks_api import router as tasks_router
from .config_api import router as config_router
from .produce_api import router as produce_router
from .update_api import router as update_router
from .feedback_api import router as feedback_router
from .system_api import router as system_router
from .idle_api import router as idle_router


api_router = APIRouter(prefix="/api")
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(produce_router, prefix="/produce", tags=["produce"])
api_router.include_router(update_router, prefix="/update", tags=["update"])
api_router.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
api_router.include_router(system_router, prefix="/system", tags=["system"])
api_router.include_router(idle_router, prefix="/idle", tags=["idle"])
