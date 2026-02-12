import logging
import os
import subprocess
import sys
import json
import zipfile
import threading
import time
from typing import Optional, List
from pydantic import BaseModel, Field

from kaa.errors import (
    UpdateFetchListError, CompatibilityError, UpdateInstallError
)

logger = logging.getLogger(__name__)

_PRIMARY_PIP_INDEX = ("https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple", "mirrors.tuna.tsinghua.edu.cn")
_EXTRA_PIP_INDEX = ("https://pypi.1ichika.de/simple", "pypi.1ichika.de")

class VersionInfo(BaseModel):
    """存储版本信息的 Pydantic 模型"""
    versions: List[str] = Field(default_factory=list)
    latest: Optional[str] = None
    installed_version: Optional[str] = None
    launcher_version: Optional[str] = None

def _compare_versions(version1: str, version2: str) -> int:
    """
    比较两个版本字符串。

    :param version1: 第一个版本号
    :param version2: 第二个版本号
    :return: -1 表示 version1 < version2, 0 表示 version1 == version2, 1 表示 version1 > version2
    """
    if version1 == "0.4.x":
        version1 = "0.4.0"

    def parse(v):
        v = v.lstrip('v')
        parts = v.split('.')
        base = []
        pre_release = ''
        for part in parts:
            if 'b' in part:
                base.append(int(part.split('b')[0]))
                pre_release = ('b', int(part.split('b')[1]))
                break
            elif 'a' in part:
                base.append(int(part.split('a')[0]))
                pre_release = ('a', int(part.split('a')[1]))
                break
            elif 'rc' in part:
                base.append(int(part.split('rc')[0]))
                pre_release = ('rc', int(part.split('rc')[1]))
                break
            else:
                base.append(int(part))
        
        pre_map = {'a': -2, 'b': -1, 'rc': -0.5}
        if pre_release:
            return tuple(base) + (pre_map[pre_release[0]], pre_release[1])
        return tuple(base) + (0, 0)

    v1_parsed = parse(version1)
    v2_parsed = parse(version2)

    if v1_parsed < v2_parsed:
        return -1
    if v1_parsed > v2_parsed:
        return 1
    return 0

class UpdateService:
    """处理应用程序更新逻辑"""

    def __init__(self, repo_name: str = "ksaa"):
        self.repo_name = repo_name
        self.bootstrap_pyz_path = os.path.join(os.getcwd(), "bootstrap.pyz")

    def _get_launcher_version(self) -> Optional[str]:
        """
        从 bootstrap.pyz/meta.py 读取启动器版本。
        
        :return: 启动器版本字符串，如果无法确定则返回 None。
        """
        if not os.path.exists(self.bootstrap_pyz_path):
            logger.warning("bootstrap.pyz not found.")
            return None

        try:
            with zipfile.ZipFile(self.bootstrap_pyz_path, 'r') as zf:
                if 'meta.py' not in zf.namelist():
                    logger.warning("meta.py not found in bootstrap.pyz, assuming legacy launcher.")
                    return "0.4.x"

                meta_content = zf.read('meta.py').decode('utf-8')
                exec_globals = {}
                exec_locals = {}
                exec(meta_content, exec_globals, exec_locals)

                version = exec_locals.get('VERSION')
                if version and isinstance(version, str):
                    logger.info(f"Launcher version from meta.py: {version}")
                    return version.lstrip('v')
                else:
                    logger.warning("VERSION not found in meta.py.")
                    return None
        except zipfile.BadZipFile:
            logger.info("bootstrap.pyz is not a valid zip file, assuming legacy launcher.")
            return "0.4.x"
        except Exception as e:
            logger.error(f"Failed to read launcher version: {e}", exc_info=True)
            return None

    def list_remote_versions(self) -> VersionInfo:
        """
        从 PyPI 获取可用版本。

        :return: 包含版本数据的 VersionInfo 对象。
        :raises UpdateFetchListError: 如果无法获取或解析版本列表。
        """
        primary_url, primary_host = _PRIMARY_PIP_INDEX
        extra_url, extra_host = _EXTRA_PIP_INDEX
        cmd = [
            sys.executable, "-m", "pip", "index", "versions", self.repo_name,
            "--json", "--pre",
            "--index-url", primary_url,
            "--extra-index-url", extra_url,
            "--trusted-host", primary_host,
            "--trusted-host", extra_host,
        ]
        logger.info(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )

            if result.returncode != 0:
                raise UpdateFetchListError(result.stderr.strip() or f"pip exited with code {result.returncode}")

            data = json.loads(result.stdout)
            version_info = VersionInfo(
                versions=data.get("versions", []),
                latest=data.get("latest"),
                installed_version=data.get("installed_version")
            )
            version_info.launcher_version = self._get_launcher_version()
            logger.info(f"Found {len(version_info.versions)} available versions.")
            return version_info

        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            raise UpdateFetchListError(str(e)) from e

    def _check_compatibility(self, target_version: str) -> Optional[str]:
        """
        检查启动器是否与目标版本兼容。
        
        :raises CompatibilityError: 如果启动器不兼容。
        :return: 如果有潜在问题，则返回警告消息，否则返回 None。
        """
        launcher_version = self._get_launcher_version()
        if not launcher_version:
            return "无法获取启动器版本，可以继续安装但可能存在兼容性问题"

        logger.info(f"Launcher version: {launcher_version}, Target version: {target_version}")

        if _compare_versions(launcher_version, "0.5.0") < 0:
            if _compare_versions(target_version, "2025.9b1") >= 0:
                raise CompatibilityError(launcher_version, target_version)
            else:
                return "启动器版本较低，建议升级到 v0.5.0 以上"
        return None

    def install_version(self, version: str):
        """
        安装应用程序的特定版本。

        :param version: 要安装的版本。
        :raises CompatibilityError: 如果启动器不兼容。
        :raises UpdateInstallError: 如果安装过程启动失败。
        """
        if not version:
            raise ValueError("A version must be selected to install.")

        warning = self._check_compatibility(version)
        if warning:
            logger.warning(warning)

        def _install_and_exit():
            try:
                time.sleep(1)
                cmd = [sys.executable, self.bootstrap_pyz_path, f"--install-version={version}"]
                logger.info(f"Starting installation via launcher: {' '.join(cmd)}")

                subprocess.Popen(
                    cmd,
                    cwd=os.getcwd(),
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
                logger.info("Installation process started. Exiting current application.")
                os._exit(0)
            except Exception as e:
                logger.critical(f"Failed to launch installation process: {e}", exc_info=True)
                
        try:
            install_thread = threading.Thread(target=_install_and_exit, daemon=True)
            install_thread.start()
        except Exception as e:
            raise UpdateInstallError(str(e)) from e
