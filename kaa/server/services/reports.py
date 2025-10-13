"""
Reports RPC 服务
处理问题报告的提交和导出
"""
import logging
from ..rpc import registry

logger = logging.getLogger(__name__)


@registry.decorator('reports.save')
async def reports_save(title: str, description: str, upload: bool):
    """保存问题报告"""
    # TODO: 实现流式输出进度
    # 当前简化版本
    
    logger.info(f"Saving bug report: {title}")
    
    # 模拟报告生成
    # 在实际实现中，这里应该调用 Gradio 中的 _save_bug_report 方法
    # 并通过流式响应推送进度
    
    return {
        "success": True,
        "message": "问题报告已保存",
        "path": f"./reports/{title}.zip"
    }


@registry.decorator('reports.export_logs')
async def reports_export_logs():
    """导出日志文件"""
    import os
    import zipfile
    from datetime import datetime
    
    if not os.path.exists('logs'):
        raise FileNotFoundError("logs 文件夹不存在")
    
    timestamp = datetime.now().strftime('%y-%m-%d-%H-%M-%S')
    zip_filename = f'logs-{timestamp}.zip'
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk('logs'):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, 'logs')
                zipf.write(file_path, arcname)
    
    logger.info(f"Exported logs to {zip_filename}")
    return {"success": True, "path": zip_filename}


@registry.decorator('reports.export_dumps')
async def reports_export_dumps():
    """导出 dumps 文件"""
    import os
    import zipfile
    from datetime import datetime
    
    if not os.path.exists('dumps'):
        raise FileNotFoundError("dumps 文件夹不存在")
    
    timestamp = datetime.now().strftime('%y-%m-%d-%H-%M-%S')
    zip_filename = f'dumps-{timestamp}.zip'
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk('dumps'):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, 'dumps')
                zipf.write(file_path, arcname)
    
    logger.info(f"Exported dumps to {zip_filename}")
    return {"success": True, "path": zip_filename}

