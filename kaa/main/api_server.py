import logging

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from kaa.application.api import api_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application for KAA HTTP API."""
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
    app = FastAPI(title="Kotone Auto Assistant API", version="1.0.0")

    # Allow local frontend dev servers to access the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8081", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=4825)