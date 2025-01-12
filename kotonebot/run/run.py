import pkgutil
import logging
import importlib

from kotonebot.backend.context import init_context
from kotonebot.backend.core import task_registry, action_registry

logger = logging.getLogger(__name__)

def initialize(module: str):
    """
    初始化并载入所有任务和动作。

    :param module: 主模块名。此模块及其所有子模块都会被载入。
    """
    logger.info('Initializing tasks and actions...')
    logger.debug(f'Loading module: {module}')
    # 加载主模块
    importlib.import_module(module)

    # 加载所有子模块
    pkg = importlib.import_module(module)
    for loader, name, is_pkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + '.'):
        logger.debug(f'Loading sub-module: {name}')
        try:
            importlib.import_module(name)
        except Exception as e:
            logger.error(f'Failed to load sub-module: {name}')
            logger.exception(f'Error: ')
    
    logger.info('Tasks and actions initialized.')
    logger.info(f'{len(task_registry)} task(s) and {len(action_registry)} action(s) loaded.')

def run(
    no_try: bool = False,
):
    """
    按优先级顺序运行所有任务。

    :param no_try: 是否不捕获异常。
    """
    tasks = sorted(task_registry.values(), key=lambda x: x.priority, reverse=True)
    for task in tasks:
        logger.info(f'Task started: {task.name}')
        if no_try:
            task.func()
        else:
            try:
                task.func()
            except Exception:
                logger.error(f'Task failed: {task.name}')
                logger.exception(f'Error: ')
        logger.info(f'Task finished: {task.name}')
    logger.info('All tasks finished.')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s')
    logger.setLevel(logging.DEBUG)
    logging.getLogger('kotonebot').setLevel(logging.DEBUG)
    init_context()
    initialize('kotonebot.tasks')
    run(no_try=True)


