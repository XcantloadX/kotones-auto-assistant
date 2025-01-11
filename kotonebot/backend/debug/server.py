import time
import asyncio
import threading
from pathlib import Path
from collections import deque

import cv2
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi import FastAPI, WebSocket, HTTPException

from . import vars

app = FastAPI()

# 获取当前文件夹路径
CURRENT_DIR = Path(__file__).parent
APP_DIR = Path.cwd()

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(CURRENT_DIR)), name="static")

@app.get("/")
async def get_root():
    """返回 UI 页面"""
    return FileResponse(CURRENT_DIR / "ui.html")

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
        if key in vars._results:
            image = vars._results[key].image
        elif key in vars._images:
            image = vars._images[key]
        else:
            raise HTTPException(status_code=404, detail="Key not found")
        
        # 编码图片
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85, cv2.IMWRITE_JPEG_PROGRESSIVE, 1]
        _, buffer = cv2.imencode('.jpg', image, encode_params)
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
                message = message_queue.pop()
                await websocket.send_json(message)
            await asyncio.sleep(0.1)
    except:
        await websocket.close()

def send_ws_message(title: str, image: str, text: str = '', wait: bool = False):
    """发送 WebSocket 消息"""
    message = {
        "type": "visual",
        "data": {
            "image": {
                "type": "memory",
                "value": image
            },
            "name": title,
            "details": text
        }
    }
    message_queue.append(message)
    if wait:
        while len(message_queue) > 0:
            time.sleep(0.3)


thread = None
def start_server():
    global thread
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level='critical' if vars.debug.hide_server_log else None)
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

