"""
KaaRuntime 适配器
封装 Kaa 实例的生命周期和运行状态
"""
import logging
import asyncio
from typing import Optional, Any
from datetime import datetime

from ...main import Kaa
from kotonebot.backend.context import vars
from kotonebot.errors import ContextNotInitializedError

from ..events import notify, Topics

logger = logging.getLogger(__name__)


class KaaRuntime:
    """
    Kaa 运行时封装
    负责管理 Kaa 实例的生命周期、状态监控和事件推送
    """
    
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self._kaa: Optional[Kaa] = None
        self._is_running = False
        self._is_single_task_running = False
        self._is_stopping = False
        self._run_status = None
        self._status_monitor_task: Optional[asyncio.Task] = None
    
    def initialize(self):
        """初始化 Kaa 实例"""
        if self._kaa is not None:
            logger.warning("Kaa already initialized")
            return
        
        logger.info(f"Initializing Kaa with config: {self.config_path}")
        self._kaa = Kaa(self.config_path)
        
        # 添加文件日志
        log_path = f'logs/web_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
        self._kaa.add_file_logger(log_path)
        
        # 初始化上下文
        self._kaa.initialize()
        logger.info("Kaa initialized successfully")
    
    @property
    def kaa(self) -> Kaa:
        """获取 Kaa 实例"""
        if self._kaa is None:
            raise RuntimeError("Kaa not initialized. Call initialize() first.")
        return self._kaa
    
    def get_status(self) -> dict[str, Any]:
        """获取当前运行状态"""
        try:
            is_paused = False
            try:
                is_paused = vars.flow.is_paused
            except (ContextNotInitializedError, AttributeError):
                pass
            
            status = {
                'running': self._is_running or self._is_single_task_running,
                'paused': is_paused,
            }
            
            # 添加运行状态详情
            if self._run_status is not None:
                status['current_task'] = getattr(self._run_status, 'current_task', None)
                status['message'] = getattr(self._run_status, 'message', None)
                
                # 如果有任务列表
                if hasattr(self._run_status, 'tasks'):
                    tasks = self._run_status.tasks
                    if tasks:
                        # 找到正在运行的任务
                        running_tasks = [t for t in tasks if getattr(t, 'status', '') == 'running']
                        if running_tasks:
                            status['current_task'] = running_tasks[0].name
            
            return status
        
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                'running': False,
                'paused': False,
                'error': str(e)
            }
    
    async def start_all(self):
        """启动所有任务"""
        if self._is_running:
            raise RuntimeError("Already running")
        
        logger.info("Starting all tasks")
        self._is_running = True
        self._run_status = self.kaa.start_all()
        
        # 启动状态监控
        await self._start_status_monitor()
        
        # 立即推送状态
        await notify(Topics.STATUS_RUN, self.get_status())
        
        return {"success": True}
    
    async def stop_all(self):
        """停止所有任务"""
        if not self._is_running:
            return {"success": True, "message": "Not running"}
        
        logger.info("Stopping all tasks")
        self._is_stopping = True
        
        # 如果当前处于暂停状态，先恢复再停止
        try:
            if vars.flow.is_paused:
                logger.info("Resuming before stop")
                vars.flow.request_resume()
        except (ContextNotInitializedError, AttributeError):
            pass
        
        self._is_running = False
        
        if self._run_status:
            self._run_status.interrupt()
        
        # 停止状态监控
        await self._stop_status_monitor()
        
        # 推送停止状态
        await notify(Topics.STATUS_RUN, self.get_status())
        
        self._is_stopping = False
        return {"success": True}
    
    async def start_task(self, task_name: str):
        """启动单个任务"""
        if self._is_single_task_running:
            raise RuntimeError("A task is already running")
        
        logger.info(f"Starting task: {task_name}")
        self._is_single_task_running = True
        
        # 导入任务注册表
        from kotonebot.backend.context import task_registry
        task = task_registry.get(task_name)
        if task is None:
            self._is_single_task_running = False
            raise ValueError(f"Task not found: {task_name}")
        
        self._run_status = self.kaa.start([task])
        
        # 启动状态监控
        await self._start_status_monitor()
        
        # 推送任务状态
        await notify(Topics.STATUS_TASK, {
            'name': task_name,
            'running': True
        })
        
        return {"success": True}
    
    async def stop_task(self):
        """停止当前任务"""
        if not self._is_single_task_running:
            return {"success": True, "message": "No task running"}
        
        logger.info("Stopping current task")
        
        # 如果当前处于暂停状态，先恢复再停止
        try:
            if vars.flow.is_paused:
                vars.flow.request_resume()
        except (ContextNotInitializedError, AttributeError):
            pass
        
        self._is_single_task_running = False
        
        if self._run_status:
            self._run_status.interrupt()
        
        # 停止状态监控
        await self._stop_status_monitor()
        
        # 推送停止状态
        await notify(Topics.STATUS_TASK, {
            'name': '',
            'running': False
        })
        
        return {"success": True}
    
    async def pause(self):
        """暂停"""
        try:
            logger.info("Pausing")
            vars.flow.request_pause()
            await notify(Topics.STATUS_RUN, self.get_status())
            return {"success": True}
        except (ContextNotInitializedError, AttributeError) as e:
            raise RuntimeError("Cannot pause: context not initialized") from e
    
    async def resume(self):
        """恢复"""
        try:
            logger.info("Resuming")
            vars.flow.request_resume()
            await notify(Topics.STATUS_RUN, self.get_status())
            return {"success": True}
        except (ContextNotInitializedError, AttributeError) as e:
            raise RuntimeError("Cannot resume: context not initialized") from e
    
    async def toggle_pause(self):
        """切换暂停/恢复"""
        try:
            if vars.flow.is_paused:
                await self.resume()
            else:
                await self.pause()
            return {"success": True}
        except (ContextNotInitializedError, AttributeError) as e:
            raise RuntimeError("Cannot toggle pause: context not initialized") from e
    
    async def _start_status_monitor(self):
        """启动状态监控任务"""
        if self._status_monitor_task is not None:
            return
        
        async def monitor():
            """定期推送状态更新"""
            try:
                while self._is_running or self._is_single_task_running:
                    await notify(Topics.STATUS_RUN, self.get_status())
                    await asyncio.sleep(1)  # 每秒推送一次
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Status monitor error: {e}")
        
        self._status_monitor_task = asyncio.create_task(monitor())
    
    async def _stop_status_monitor(self):
        """停止状态监控任务"""
        if self._status_monitor_task is not None:
            self._status_monitor_task.cancel()
            try:
                await self._status_monitor_task
            except asyncio.CancelledError:
                pass
            self._status_monitor_task = None


# 全局运行时实例
_runtime: Optional[KaaRuntime] = None


def get_runtime(config_path: str = 'config.json') -> KaaRuntime:
    """获取全局运行时实例"""
    global _runtime
    if _runtime is None:
        _runtime = KaaRuntime(config_path)
        _runtime.initialize()
    return _runtime

