import logging

from fastapi import FastAPI

from kaa.application.api import api_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application for KAA HTTP API."""
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
    app = FastAPI(title="Kotone Auto Assistant API", version="1.0.0")

    app.include_router(api_router)

    return app


app = create_app()
