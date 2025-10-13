"""
FastAPI + Socket.IO 应用主入口
"""
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import socketio

from .rpc import registry
from .models import RPCErrorResponse, RPCRequest
from . import events

logger = logging.getLogger(__name__)

# 创建 Socket.IO 服务器
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_interval=25,
    ping_timeout=60,
    logger=True,
    engineio_logger=False
)

# 设置事件发布器的 SIO 实例
events.set_sio(sio)

app = FastAPI(
    title="Kaa API",
    description="Kotone Auto Assistant - New Web UI Backend",
    version="1.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Socket.IO 事件处理器
@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

@sio.on('rpc/req') # type: ignore
async def rpc_req(sid, payload):
    try:
        request = RPCRequest(**payload)
        logger.debug(f"RPC request from {sid}: {request.method}")
        
        response = await registry.dispatch(request)
        
        if isinstance(response, RPCErrorResponse):
            await sio.emit('rpc/err', response.model_dump(), room=sid)
        else:
            await sio.emit('rpc/res', response.model_dump(), room=sid)
    except:
        logger.exception(f"Error handling RPC request")

@app.get("/")
async def root():
    return {
        "message": "Kaa API Server",
        "version": "1.0.0",
        "methods": registry.list_methods()
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

asgi_app = socketio.ASGIApp(
    sio,
    other_asgi_app=app,
    socketio_path='/socket.io',
)

def setup_static_files(static_dir: str):
    """
    设置静态文件服务（用于生产环境）
    在开发环境中，Vite 会自己处理静态文件
    """
    import os
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
        logger.info(f"Mounted static files from: {static_dir}")
    else:
        logger.warning(f"Static directory not found: {static_dir}")

