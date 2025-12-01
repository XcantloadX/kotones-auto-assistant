import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

from kaa.main.kaa import Kaa
from kotonebot.backend.context import task_registry, vars as context_vars, Task
from kotonebot.backend.bot import RunStatus
from kotonebot.errors import ContextNotInitializedError

logger = logging.getLogger(__name__)


class TaskControlService:
    """
    Manages the lifecycle of Kaa tasks, including starting, stopping,
    and pausing. It encapsulates the state related to task execution.
    """

    def __init__(self, kaa_instance: Kaa):
        self._kaa = kaa_instance
        self.run_status: RunStatus | None = None
        self.is_running_all: bool = False
        self.is_running_single: bool = False
        self.is_stopping: bool = False
        self.task_start_time: Optional[datetime] = None

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
        self.task_start_time = datetime.now()
        self.run_status = self._kaa.start_all()

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
        self.task_start_time = datetime.now()
        self.run_status = self._kaa.start([task])

    def stop_tasks(self) -> None:
        """Stops the currently running tasks."""
        if not self.is_running() or self.is_stopping:
            logger.warning("No tasks are running or tasks are already stopping.")
            return

        logger.info("Stopping tasks...")
        self.is_stopping = True
        try:
            if context_vars.flow.is_paused:
                logger.info("Tasks are paused, resuming before stopping.")
                context_vars.flow.request_resume()
        except ContextNotInitializedError:
            pass # Context might not be ready if stopping very early

        if self.run_status:
            self.run_status.interrupt()

    def get_task_statuses(self) -> List[Tuple[str, str]]:
        """
        Gets the current status of all registered tasks.

        :return: A list of tuples, where each tuple contains the task name and its status.
        """
        if not self.run_status:
            return [(task.name, "pending") for task in task_registry.values()]

        # Reset running flags if the underlying run_status is no longer running
        if not self.run_status.running:
            self.is_running_all = False
            self.is_running_single = False
            self.is_stopping = False
            self.task_start_time = None

        status_list: List[Tuple[str, str]] = []
        for task_status in self.run_status.tasks:
            status_list.append((task_status.task.name, task_status.status))
        return status_list

    def toggle_pause(self) -> str:
        """
Toggles the pause/resume state of the running tasks.

:return: The new state ("paused" or "resumed").
        """
        try:
            if context_vars.flow.is_paused:
                context_vars.flow.request_resume()
                logger.info("Tasks resumed.")
                return "resumed"
            else:
                context_vars.flow.request_pause()
                logger.info("Tasks paused.")
                return "paused"
        except ContextNotInitializedError:
            logger.warning("Cannot toggle pause, context not initialized.")
            return "unknown"

    def get_pause_status(self) -> str:
        """
        Gets the current pause status.

        :return: "paused", "resumed", or "unknown".
        """
        try:
            return "paused" if context_vars.flow.is_paused else "resumed"
        except ContextNotInitializedError:
            return "unknown"

    def get_all_task_names(self) -> List[str]:
        """Returns a list of all registered task names."""
        return list(task_registry.keys())

    def get_task_runtime(self) -> Optional[timedelta]:
        """
        Gets the current task runtime.

        :return: A timedelta object representing the runtime, or None if no task is running.
        """
        if self.task_start_time is None:
            return None
        return datetime.now() - self.task_start_time
