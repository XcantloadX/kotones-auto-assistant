import logging
from typing import List, Tuple

from kaa.main.kaa import Kaa
from kaa.tasks import TASK_REGISTRY
from kotonebot.backend.context import task_registry
from kotonebot.core.bot import RunStatus

logger = logging.getLogger(__name__)


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

        self._task_status = {task.task: "pending" for task in TASK_REGISTRY.values()}

        def _on_stopped(reason: str, exception: Exception | None):
            self.is_running_all = False
            self.is_running_single = False
            self.is_stopping = False
            self._run_status = None

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

    def get_task_statuses(self) -> List[Tuple[str, str]]:
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
