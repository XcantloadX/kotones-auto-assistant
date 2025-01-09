from pathlib import Path
from collections import deque
import asyncio

import cv2
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

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
    print('read_memory', key)
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
                # print('send message', message)
                await websocket.send_json(message)
            await asyncio.sleep(0.1)
            # data = await websocket.receive_text()
            # try:
            #     message = json.loads(data)
            #     if message["type"] == "visual":
            #         # 处理可视化消息
            #         image_data = message["data"]["image"]
            #         if image_data["type"] == "path":
            #             # 从文件读取
            #             full_path = (CURRENT_DIR / image_data["value"]).resolve()
            #             if not str(full_path).startswith(str(CURRENT_DIR)):
            #                 await websocket.send_json({"error": "Access denied"})
            #                 continue
                        
            #             if not full_path.exists():
            #                 await websocket.send_json({"error": "File not found"})
            #                 continue
                        
            #             with open(full_path, 'rb') as f:
            #                 content = base64.b64encode(f.read()).decode()
            #         else:  # memory
            #             key = image_data["value"]
            #             if key not in vars._results:
            #                 await websocket.send_json({"error": "Key not found"})
            #                 continue
                        
            #             result = vars._results[key]
            #             _, buffer = cv2.imencode('.png', result.image)
            #             content = base64.b64encode(buffer).decode()
                    
            #         # 发送响应
            #         await websocket.send_json({
            #             "type": "visual",
            #             "data": {
            #                 "image": content,
            #                 "name": message["data"]["name"],
            #                 "details": message["data"]["details"]
            #             }
            #         })
            # except json.JSONDecodeError:
            #     await websocket.send_json({"error": "Invalid JSON"})
            # except Exception as e:
            #     await websocket.send_json({"error": str(e)})
    except:
        await websocket.close()

# 修改 vars.py 中的 result 函数
def send_ws_message(title: str, image: str, text: str = ''):
    """发送 WebSocket 消息"""
    # 这个函数将在 vars.py 中被调用
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
    # 发送消息到所有连接的客户端
    message_queue.append(message)
