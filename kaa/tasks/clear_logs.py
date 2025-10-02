import logging
from pathlib import Path
from datetime import datetime, timedelta

from kotonebot import task

logger = logging.getLogger(__name__)

@task('清理日志')
def clear_logs():
    """清理 logs 目录下超过 7 天的日志文件"""
    log_dir = Path('logs')
    if not log_dir.exists():
        return
    
    now = datetime.now()
    cutoff_date = now - timedelta(days=7)
    
    logger.info('Clearing logs...')
    for file in log_dir.glob('*.log'):
        try:
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if mtime < cutoff_date:
                file.unlink()
                logger.info(f'Removed file {file}.')
        except Exception as e:
            logger.error(f'Failed to remove {file}: {e}.')
    logger.info('Clearing logs done.')

if __name__ == '__main__':
    clear_logs()
