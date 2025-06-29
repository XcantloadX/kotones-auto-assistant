import time
import logging
import threading
from typing import Literal

logger = logging.getLogger(__name__)

class FlowController:
    """
    一个用于控制任务执行流程（如停止、暂停、恢复）的类。

    这个类是线程安全的，提供了以下功能：

    * 停止任务执行（通过中断信号）
    * 暂停/恢复任务执行
    * 可中断和可暂停的 sleep 功能
    * 流程状态检查

    使用方法::

        controller = FlowController()

        # 在任务的关键路径上调用检查
        controller.check()

        # 使用可控制的 sleep
        controller.sleep(1.0)

        # 外部控制
        controller.request_pause()  # 暂停
        controller.request_resume()  # 恢复
        controller.request_stop()   # 停止
    """
    
    def __init__(self):
        self.interrupt_event: threading.Event = threading.Event()
        """中断事件，用于停止任务"""

        self.paused: bool = False
        """暂停标志"""

        self.pause_condition: threading.Condition = threading.Condition()
        """暂停条件变量，用于线程间同步"""
    
    def check(self) -> None:
        """
        检查当前流程状态。

        如果收到停止请求，则抛出 KeyboardInterrupt 异常。
        如果收到暂停请求，则阻塞直到恢复。

        这是核心的检查点方法，应在任务的关键路径上（如循环或等待前）调用。

        :raises KeyboardInterrupt: 当收到停止请求时
        """
        # 优先检查中断信号
        if self.interrupt_event.is_set():
            raise KeyboardInterrupt("User requested interrupt.")
        
        # 检查暂停状态
        with self.pause_condition:
            while self.paused:
                self.pause_condition.wait()
    
    def sleep(self, seconds: float) -> None:
        """
        一个可被中断和暂停的 sleep 方法。

        与标准的 time.sleep() 不同，这个方法会响应停止和暂停请求。
        在暂停状态下，计时器会暂停，恢复后继续计时。

        :param seconds: 睡眠时间（秒）
        :raises KeyboardInterrupt: 当收到停止请求时
        """
        with self.pause_condition:
            end_time = time.time() + seconds
            while True:
                self.check()  # 每次循环都检查状态
                remaining = end_time - time.time()
                if remaining <= 0:
                    break
                # 等待指定时间或直到被唤醒
                self.pause_condition.wait(timeout=remaining)
        
        # 结束后再次检查状态
        self.check()
    
    def request_interrupt(self) -> None:
        """
        请求停止任务。

        设置中断信号，所有正在执行的任务将在下一个检查点停止。
        停止的优先级高于暂停。
        """
        logger.info('Interrupt requested.')
        self.interrupt_event.set()
    
    def request_pause(self) -> None:
        """
        请求暂停任务。

        设置暂停标志，所有正在执行的任务将在下一个检查点暂停。
        如果任务已经暂停，此操作无效果。
        """
        with self.pause_condition:
            if not self.paused:
                logger.info('Pause requested.')
                self.paused = True
    
    def request_resume(self) -> None:
        """
        请求恢复任务。

        清除暂停标志并通知所有等待的线程恢复执行。
        如果任务没有暂停，此操作无效果。
        """
        with self.pause_condition:
            if self.paused:
                logger.info('Resume requested.')
                self.paused = False
                self.pause_condition.notify_all()
    
    def toggle_pause(self) -> bool:
        """
        切换暂停/恢复状态。

        :returns: 操作后的暂停状态。True 表示已暂停，False 表示已恢复。
        """
        with self.pause_condition:
            logger.info('Pause toggled.')
            if self.paused:
                self.paused = False
                self.pause_condition.notify_all()
                return False
            else:
                self.paused = True
                return True
    
    def clear_interrupt(self) -> None:
        """
        清除中断信号。

        用于任务正常结束或重启时重置状态。
        通常在开始新任务前调用。
        """
        self.interrupt_event.clear()
        logger.info('Interrupt cleared.')
    
    def reset(self) -> None:
        """
        重置流程控制器到初始状态。

        清除所有信号和状态，相当于重新创建一个新的控制器。
        """
        self.interrupt_event.clear()
        with self.pause_condition:
            if self.paused:
                self.paused = False
                self.pause_condition.notify_all()
        logger.info('FlowController reset.')
    
    @property
    def is_interrupted(self) -> bool:
        """
        检查是否收到中断请求。

        :returns: True 表示已收到中断请求
        """
        return self.interrupt_event.is_set()
    
    @property
    def is_paused(self) -> bool:
        """
        检查是否处于暂停状态。

        :returns: True 表示当前处于暂停状态
        """
        return self.paused
    
    @property
    def status(self) -> Literal['running', 'paused', 'interrupted']:
        """
        获取当前状态的字符串描述。

        :returns: 状态描述，可能的值：'running', 'paused', 'interrupted'
        """
        if self.is_interrupted:
            return 'interrupted'
        elif self.is_paused:
            return 'paused'
        else:
            return 'running'
    
    def __repr__(self) -> str:
        return f"FlowController(status='{self.status}')"