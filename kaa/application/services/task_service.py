import logging
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import List

from kaa.main.kaa import Kaa
from kaa.tasks import TASK_REGISTRY
from kotonebot.backend.context import Task, task_registry
from kotonebot.core.bot import BotStopReason, RunStatus

logger = logging.getLogger(__name__)

# 后台任务线程 join 超时（秒）。正常 device.stop() 收尾为秒级，
# 30s 足以区分 hang 与慢。超时按 fast-fail 抛异常，见 _join_worker_thread。
_JOIN_TIMEOUT_SEC = 30.0
_JOIN_POLL_SEC = 0.5


@dataclass(frozen=True)
class RunOutcome:
    """一次阻塞运行的结局快照（跨线程摆渡，调用方定政策）。

    后台线程的异常无法自动抛到等待线程，只能经 stopped 事件记下、
    再以此对象交还调用方。正常结局（COMPLETED/USER_REQUEST）也是
    返回值而非异常——抛不抛由调用方经 raise_if_failed() 定政策，
    服务层不焊死。
    """

    reason: BotStopReason
    """停机原因（COMPLETED / USER_REQUEST / ERROR）。"""
    exception: Exception | None = None
    """ERROR 时携带的原始异常（保 traceback，供调用方重抛），其余为 None。"""
    timed_out: bool = False
    """预留：单次运行时间上限触发的停机置 True。目前恒 False，占位不生效。"""

    def raise_if_failed(self) -> None:
        """ERROR 且携带明确异常时重抛原异常，其余静默返回。

        ERROR 但 exception 为 None 时不抛（bot.py 触发 ERROR 总是带参，
        此分支理论上不可达；未知状态不误抛，排查靠日志与返回值）。
        """
        if self.reason == BotStopReason.ERROR and self.exception is not None:
            raise self.exception


class TaskService:
    """
    Manages the lifecycle of Kaa tasks, including starting, stopping,
    and pausing. It encapsulates the state related to task execution.
    """

    def __init__(self, kaa_instance: Kaa):
        self._kaa = kaa_instance
        self.is_running_all: bool = False
        self.is_running_single: bool = False
        self.is_stopping: bool = False
        self._run_status: RunStatus | None = None
        # CLI 退出语义所需：记录最近一次 stopped 的原因与异常。
        # 未发生过任何一次 run 时为 None，对应只读属性 fast-fail。
        self._last_stop_reason: BotStopReason | None = None
        self._last_exception: Exception | None = None

        self._task_status = {info.func.task: "pending" for info in TASK_REGISTRY.values()}

        def _on_stopped(reason: BotStopReason, exception: Exception | None):
            self.is_running_all = False
            self.is_running_single = False
            self.is_stopping = False
            self._run_status = None
            self._last_stop_reason = reason
            self._last_exception = exception
            for task in self._task_status:
                if self._task_status[task] == 'running':
                    self._task_status[task] = 'pending'

        def _on_task_status_changed(task, status: str):
            self._task_status[task] = status

        self._kaa.events.stopped += _on_stopped
        self._kaa.events.task_status_changed += _on_task_status_changed

    def is_running(self) -> bool:
        """Checks if any task (either all or single) is currently running."""
        return self.is_running_all or self.is_running_single

    def start_all_tasks(self) -> None:
        """Starts all registered tasks."""
        if self.is_running():
            logger.warning("Cannot start all tasks, a task is already running.")
            return

        logger.info("Starting all tasks...")
        self.is_running_all = True
        self.is_stopping = False
        self._run_status = self._kaa.start_all()

    def start_single_task(self, task_name: str) -> None:
        """
        Starts a single task by its name.

        :param task_name: The name of the task to start.
        :raises ValueError: If the task name is not found.
        """
        if self.is_running():
            logger.warning(f"Cannot start task '{task_name}', a task is already running.")
            return

        task = task_registry.get(task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found in task registry.")

        logger.info(f"Starting single task: {task_name}")
        self.is_running_single = True
        self.is_stopping = False
        self._run_status = self._kaa.start([task])

    def _wait_blocking(self, thread: threading.Thread) -> RunOutcome:
        """主线程阻塞等待当前 run 结束，返回本次运行的结局快照。

        语义 = while is_running: sleep(0.5) 轮询 stopped 事件 + join 后台线程。
        Ctrl+C 语义说明：原来 CLI 走 Kaa.run()（当前线程阻塞跑），
        KeyboardInterrupt 由 bot 主循环捕获并触发 stopped(USER_REQUEST)；
        统一后 bot 跑在 Kaa.start() 起的后台线程，主线程的 KeyboardInterrupt
        只能在这里捕获，转调 stop_tasks() 请求停机，再等待 stopped 事件后返回。
        退出语义等价（正常收尾、进程退出码 0），但上报的 reason 可能为
        COMPLETED 而非 USER_REQUEST（停机经 ctx.stop()/flow 中断走正常收尾）。

        注意：stopped 事件在 KotoneBot.run 的 finally(device.stop()) 之前触发，
        仅轮询 is_running 会在后台线程仍做 device.stop() 收尾时提前返回。
        因此轮询结束后必须 join 后台线程（见 _join_worker_thread），保证
        run_all_blocking 等返回时后台线程已彻底退出。调用方必须在 start
        成功后立刻捕获 run_status.thread 传入——_on_stopped 会把
        self._run_status 置 None，事后取不到句柄。

        :param thread: Kaa.start() 起的后台任务线程（调用方 start 后立刻捕获）。
        :raises RuntimeError: 等待结束仍无 stopped 记录、或 join 超时时抛出。
        """
        try:
            while self.is_running():
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping tasks...")
            self.stop_tasks()
            while self.is_running():
                time.sleep(0.5)
        if self._last_stop_reason is None:
            raise RuntimeError(
                "Task run finished but no stop reason was recorded; "
                "expected stopped event from KotoneBot.run()."
            )
        self._join_worker_thread(thread)
        return RunOutcome(reason=self._last_stop_reason, exception=self._last_exception)

    def _join_worker_thread(self, thread: threading.Thread) -> None:
        """等待后台任务线程彻底退出（含 finally 内 device.stop() 收尾）。

        :param thread: 后台任务线程。
        :raises RuntimeError: 超过 _JOIN_TIMEOUT_SEC 线程仍存活时抛出，
            不做 silent 返回（否则后台变野线程还正常退出，违背 fast-fail）。
        """
        deadline = time.monotonic() + _JOIN_TIMEOUT_SEC
        while thread.is_alive():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(
                    f"Background task thread did not exit within {_JOIN_TIMEOUT_SEC:g}s "
                    f"after stopped event (last_stop_reason={self._last_stop_reason}); "
                    f"thread={thread!r}. device.stop() may be hanging."
                )
            try:
                thread.join(timeout=min(_JOIN_POLL_SEC, remaining))
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received while joining worker thread...")
                if self.is_running():
                    self.stop_tasks()

    def run_all_blocking(self) -> RunOutcome:
        """阻塞运行全部任务（start_all_tasks + 主线程等待），供 CLI 使用。

        :raises RuntimeError: 已有任务在运行时抛出，不做 silent 等待/降级。
        """
        if self.is_running():
            raise RuntimeError(
                "Cannot run all tasks blocking: a task is already running."
            )
        self.start_all_tasks()
        if not self.is_running():
            raise RuntimeError(
                "Failed to start all tasks: TaskService is not running after start_all_tasks()."
            )
        run_status = self._run_status
        if run_status is None:
            raise RuntimeError(
                "TaskService is running but run status handle is missing; "
                "expected RunStatus from Kaa.start_all()."
            )
        return self._wait_blocking(run_status.thread)

    def run_tasks_blocking(self, tasks: Iterable[Task]) -> RunOutcome:
        """阻塞运行指定的任务列表，供 CLI 使用。

        批量 run 计为 is_running_all（与 start_all_tasks 同一标志位）。

        :param tasks: 要运行的任务可迭代对象。
        :raises RuntimeError: 已有任务在运行、或任务列表为空、或启动后未进入
            运行态时抛出，不做 silent 返回/降级。
        """
        if self.is_running():
            raise RuntimeError(
                "Cannot run tasks blocking: a task is already running."
            )
        task_list = list(tasks)
        if not task_list:
            raise RuntimeError(
                "Cannot run tasks blocking: task list is empty."
            )
        logger.info("Starting %d task(s)...", len(task_list))
        self.is_running_all = True
        self.is_stopping = False
        self._run_status = self._kaa.start(task_list)
        if not self.is_running():
            raise RuntimeError(
                "Failed to start tasks: TaskService is not running after start()."
            )
        run_status = self._run_status
        if run_status is None:
            raise RuntimeError(
                "TaskService is running but run status handle is missing; "
                "expected RunStatus from Kaa.start()."
            )
        return self._wait_blocking(run_status.thread)

    def run_single_blocking(self, task_name: str) -> RunOutcome:
        """阻塞运行单个任务（start_single_task + 主线程等待），供 CLI 使用。

        :param task_name: 任务名称。
        :raises ValueError: 任务名不存在时抛出（透传 start_single_task）。
        :raises RuntimeError: 已有任务在运行时抛出，不做 silent 等待/降级。
        """
        if self.is_running():
            raise RuntimeError(
                f"Cannot run task '{task_name}' blocking: a task is already running."
            )
        self.start_single_task(task_name)
        if not self.is_running():
            raise RuntimeError(
                f"Failed to start task '{task_name}': TaskService is not running after start_single_task()."
            )
        run_status = self._run_status
        if run_status is None:
            raise RuntimeError(
                f"TaskService is running task '{task_name}' but run status handle is missing; "
                "expected RunStatus from Kaa.start()."
            )
        return self._wait_blocking(run_status.thread)

    def stop_tasks(self) -> None:
        """Stops the currently running tasks."""
        if not self.is_running() or self.is_stopping:
            logger.warning("No tasks are running or tasks are already stopping.")
            return

        logger.info("Stopping tasks...")
        self.is_stopping = True
        if self._run_status is not None:
            self._run_status.interrupt()
        self._kaa.stop()

    def get_task_statuses(self) -> List[tuple[str, str]]:
        """
        Gets the current status of all registered tasks.

        :return: A list of tuples, where each tuple contains the task name and its status.
        """
        return [(task.name, status) for task, status in self._task_status.items()]

    def toggle_pause(self) -> bool | None:
        """
        Toggles the pause/resume state of the running tasks.

        :return: True if paused, False if resumed, None if no active task.
        """
        run = self._run_status
        if run is None or not run.running:
            logger.warning("Cannot toggle pause, no active task.")
            return None
        if run.is_paused:
            run.resume()
            logger.info("Tasks resumed.")
            return False
        else:
            run.pause()
            logger.info("Tasks paused.")
            return True

    def get_pause_status(self) -> bool | None:
        """
        Gets the current pause status.

        :return: True if paused, False if running, None if no active task.
        """
        run = self._run_status
        if run is None:
            return None
        return run.is_paused

    def request_pause(self) -> None:
        """Requests pause of the running task. Safe to call from any thread."""
        if self._run_status is not None:
            self._run_status.pause()

    def request_resume(self) -> None:
        """Requests resume of a paused task. Safe to call from any thread."""
        if self._run_status is not None:
            self._run_status.resume()

    def get_all_task_names(self) -> List[str]:
        """Returns a list of all registered task names."""
        return list(task_registry.keys())
