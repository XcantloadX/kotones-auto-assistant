from fastapi import APIRouter, HTTPException, Path
from ..schemas import VersionInfo, SaveResult
import subprocess
import sys
import json
import logging
import threading
import time
import os

router = APIRouter(tags=["update"]) 

logger = logging.getLogger(__name__)


@router.get("/update/changelog", response_model=str)
async def get_update_changelog() -> str:
    """获取更新日志"""
    try:
        from kotonebot.kaa.metadata import WHATS_NEW
        return WHATS_NEW
    except ImportError:
        logger.warning("无法导入 WHATS_NEW，返回默认信息")
        return "# 更新日志\n\n暂无更新日志信息。"


@router.get("/update/versions", response_model=VersionInfo)
async def get_update_versions() -> VersionInfo:
    """列出所有可用版本"""
    try:
        # 构建命令，使用清华镜像源
        cmd = [
            sys.executable, "-m", "pip", "index", "versions", "ksaa", "--json",
            "--index-url", "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple",
            "--trusted-host", "mirrors.tuna.tsinghua.edu.cn"
        ]
        logger.info(f"执行命令: {' '.join(cmd)}")

        # 使用 pip index versions --json 来获取版本信息
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        logger.info(f"命令返回码: {result.returncode}")
        if result.stdout:
            logger.info(f"命令输出: {result.stdout[:500]}...")  # 只记录前500字符
        if result.stderr:
            logger.warning(f"命令错误输出: {result.stderr}")

        if result.returncode != 0:
            error_msg = f"获取版本列表失败: {result.stderr}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # 解析 JSON 输出
        try:
            data = json.loads(result.stdout)
            versions = data.get("versions", [])
            latest_version = data.get("latest", "")
            installed_version = data.get("installed_version", "")

            logger.info(f"解析到 {len(versions)} 个版本")
            logger.info(f"最新版本: {latest_version}")
            logger.info(f"已安装版本: {installed_version}")

        except json.JSONDecodeError as e:
            error_msg = f"解析版本信息失败: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        if not versions:
            error_msg = "未找到可用版本"
            logger.warning(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        return VersionInfo(
            installed=installed_version if installed_version else None,
            latest=latest_version if latest_version else None,
            versions=versions
        )

    except subprocess.TimeoutExpired:
        error_msg = "获取版本列表超时"
        logger.error(error_msg)
        raise HTTPException(status_code=408, detail=error_msg)
    except Exception as e:
        error_msg = f"获取版本列表失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/update/install/{version}", response_model=SaveResult)
async def post_update_install(version: str = Path(..., description="要安装的版本")) -> SaveResult:
    """安装选定的版本"""
    if not version:
        raise HTTPException(status_code=400, detail="请先选择一个版本")

    def install_and_exit():
        """在后台线程中执行安装并退出程序"""
        try:
            # 等待一小段时间确保UI响应已返回
            time.sleep(1)

            # 构建启动器命令
            bootstrap_path = os.path.join(os.getcwd(), "bootstrap.pyz")
            cmd = [sys.executable, bootstrap_path, f"--install-version={version}"]
            logger.info(f"开始通过启动器安装版本 {version}")
            logger.info(f"执行命令: {' '.join(cmd)}")

            # 启动启动器进程（不等待完成）
            subprocess.Popen(
                cmd,
                cwd=os.getcwd(),
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )

            # 等待一小段时间确保启动器启动
            time.sleep(2)

            # 退出当前程序
            logger.info("安装即将开始，正在退出当前程序...")
            os._exit(0)

        except Exception as e:
            logger.error(f"安装过程中发生错误: {str(e)}")
            raise

    try:
        # 在后台线程中执行安装和退出
        install_thread = threading.Thread(target=install_and_exit, daemon=True)
        install_thread.start()

        return SaveResult(
            ok=True, 
            message=f"正在启动器中安装版本 {version}，程序将自动重启..."
        )

    except Exception as e:
        error_msg = f"启动安装进程失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


# 保留原有的不带版本参数的接口作为兼容
@router.post("/update/install", response_model=SaveResult)
async def post_update_install_default() -> SaveResult:
    """安装最新版本（兼容接口）"""
    # 获取最新版本信息
    version_info = await get_update_versions()
    if not version_info.latest:
        raise HTTPException(status_code=404, detail="未找到最新版本")
    
    # 调用带版本参数的安装接口
    return await post_update_install(version_info.latest) 