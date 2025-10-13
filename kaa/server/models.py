"""
RPC 错误模型和响应格式
"""
from typing import Any, Optional
from pydantic import BaseModel


class RPCError(BaseModel):
    """RPC 错误响应"""
    code: str
    message: str
    data: Optional[dict[str, Any]] = None


class RPCRequest(BaseModel):
    """RPC 请求"""
    id: str
    method: str
    params: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None


class RPCResponse(BaseModel):
    """RPC 成功响应"""
    id: str
    result: Any


class RPCErrorResponse(BaseModel):
    """RPC 错误响应"""
    id: str
    error: RPCError


class RPCNotify(BaseModel):
    """服务端通知"""
    topic: str
    data: Any
    ts: int


class RPCStream(BaseModel):
    """流式响应"""
    id: str
    event: str  # progress, data, end, error
    data: Optional[Any] = None
    progress: Optional[dict[str, int]] = None

