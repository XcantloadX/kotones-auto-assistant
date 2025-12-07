import logging
from typing import List

from kaa.config.produce import ProduceSolution, ProduceSolutionManager, ProduceData

logger = logging.getLogger(__name__)


class ProduceSolutionService:
    """
    Service layer for managing produce solutions.
    This service acts as a wrapper around ProduceSolutionManager,
    decoupling the UI/facade from the direct file system operations.
    """

    def __init__(self):
        self._manager = ProduceSolutionManager()

    def list_solutions(self) -> List[ProduceSolution]:
        """
        Retrieves a list of all available produce solutions.

        :return: A list of ProduceSolution objects.
        """
        return self._manager.list()

    def get_solution(self, solution_id: str) -> ProduceSolution:
        """
        Retrieves a single produce solution by its ID.

        :param solution_id: The ID of the solution to retrieve.
        :return: The ProduceSolution object.
        :raises ProduceSolutionNotFoundError: If no solution with the given ID is found.
        """
        return self._manager.read(solution_id)

    def create_solution(self, name: str = "新培育方案") -> ProduceSolution:
        """
        Creates a new, empty produce solution with a unique ID and saves it.

        :param name: The name for the new solution.
        :return: The newly created ProduceSolution object.
        """
        new_solution = self._manager.new(name)
        self._manager.save(new_solution.id, new_solution)
        logger.info(f"Created new produce solution '{name}' with ID {new_solution.id}")
        return new_solution

    def delete_solution(self, solution_id: str) -> None:
        """
        Deletes a produce solution by its ID.

        :param solution_id: The ID of the solution to delete.
        """
        self._manager.delete(solution_id)
        logger.info(f"Deleted produce solution with ID {solution_id}")

    def save_solution(self, solution: ProduceSolution) -> None:
        """
        Saves a ProduceSolution object to the filesystem.
        This can be used for both updating existing solutions and saving new ones.

        :param solution: The ProduceSolution object to save.
        """
        self._manager.save(solution.id, solution)
        logger.info(f"Saved produce solution '{solution.name}' with ID {solution.id}")

    def update_solution_data(self, solution_id: str, name: str, description: str, data: ProduceData) -> ProduceSolution:
        """
        Updates an existing produce solution with new data and saves it.

        :param solution_id: The ID of the solution to update.
        :param name: The new name for the solution.
        :param description: The new description for the solution.
        :param data: The new ProduceData object.
        :return: The updated ProduceSolution object.
        """
        solution = self.get_solution(solution_id)
        solution.name = name
        solution.description = description
        solution.data = data
        self.save_solution(solution)
        return solution
