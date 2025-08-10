from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
import logging
import time

from .routers import health
from .routers import run as run_router
from .routers import tasks as tasks_router
from .routers import config as config_router
from .routers import config_quick as config_quick_router
from .routers import screen as screen_router
from .routers import emulator as emulator_router
from .routers import update as update_router
from .routers import reports as reports_router
from .routers import produce as produce_router
from .routers import options as options_router


def create_app() -> FastAPI:
    app = FastAPI(title="Kotone Auto Assistant API", version="0.1.0")

    # Middlewares
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger = logging.getLogger("kaa.api")

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        logger.info(f"%s %s -> %s (%d ms)", request.method, request.url.path, response.status_code, duration_ms)
        return response

    # Routers
    api_prefix = "/api/v1"
    app.include_router(health.router, prefix=api_prefix)
    app.include_router(run_router.router, prefix=api_prefix)
    app.include_router(tasks_router.router, prefix=api_prefix)
    app.include_router(config_router.router, prefix=api_prefix)
    app.include_router(config_quick_router.router, prefix=api_prefix)
    app.include_router(screen_router.router, prefix=api_prefix)
    app.include_router(emulator_router.router, prefix=api_prefix)
    app.include_router(update_router.router, prefix=api_prefix)
    app.include_router(reports_router.router, prefix=api_prefix)
    app.include_router(options_router.router, prefix=api_prefix)
    app.include_router(produce_router.router, prefix=api_prefix)

    return app 