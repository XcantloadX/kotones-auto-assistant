import time
import asyncio
import inspect
import threading
import traceback
import subprocess
from io import StringIO
from pathlib import Path
from typing import Literal
from collections import deque
from contextlib import redirect_stdout

import cv2
import uvicorn
from thefuzz import fuzz
from pydantic import BaseModel
from fastapi.responses import FileResponse, Response
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import kotonebot
import kotonebot.backend
import kotonebot.backend.context
from kotonebot.backend.core import HintBox, Image
from ..context import manual_context
from . import vars as debug_vars
from .vars import WSImage, WSMessageData, WSMessage, WSCallstack

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 获取当前文件夹路径
CURRENT_DIR = Path(__file__).parent

APP_DIR = Path.cwd()

class File(BaseModel):
    name: str
    full_path: str
    type: Literal["file", "dir"]

@app.get("/api/read_file")
async def read_file(path: str):
    """读取文件内容"""
    try:
        # 确保路径在当前目录下
        full_path = (APP_DIR / path).resolve()
        if not Path(full_path).is_relative_to(APP_DIR):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        # 添加缓存控制头
        headers = {
            "Cache-Control": "public, max-age=3600",  # 缓存1小时
            "ETag": f'"{hash(full_path)}"'  # 使用full_path的哈希值作为ETag
        }
        return FileResponse(full_path, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/read_memory")
async def read_memory(key: str):
    """读取内存中的数据"""
    try:
        image = None
        if (image := debug_vars._read_image(key)) is not None:
            pass
        else:
            raise HTTPException(status_code=404, detail="Key not found")
        
        # 编码图片
        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 4]
        _, buffer = cv2.imencode('.png', image, encode_params)
        # 添加缓存控制头
        headers = {
            "Cache-Control": "public, max-age=3600",  # 缓存1小时
            "ETag": f'"{hash(key)}"'  # 使用key的哈希值作为ETag
        }
        return Response(
            buffer.tobytes(), 
            media_type="image/jpeg",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screenshot")
def screenshot():
    from ..context import device
    img = device.screenshot()
    buff = cv2.imencode('.png', img)[1].tobytes()
    return Response(buff, media_type="image/png")

class RunCodeRequest(BaseModel):
    code: str

@app.post("/api/code/run")
async def run_code(request: RunCodeRequest):
    event = asyncio.Event()
    stdout = StringIO()
    code = f"from kotonebot import *\n" + request.code
    result = {}
    def _runner():
        nonlocal result
        from kotonebot.backend.context import vars as context_vars
        try:
            with manual_context():
                global_vars = dict(vars(kotonebot.backend.context))
                with redirect_stdout(stdout):
                    exec(code, global_vars)
            result = {"status": "ok", "result": stdout.getvalue()}
        except (Exception) as e:
            result = {"status": "error", "result": stdout.getvalue(), "message": str(e), "traceback": traceback.format_exc()}
        except KeyboardInterrupt as e:
            result = {"status": "error", "result": stdout.getvalue(), "message": str(e), "traceback": traceback.format_exc()}
        finally:
            context_vars.flow.clear_interrupt()
        event.set()
    threading.Thread(target=_runner, daemon=True).start()
    await event.wait()
    return result

@app.get("/api/code/stop")
async def stop_code():
    from kotonebot.backend.context import vars
    vars.flow.request_interrupt()
    while vars.flow.is_interrupted:
        await asyncio.sleep(0.1)
    return {"status": "ok"}

@app.get("/api/fs/list_dir")
def list_dir(path: str) -> list[File]:
    result = []
    for item in Path(path).iterdir():
        result.append(File(
            name=item.name,
            full_path=str(item),
            type="file" if item.is_file() else "dir"
        ))
    return result

@app.get("/api/resources/autocomplete")
def autocomplete(class_path: str) -> list[str]:
    from kotonebot.kaa.tasks import R
    class_names = class_path.split(".")[:-1]
    target_class = R
    # 定位到目标类
    for name in class_names:
        target_class = getattr(target_class, name, None)
        if target_class is None:
            return []
    # 获取目标类的所有属性
    attrs = [attr for attr in dir(target_class) if not attr.startswith("_")]
    filtered_attrs = []
    for attr in attrs:
        if inspect.isclass(getattr(target_class, attr)):
            filtered_attrs.append(attr)
        elif isinstance(getattr(target_class, attr), (Image, HintBox)):
            filtered_attrs.append(attr)  
    attrs = filtered_attrs
    # 排序
    attrs.sort(key=lambda x: fuzz.ratio(x, class_path), reverse=True)
    return attrs

@app.get("/api/ping")
async def ping():
    return {"status": "ok"}

message_queue = deque()
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if len(message_queue) > 0:
                message = message_queue.popleft()
                await websocket.send_json(message)
            await asyncio.sleep(0.1)
    except:
        await websocket.close()

def send_ws_message(title: str, image: list[str], text: str = '', callstack: list[WSCallstack] = [], wait: bool = False):
    """发送 WebSocket 消息"""
    message = WSMessage(
        type="visual",
        data=WSMessageData(
            image=WSImage(type="memory", value=image),
            name=title,
            details=text,
            timestamp=int(time.time() * 1000),
            callstack=callstack
        )
    )
    message_queue.append(message.dict())
    if wait:
        while len(message_queue) > 0:
            time.sleep(0.3)


thread = None
def start_server():
    global thread
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level='critical' if debug_vars.debug.hide_server_log else None)
    if thread is None:
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

def wait_message_all_done():
    global thread
    def _wait():
        while len(message_queue) > 0:
            time.sleep(0.1)
    if thread is not None:
        threading.Thread(target=_wait, daemon=True).start()

if __name__ == "__main__":
    debug_vars.debug.hide_server_log = False
    process = subprocess.Popen(["pylsp", "--port", "5479", "--ws"])
    print("LSP started. PID=", process.pid)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level='critical' if debug_vars.debug.hide_server_log else None)
    process.kill()