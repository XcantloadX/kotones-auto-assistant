import logging
import os
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Tuple

from kaa.main.kaa import Kaa
from kaa.application.services.config_service import ConfigService, ConfigValidationError
from kaa.application.services.produce_solution_service import ProduceSolutionService
from kaa.application.services.task_service import TaskService
from kaa.application.services.update_service import UpdateService
from kaa.application.services.feedback_service import FeedbackService
from kaa.application.core.idle_mode import IdleModeManager
from kaa.config.produce import ProduceSolution
from kotonebot.errors import ContextNotInitializedError

logger = logging.getLogger(__name__)

class KaaFacade:
    """
    The Facade provides a simplified interface to the application's core services,
    acting as a single bridge between the UI (View) and the business logic (Services).
    It orchestrates service interactions and manages application state flow.
    """

    def __init__(self, kaa_instance: Kaa):
        # Core services
        self.config_service = ConfigService()
        self.produce_solution_service = ProduceSolutionService()
        self.task_service = TaskService(kaa_instance)

        # Other existing services
        self.update_service = UpdateService()
        self.feedback_service = FeedbackService()
        self.idle_mgr = self._setup_idle_manager()

        self._kaa = kaa_instance

    def _setup_idle_manager(self) -> IdleModeManager:
        """Initializes and configures the IdleModeManager."""

        def is_task_running():
            try:
                return self.task_service.is_running() and not self.task_service.is_stopping
            except ContextNotInitializedError:
                return False

        def is_task_paused():
            try:
                status = self.task_service.get_pause_status()
                return status is True
            except ContextNotInitializedError:
                return False

        return IdleModeManager(
            get_is_running=is_task_running,
            get_is_paused=is_task_paused,
            get_config=lambda: self.config_service.get_options().idle,
        )

    # --- Task Control ---

    def start_all_tasks(self):
        """Starts all tasks and notifies the idle manager."""
        self.task_service.start_all_tasks()
        self.idle_mgr.notify_on_start()

    def stop_all_tasks(self):
        """Stops all running tasks and notifies the idle manager."""
        self.task_service.stop_tasks()
        self.idle_mgr.notify_on_stop()

    def get_run_status(self) -> Dict[str, Any]:
        """
        Gets the comprehensive status for the main run button.
        :return: A dictionary with 'text' and 'interactive' keys for the button.
        """
        tcs = self.task_service
        if not tcs.is_running_all:
            return {"text": "启动", "interactive": True}
        if tcs.is_stopping:
            return {"text": "停止中...", "interactive": False}
        return {"text": "停止", "interactive": True}

    def get_task_statuses(self) -> List[Tuple[str, str]]:
        """Gets a list of all tasks and their current statuses."""
        return self.task_service.get_task_statuses()

    def toggle_pause(self) -> bool | None:
        """Toggles the pause/resume state of tasks."""
        return self.task_service.toggle_pause()

    def get_pause_button_status(self) -> Dict[str, Any]:
        """

        Gets the status for the pause button.
        :return: A dictionary with 'text' and 'interactive' keys for the button.
        """
        pause_status = self.task_service.get_pause_status()
        is_paused = pause_status is True
        is_stoppable = not self.task_service.is_stopping
        can_pause = self.task_service.is_running() and is_stoppable

        return {
            "text": "恢复" if is_paused else "暂停",
            "interactive": can_pause,
        }

    def get_task_runtime(self) -> str:
        """
        Gets the current task runtime as a formatted string.
        :return: A string representing the runtime (e.g., "00:05:23"), or "未运行" if no task is running.
        """
        runtime = self.task_service.get_task_runtime()
        if runtime is None:
            return "未运行"
        
        total_seconds = int(runtime.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # --- Configuration ---

    def get_all_configs(self) -> Tuple[Any, Any]:
        """
        Gets all configuration objects.
        :return: A tuple of (root_config, current_user_config).
        """
        return self.config_service.get_root_config(), self.config_service.get_current_user_config()

    def save_configs(self):
        """
        Saves the current configuration and re-initializes Kaa.
        The UI is responsible for updating the config object in ConfigService before calling this.
        """
        try:
            self.config_service.save()
            logger.info("Configuration saved and Kaa re-initialized.")
            return "设置已保存并应用！"
        except ConfigValidationError as e:
            logger.warning(f"Configuration validation failed: {e}")
            raise  # Re-raise for the view to handle
        except Exception as e:
            logger.error(f"Failed to save or reload config: {e}", exc_info=True)
            raise RuntimeError("设置已保存，但重新加载失败，请重启程序。") from e

    # --- Produce Solutions ---

    def list_produce_solutions(self) -> List[ProduceSolution]:
        """Lists all produce solutions."""
        return self.produce_solution_service.list_solutions()

    def get_produce_solution(self, solution_id: str) -> ProduceSolution:
        """Gets a single produce solution by ID."""
        return self.produce_solution_service.get_solution(solution_id)

    def create_produce_solution(self, name: str) -> ProduceSolution:
        """Creates a new produce solution."""
        return self.produce_solution_service.create_solution(name)

    def delete_produce_solution(self, solution_id: str):
        """Deletes a produce solution."""
        # Prevent deleting the currently selected solution
        selected_id = self.config_service.get_options().produce.selected_solution_id
        if solution_id == selected_id:
            raise ValueError("不可删除当前正在使用的培育方案。")
        self.produce_solution_service.delete_solution(solution_id)

    def save_produce_solution(self, solution: ProduceSolution):
        """Saves a produce solution."""
        self.produce_solution_service.save_solution(solution)

    # --- Misc ---
    def export_logs_as_zip(self) -> str:
        # This logic was in gr.py, moving it here.
        # It doesn't neatly fit a service, but facade is ok for now.
        if not os.path.exists('logs'):
            return "logs 文件夹不存在"
        timestamp = datetime.now().strftime('%y-%m-%d-%H-%M-%S')
        zip_filename = f'logs-{timestamp}.zip'
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, _, files in os.walk('logs'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, 'logs')
                    zipf.write(file_path, arcname)
        return f"已导出到 {zip_filename}"
