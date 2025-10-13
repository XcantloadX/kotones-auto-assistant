"""
RPC 注册器和分发器
"""
import logging
import traceback
from typing import Callable, Any, Dict
from .models import RPCRequest, RPCResponse, RPCErrorResponse, RPCError

logger = logging.getLogger(__name__)


class RPCRegistry:
    """RPC 方法注册器"""
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
    
    def register(self, method: str, handler: Callable):
        """注册 RPC 方法"""
        if method in self._handlers:
            logger.warning(f"RPC method already registered: {method}")
        self._handlers[method] = handler
        logger.info(f"Registered RPC method: {method}")
    
    def decorator(self, method: str):
        """装饰器语法注册"""
        def wrapper(handler: Callable):
            self.register(method, handler)
            return handler
        return wrapper
    
    async def dispatch(self, request: RPCRequest) -> RPCResponse | RPCErrorResponse:
        """分发 RPC 请求"""
        try:
            # 查找处理器
            handler = self._handlers.get(request.method)
            if handler is None:
                return RPCErrorResponse(
                    id=request.id,
                    error=RPCError(
                        code="MethodNotFound",
                        message=f"Method not found: {request.method}"
                    )
                )
            
            # 调用处理器
            logger.debug(f"Dispatching RPC: {request.method}")
            params = request.params or {}
            
            # 判断是否是异步函数
            import inspect
            if inspect.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)
            
            return RPCResponse(
                id=request.id,
                result=result
            )
        
        except TypeError as e:
            # 参数错误
            logger.exception(f"Invalid parameters for {request.method}")
            return RPCErrorResponse(
                id=request.id,
                error=RPCError(
                    code="InvalidParams",
                    message=f"Invalid parameters: {str(e)}",
                    data={"params": request.params}
                )
            )
        
        except Exception as e:
            # 其他错误
            logger.exception(f"RPC handler error for {request.method}")
            
            error_code = type(e).__name__
            
            return RPCErrorResponse(
                id=request.id,
                error=RPCError(
                    code=error_code,
                    message=str(e),
                    data={
                        "traceback": traceback.format_exc(),
                        "type": type(e).__name__
                    }
                )
            )
    
    def list_methods(self) -> list[str]:
        """列出所有已注册的方法"""
        return sorted(self._handlers.keys())


# 全局注册器实例
registry = RPCRegistry()

